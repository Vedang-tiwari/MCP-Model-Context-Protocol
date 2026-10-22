"""Dynamic custom platform provider that executes RSS, JSON API, or HTML scraping
declaratively defined via configuration or runtime registration.
"""
import logging
import urllib.parse
import xml.etree.ElementTree as ET
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime

from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus, CustomPlatformConfig, PlatformType

logger = logging.getLogger(__name__)


class CustomPlatformProvider(BaseJobProvider):
    def __init__(self, config: CustomPlatformConfig):
        super().__init__(name=config.name)
        self.config = config
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "*/*"
        }
        self.headers.update(config.headers)

    async def fetch_recent_jobs(
        self,
        roles: List[str],
        locations: List[str],
        max_age_hours: int = 24
    ) -> List[JobListing]:
        if not self.config.enabled:
            return []

        if self.config.platform_type == PlatformType.RSS:
            return await self._fetch_rss(roles, locations)
        elif self.config.platform_type == PlatformType.JSON_API:
            return await self._fetch_json_api(roles, locations)
        elif self.config.platform_type == PlatformType.HTML_SCRAPER:
            return await self._fetch_html_scraper(roles, locations)

        return []

    async def _fetch_rss(self, roles: List[str], locations: List[str]) -> List[JobListing]:
        results: List[JobListing] = []
        async with httpx.AsyncClient(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
            for role in roles[:3]:
                url = self._format_url(self.config.url_template, role, locations[0] if locations else "")
                try:
                    res = await client.get(url)
                    if res.status_code != 200:
                        continue

                    root = ET.fromstring(res.text)
                    channel = root.find("channel")
                    items = channel.findall("item") if channel is not None else root.findall(".//item")

                    for item in items[:self.config.max_items_per_cycle]:
                        title_el = item.find("title")
                        link_el = item.find("link")
                        desc_el = item.find("description")

                        if title_el is None or link_el is None:
                            continue

                        title = (title_el.text or "").strip()
                        link = (link_el.text or "").strip()
                        desc = (desc_el.text or "").strip() if desc_el is not None else ""
                        company = self.config.display_name or self.config.name.capitalize()

                        if " at " in title:
                            parts = title.split(" at ")
                            title = parts[0].strip()
                            company = parts[1].strip()
                        elif " - " in title:
                            parts = title.split(" - ")
                            title = parts[0].strip()
                            company = parts[-1].strip()

                        job_id = self.generate_job_id(self.name, company, title, link)

                        results.append(JobListing(
                            id=job_id,
                            platform=self.name,
                            title=title,
                            company=company,
                            location="Remote",
                            url=link,
                            apply_url=link,
                            is_easy_apply=False,
                            description=desc[:1000],
                            posted_at=datetime.utcnow(),
                            discovered_at=datetime.utcnow(),
                            status=ApplicationStatus.DISCOVERED,
                            metadata={"custom_platform": self.name}
                        ))
                except Exception as e:
                    logger.debug(f"RSS fetch error for {self.name} ({url}): {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} jobs from custom RSS provider")
        return results

    async def _fetch_json_api(self, roles: List[str], locations: List[str]) -> List[JobListing]:
        results: List[JobListing] = []
        mapping = self.config.field_mappings
        items_key = mapping.get("items", "jobs")
        title_key = mapping.get("title", "title")
        company_key = mapping.get("company", "company")
        url_key = mapping.get("url", "url")
        loc_key = mapping.get("location", "location")
        desc_key = mapping.get("description", "description")

        async with httpx.AsyncClient(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
            for role in roles[:3]:
                url = self._format_url(self.config.url_template, role, locations[0] if locations else "")
                try:
                    res = await client.get(url)
                    if res.status_code != 200:
                        continue

                    data = res.json()
                    # Resolve items
                    items = self._resolve_nested_key(data, items_key) if items_key else data
                    if not isinstance(items, list):
                        continue

                    for item in items[:self.config.max_items_per_cycle]:
                        title = str(self._resolve_nested_key(item, title_key) or "")
                        company = str(self._resolve_nested_key(item, company_key) or self.name.capitalize())
                        job_url = str(self._resolve_nested_key(item, url_key) or "")
                        loc = str(self._resolve_nested_key(item, loc_key) or "Remote")
                        desc = str(self._resolve_nested_key(item, desc_key) or "")

                        if not (title and job_url):
                            continue

                        job_id = self.generate_job_id(self.name, company, title, job_url)

                        results.append(JobListing(
                            id=job_id,
                            platform=self.name,
                            title=title,
                            company=company,
                            location=loc,
                            url=job_url,
                            apply_url=job_url,
                            is_easy_apply=False,
                            description=desc[:1000],
                            posted_at=datetime.utcnow(),
                            discovered_at=datetime.utcnow(),
                            status=ApplicationStatus.DISCOVERED,
                            metadata={"custom_platform": self.name}
                        ))
                except Exception as e:
                    logger.debug(f"JSON API error for {self.name} ({url}): {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} jobs from custom JSON API provider")
        return results

    async def _fetch_html_scraper(self, roles: List[str], locations: List[str]) -> List[JobListing]:
        results: List[JobListing] = []
        sel = self.config.selectors
        card_sel = sel.get("card", ".job")
        title_sel = sel.get("title", "h2")
        company_sel = sel.get("company", ".company")
        link_sel = sel.get("link", "a")
        loc_sel = sel.get("location", ".location")

        async with httpx.AsyncClient(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
            for role in roles[:3]:
                url = self._format_url(self.config.url_template, role, locations[0] if locations else "")
                try:
                    res = await client.get(url)
                    if res.status_code != 200:
                        continue

                    soup = BeautifulSoup(res.text, "html.parser")
                    cards = soup.select(card_sel)

                    for card in cards[:self.config.max_items_per_cycle]:
                        title_el = card.select_one(title_sel)
                        company_el = card.select_one(company_sel)
                        link_el = card.select_one(link_sel)
                        loc_el = card.select_one(loc_sel) if loc_sel else None

                        if not (title_el and link_el):
                            continue

                        title = title_el.get_text(strip=True)
                        company = company_el.get_text(strip=True) if company_el else self.name.capitalize()
                        job_url = link_el.get("href", "")
                        loc = loc_el.get_text(strip=True) if loc_el else "Remote"

                        if not job_url.startswith("http"):
                            # Resolve relative URL against base domain
                            base_domain = "/".join(url.split("/")[:3])
                            job_url = f"{base_domain}/{job_url.lstrip('/')}"

                        job_id = self.generate_job_id(self.name, company, title, job_url)

                        results.append(JobListing(
                            id=job_id,
                            platform=self.name,
                            title=title,
                            company=company,
                            location=loc,
                            url=job_url,
                            apply_url=job_url,
                            is_easy_apply=False,
                            description=f"Job posting for {title} at {company}",
                            posted_at=datetime.utcnow(),
                            discovered_at=datetime.utcnow(),
                            status=ApplicationStatus.DISCOVERED,
                            metadata={"custom_platform": self.name}
                        ))
                except Exception as e:
                    logger.debug(f"HTML scraper error for {self.name}: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} jobs from custom HTML scraper provider")
        return results

    def _format_url(self, template: str, role: str, location: str) -> str:
        role_encoded = urllib.parse.quote_plus(role)
        loc_encoded = urllib.parse.quote_plus(location)
        try:
            return template.format(role=role_encoded, location=loc_encoded)
        except Exception:
            return template

    def _resolve_nested_key(self, data: Any, key_path: str) -> Any:
        if not key_path:
            return data
        parts = key_path.split(".")
        current = data
        for p in parts:
            if isinstance(current, dict):
                current = current.get(p)
            elif isinstance(current, list) and p.isdigit():
                idx = int(p)
                current = current[idx] if idx < len(current) else None
            else:
                return None
        return current
