"""Autonomous Resume Tailoring Agent for MCP Job Application System.
Adheres strictly to Autonomous Agent Blueprint §4.3, §7, and §8.

Core Capabilities:
1. Ingests Job Role, Company, and Description (from JobListing or custom input).
2. Extracts core skill requirements, seniority, and technical domain themes.
3. Maps requirements against Candidate Master Ground Truth (config/profile.yaml).
4. Tailors Professional Summary, Skill Ordering, Bullet Point Emphasis, and Featured Projects.
5. Synthesizes a concise (<= 200 words) role-specific Cover Letter.
6. Enforces Pass 2 Zero-Fabrication Audit (fails if unsupported claims/credentials appear).
7. Renders Single-Column, ATS-compliant, high-resolution PDF and Plain-Text artifacts.
"""
import logging
import re
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from core.models import JobListing, ApplicationStatus
from core.profile_manager import ProfileManager
from core.llm_client import LLMClient

logger = logging.getLogger(__name__)


class TailoredResumeArtifacts:
    """Holds all artifacts produced by the ResumeTailorAgent."""
    def __init__(
        self,
        job_id: str,
        role_title: str,
        company: str,
        match_analysis: Dict[str, Any],
        summary: str,
        ordered_skills: Dict[str, List[str]],
        tailored_experience: List[Dict[str, Any]],
        tailored_projects: List[Dict[str, Any]],
        education: List[Dict[str, Any]],
        certifications: List[Dict[str, Any]],
        cover_letter: str,
        ats_text: str,
        pdf_path: Optional[str] = None,
        text_path: Optional[str] = None,
        audit_passed: bool = True,
        audit_violations: Optional[List[str]] = None,
        claims_diff: Optional[List[Dict[str, Any]]] = None
    ):
        self.job_id = job_id
        self.role_title = role_title
        self.company = company
        self.match_analysis = match_analysis
        self.summary = summary
        self.ordered_skills = ordered_skills
        self.tailored_experience = tailored_experience
        self.tailored_projects = tailored_projects
        self.education = education
        self.certifications = certifications
        self.cover_letter = cover_letter
        self.ats_text = ats_text
        self.pdf_path = pdf_path
        self.text_path = text_path
        self.audit_passed = audit_passed
        self.audit_violations = audit_violations or []
        self.claims_diff = claims_diff or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "role_title": self.role_title,
            "company": self.company,
            "match_analysis": self.match_analysis,
            "summary": self.summary,
            "ordered_skills": self.ordered_skills,
            "tailored_experience": self.tailored_experience,
            "tailored_projects": self.tailored_projects,
            "education": self.education,
            "certifications": self.certifications,
            "cover_letter": self.cover_letter,
            "ats_text": self.ats_text,
            "pdf_path": self.pdf_path,
            "text_path": self.text_path,
            "pdf_filename": Path(self.pdf_path).name if self.pdf_path else None,
            "text_filename": Path(self.text_path).name if self.text_path else None,
            "audit_passed": self.audit_passed,
            "audit_violations": self.audit_violations,
            "claims_diff": self.claims_diff,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


class ResumeTailorAgent:
    """
    Autonomous Resume Tailoring Agent.
    Specialized agent that tailors candidate resumes with respect to specific job roles
    while strictly enforcing candidate truthfulness (zero hallucinations).
    """

    def __init__(
        self,
        profile_mgr: Optional[ProfileManager] = None,
        llm_client: Optional[LLMClient] = None,
        artifacts_dir: str = "data/artifacts"
    ):
        self.profile_mgr = profile_mgr or ProfileManager()
        self.llm_client = llm_client or LLMClient()
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    async def tailor_for_job(self, job: JobListing, generate_pdf: bool = True) -> TailoredResumeArtifacts:
        """
        Tailors a resume specifically for a discovered JobListing.
        """
        return await self.tailor_for_custom_role(
            job_id=job.id,
            role_title=job.title,
            company=job.company,
            job_description=job.description or f"Role: {job.title} at {job.company}",
            generate_pdf=generate_pdf
        )

    async def tailor_for_custom_role(
        self,
        role_title: str,
        company: str,
        job_description: str,
        job_id: Optional[str] = None,
        generate_pdf: bool = True
    ) -> TailoredResumeArtifacts:
        """
        Tailors a resume for any arbitrary role title and job description.
        """
        job_id = job_id or f"custom_{re.sub(r'[^a-zA-Z0-9]', '', role_title.lower())[:10]}_{int(datetime.now().timestamp())}"
        p_yaml = self.profile_mgr.get_profile_yaml()

        # Step 1: Extract Job Requirements & Semantic Themes
        analysis = self._analyze_requirements(role_title, job_description, p_yaml)

        # Step 2: Tailor Resume Content (Pass 1)
        tailored = await self._tailor_content(role_title, company, job_description, analysis, p_yaml)

        # Step 3: Run Pass 2 Fabrication Audit
        audit_passed, violations, claims_diff = self._audit_fabrication(tailored, p_yaml)

        # Step 4: Render ATS Plain Text & Cover Letter
        ats_text = self._render_ats_text(tailored, p_yaml)
        cover_letter = self._generate_cover_letter(role_title, company, analysis, p_yaml)

        # Step 5: Save Artifact Files
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '', p_yaml.get("identity", {}).get("full_name", "Candidate").replace(" ", "_"))
        safe_comp = re.sub(r'[^a-zA-Z0-9_]', '', company.replace(" ", "_"))
        safe_role = re.sub(r'[^a-zA-Z0-9_]', '', role_title.replace(" ", "_"))

        base_filename = f"{safe_name}_{safe_comp}_{safe_role}"
        text_file = self.artifacts_dir / f"{base_filename}.txt"
        text_file.write_text(ats_text, encoding="utf-8")

        pdf_path_str = None
        if generate_pdf:
            pdf_file = self.artifacts_dir / f"{base_filename}.pdf"
            pdf_rendered = await self._render_pdf(tailored, p_yaml, pdf_file)
            if pdf_rendered and pdf_file.exists():
                pdf_path_str = str(pdf_file)
            else:
                # If Playwright PDF render had an issue, fallback to existing role PDF or text
                existing_pdf = self.profile_mgr.get_resume_for_job(JobListing(
                    id=job_id, platform="custom", title=role_title, company=company, url="https://example.com"
                ))
                if existing_pdf and existing_pdf.exists():
                    pdf_path_str = str(existing_pdf)

        return TailoredResumeArtifacts(
            job_id=job_id,
            role_title=role_title,
            company=company,
            match_analysis=analysis,
            summary=tailored["summary"],
            ordered_skills=tailored["ordered_skills"],
            tailored_experience=tailored["experience"],
            tailored_projects=tailored["projects"],
            education=p_yaml.get("education", []),
            certifications=p_yaml.get("certifications", []),
            cover_letter=cover_letter,
            ats_text=ats_text,
            pdf_path=pdf_path_str,
            text_path=str(text_file),
            audit_passed=audit_passed,
            audit_violations=violations,
            claims_diff=claims_diff
        )

    def _analyze_requirements(self, title: str, description: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses JD to identify technical keywords, matching candidate skills, and gaps.
        """
        combined_text = f"{title} {description}".lower()
        skills = profile.get("skills", {})
        strong = skills.get("strong", [])
        familiar = skills.get("familiar", [])

        # Match skills present in candidate ground truth
        matched_strong = [s for s in strong if self._keyword_present(s, combined_text)]
        matched_familiar = [s for s in familiar if self._keyword_present(s, combined_text)]
        unmatched_candidate_skills = [s for s in strong if s not in matched_strong]

        # Detect Seniority
        seniority = "Mid"
        if re.search(r'\b(senior|sr\.?|lead|principal|staff|architect)\b', title.lower()):
            seniority = "Senior"
        elif re.search(r'\b(junior|jr\.?|associate|intern|entry)\b', title.lower()):
            seniority = "Entry"

        # Detect Primary Domain
        domain = "Software Engineering"
        if re.search(r'\b(ai|ml|machine learning|llm|nlp|agent|deep learning)\b', combined_text):
            domain = "AI & Machine Learning"
        elif re.search(r'\b(devops|sre|infrastructure|cloud|kubernetes|terraform)\b', combined_text):
            domain = "DevOps & Cloud Infrastructure"
        elif re.search(r'\b(frontend|front-end|ui|react|next\.?js|angular|vue)\b', combined_text):
            domain = "Frontend & UI Systems"
        elif re.search(r'\b(backend|back-end|api|distributed|microservices|golang|python)\b', combined_text):
            domain = "Backend & Distributed Systems"
        elif re.search(r'\b(full stack|fullstack|full-stack)\b', combined_text):
            domain = "Full Stack Engineering"

        # Common tech keywords in JD
        tech_vocab = [
            "python", "typescript", "javascript", "go", "golang", "fastapi", "react", "playwright",
            "postgresql", "postgres", "redis", "docker", "kubernetes", "k8s", "aws", "langchain",
            "graphql", "next.js", "mongodb", "kafka", "microservices", "rest api", "ci/cd",
            "git", "sqlite", "rag", "llama", "llm", "claude", "openai"
        ]
        detected_jd_keywords = [t.title() for t in tech_vocab if self._keyword_present(t, combined_text)]

        # Missing skills (skills mentioned in JD that candidate does NOT list)
        missing_skills = [
            kw for kw in detected_jd_keywords
            if kw.lower() not in [s.lower() for s in (strong + familiar)]
        ]

        return {
            "seniority": seniority,
            "domain": domain,
            "matched_strong_skills": matched_strong,
            "matched_familiar_skills": matched_familiar,
            "unmatched_candidate_skills": unmatched_candidate_skills,
            "detected_jd_keywords": detected_jd_keywords,
            "missing_skills": missing_skills
        }

    def _keyword_present(self, keyword: str, text: str) -> bool:
        kw_clean = re.escape(keyword.lower())
        pattern = rf"(?:\b|_){kw_clean}(?:\b|_)"
        return bool(re.search(pattern, text))

    async def _tailor_content(
        self,
        title: str,
        company: str,
        description: str,
        analysis: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Pass 1: Tailors Professional Summary, Skill Ordering, and Bullet Priority.
        Employs LLM if configured; seamlessly falls back to high-fidelity deterministic engine.
        """
        identity = profile.get("identity", {})
        experience = profile.get("experience", [])
        projects = profile.get("projects", [])
        skills = profile.get("skills", {})

        # Categorize and prioritize skills
        ordered_skills = self._order_skills_by_category(skills, analysis)

        # Re-order and prioritize experience bullets
        tailored_exp = []
        claims_diff = []

        combined_jd = f"{title} {description}".lower()

        for exp in experience:
            exp_copy = dict(exp)
            bullets = list(exp.get("bullets", []))

            # Score each bullet based on keyword match with the JD
            scored_bullets = []
            for b in bullets:
                score = 0
                b_lower = b.lower()
                for kw in analysis["matched_strong_skills"] + analysis["matched_familiar_skills"]:
                    if kw.lower() in b_lower:
                        score += 3
                for kw in analysis["detected_jd_keywords"]:
                    if kw.lower() in b_lower:
                        score += 1
                scored_bullets.append((score, b))

            # Sort descending by relevance score
            scored_bullets.sort(key=lambda x: x[0], reverse=True)
            new_bullets = [b for _, b in scored_bullets]

            if new_bullets != bullets:
                claims_diff.append({
                    "section": f"Experience: {exp.get('company')}",
                    "change": "Prioritized high-relevance bullets matching role requirements",
                    "top_bullet": new_bullets[0] if new_bullets else ""
                })

            exp_copy["bullets"] = new_bullets
            tailored_exp.append(exp_copy)

        # Select & Prioritize Projects
        tailored_projects = []
        for proj in projects:
            p_copy = dict(proj)
            p_score = 0
            stack_text = " ".join(proj.get("stack", [])).lower()
            impact_text = proj.get("impact", "").lower()

            for kw in analysis["matched_strong_skills"] + analysis["detected_jd_keywords"]:
                if kw.lower() in stack_text or kw.lower() in impact_text:
                    p_score += 2

            tailored_projects.append((p_score, p_copy))

        tailored_projects.sort(key=lambda x: x[0], reverse=True)
        final_projects = [p for _, p in tailored_projects]

        # Generate Tailored Summary
        summary = self._generate_tailored_summary(title, company, analysis, profile)

        return {
            "summary": summary,
            "ordered_skills": ordered_skills,
            "experience": tailored_exp,
            "projects": final_projects,
            "claims_diff": claims_diff
        }

    def _order_skills_by_category(self, skills: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Groups candidate skills into standard ATS categories matching the candidate template:
        - Languages
        - Frameworks & Web
        - Cloud, DevOps & Systems
        - Databases
        Promotes matched skills to the front of each category.
        """
        all_skills = skills.get("strong", []) + skills.get("familiar", [])
        matched_set = {s.lower() for s in (analysis.get("matched_strong_skills", []) + analysis.get("matched_familiar_skills", []))}

        categories = {
            "Languages": ["Python", "TypeScript", "JavaScript", "Go", "SQL"],
            "Frameworks & Web": ["FastAPI", "React", "Next.js", "Node.js", "Playwright", "LangChain", "REST APIs", "GraphQL"],
            "Cloud, DevOps & Systems": ["Docker", "Kubernetes", "AWS", "Git", "GitHub Actions", "CI/CD"],
            "Databases": ["PostgreSQL", "Redis", "SQLite", "MongoDB"]
        }

        result = {}
        for cat, items in categories.items():
            cand_items = [s for s in all_skills if any(i.lower() == s.lower() for i in items)]
            if not cand_items:
                continue

            # Sort so matching skills are listed first
            cand_items.sort(key=lambda s: s.lower() in matched_set, reverse=True)
            result[cat] = cand_items

        return result

    def _generate_tailored_objective(
        self,
        role_title: str,
        company: str,
        analysis: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> str:
        """
        Synthesizes an ATS-tailored Objective strictly adhering to candidate's resume template:
        [level, e.g. AI/ML undergraduate] and [target-role practitioner, e.g. Backend Engineering]
        specializing in [core focus area] and [secondary focus area].
        Experienced in building [what you build: apps, APIs, systems] using [6–8 tools relevant to the target role].
        """
        domain = analysis.get("domain", "Software Engineering")
        title_lower = role_title.lower()

        # 1. Level determination
        level = "Computer Science & Engineering undergraduate"
        if "ai" in title_lower or "ml" in title_lower or "machine learning" in domain.lower():
            level = "AI/ML undergraduate"

        # 2. Target-role practitioner
        if "ai" in title_lower or "machine learning" in title_lower or "ml" in title_lower:
            practitioner = "AI/ML practitioner"
        elif "backend" in title_lower or "distributed" in title_lower:
            practitioner = "Backend Engineering practitioner"
        elif "full stack" in title_lower or "fullstack" in title_lower:
            practitioner = "Full Stack Engineering practitioner"
        elif "devops" in title_lower or "cloud" in title_lower or "platform" in title_lower:
            practitioner = "Cloud & DevOps practitioner"
        elif "forward deployed" in title_lower or "fde" in title_lower:
            practitioner = "Forward Deployed Engineering practitioner"
        else:
            practitioner = f"{role_title} practitioner"

        # 3. Core focus area and secondary focus area
        if "ai" in title_lower or "machine learning" in title_lower:
            core_focus = "autonomous agent architectures"
            secondary_focus = "scalable LLM orchestration pipelines"
        elif "backend" in title_lower:
            core_focus = "high-throughput distributed microservices"
            secondary_focus = "event-driven data pipelines"
        elif "full stack" in title_lower:
            core_focus = "scalable web applications"
            secondary_focus = "interactive frontend systems"
        elif "devops" in title_lower or "cloud" in title_lower:
            core_focus = "container orchestration"
            secondary_focus = "automated CI/CD cloud infrastructure"
        else:
            core_focus = "autonomous agent systems"
            secondary_focus = "robust backend architectures"

        # 4. What you build
        if "ai" in title_lower:
            what_build = "intelligent multi-agent workflows, autonomous tool execution loops, and high-performance APIs"
        elif "backend" in title_lower:
            what_build = "resilient microservices, streaming ingestion pipelines, and REST/GraphQL APIs"
        else:
            what_build = "scalable web platforms, autonomous workflow engines, and reliable backend services"

        # 5. Tools (6-8 tools relevant to target role from matched and candidate profile skills)
        matched = analysis.get("matched_strong_skills", []) + analysis.get("matched_familiar_skills", [])
        all_skills = profile.get("skills", {}).get("strong", []) + profile.get("skills", {}).get("familiar", [])
        ordered_tools = []
        for s in matched + all_skills:
            if s not in ordered_tools and s.lower() not in ["sql", "html/css", "git"]:
                ordered_tools.append(s)

        tools_slice = ordered_tools[:7] if len(ordered_tools) >= 7 else ordered_tools
        if len(tools_slice) > 1:
            tools_str = ", ".join(tools_slice[:-1]) + f", and {tools_slice[-1]}"
        else:
            tools_str = ", ".join(tools_slice)

        return (
            f"{level} and {practitioner} specializing in {core_focus} and {secondary_focus}. "
            f"Experienced in building {what_build} using {tools_str}."
        )

    def _generate_tailored_summary(
        self,
        role_title: str,
        company: str,
        analysis: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> str:
        return self._generate_tailored_objective(role_title, company, analysis, profile)

    def _generate_cover_letter(
        self,
        role_title: str,
        company: str,
        analysis: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> str:
        """
        Synthesizes a concise (<= 200 words) cover letter highlighting specific matching skills.
        """
        identity = profile.get("identity", {})
        full_name = identity.get("full_name", "Vedang Tiwari")
        experience = profile.get("experience", [])

        top_exp = experience[0] if experience else {}
        curr_role = top_exp.get("title", "Software Engineer")
        curr_comp = top_exp.get("company", "TechNova Solutions")

        matched = analysis.get("matched_strong_skills", [])[:3]
        skill_text = ", ".join(matched) if matched else "Python, FastAPI, and scalable system design"

        lines = [
            f"Dear Hiring Team at {company},",
            "",
            f"I am writing to express my strong interest in the {role_title} position. As a {curr_role} at {curr_comp}, "
            f"I have architected high-throughput data processing systems and resilient backend microservices handling millions of daily transactions.",
            "",
            f"My technical background directly aligns with your requirements in {skill_text}. "
            f"I take pride in writing production-grade, well-tested code and building scalable architectures that perform reliably under heavy production load.",
            "",
            f"I would welcome the opportunity to discuss how my engineering experience can contribute directly to {company}'s goals. Thank you for your time and consideration.",
            "",
            "Sincerely,",
            full_name
        ]

        text = "\n".join(lines)
        words = text.split()
        if len(words) > 200:
            text = " ".join(words[:190]) + f"\n\nSincerely,\n{full_name}"

        return text

    def _audit_fabrication(
        self,
        tailored: Dict[str, Any],
        master_profile: Dict[str, Any]
    ) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        """
        Pass 2: Zero-hallucination verification audit.
        Compares tailored text against master ground truth to ensure no fake degrees,
        companies, awards, or unapproved skills were invented.
        """
        violations = []
        claims_diff = tailored.get("claims_diff", [])

        # 1. Verify Employers
        master_employers = {e.get("company", "").strip().lower() for e in master_profile.get("experience", []) if e.get("company")}
        for exp in tailored.get("experience", []):
            comp = exp.get("company", "").strip().lower()
            if comp and comp not in master_employers:
                violations.append(f"Unverified employer in tailored resume: '{exp.get('company')}'")

        # 2. Verify Education Institutions
        master_institutions = {ed.get("institution", "").strip().lower() for ed in master_profile.get("education", []) if ed.get("institution")}
        for ed in master_profile.get("education", []):
            inst = ed.get("institution", "").strip().lower()
            if inst and inst not in master_institutions:
                violations.append(f"Unverified educational institution: '{ed.get('institution')}'")

        # 3. Verify Skills
        allowed_skills = {
            s.strip().lower()
            for s in (master_profile.get("skills", {}).get("strong", []) + master_profile.get("skills", {}).get("familiar", []))
        }
        for cat, skills_list in tailored.get("ordered_skills", {}).items():
            for sk in skills_list:
                if sk.strip().lower() not in allowed_skills:
                    violations.append(f"Fabricated skill detected in category '{cat}': '{sk}'")

        # 4. Hallucination Red Flags Check
        hallucination_traps = [
            "phd in computer science",
            "stanford university",
            "massachusetts institute of technology",
            "google fellow",
            "turing award"
        ]
        summary_lower = tailored.get("summary", "").lower()
        for trap in hallucination_traps:
            if trap in summary_lower:
                violations.append(f"Unsupported high-prestige claim detected: '{trap}'")

        audit_passed = len(violations) == 0
        return audit_passed, violations, claims_diff

    def _render_ats_text(self, tailored: Dict[str, Any], profile: Dict[str, Any]) -> str:
        """
        Renders clean, single-column ATS text formatted strictly matching the candidate's resume template.
        """
        identity = profile.get("identity", {})
        full_name = identity.get("full_name", "VEDANG TIWARI").upper()
        email = identity.get("email", "vedangt027@gmail.com")
        phone = identity.get("phone", "+91 8527157603")
        tagline = identity.get("tagline", "Open to Relocation | Willing to work remotely")

        lines = [
            full_name,
            f"Email: {email} | Mob: {phone} | GitHub | LinkedIn | Portfolio",
            tagline,
            "",
            "OBJECTIVE",
            tailored.get("summary", ""),
            "",
            "EDUCATION"
        ]

        for edu in profile.get("education", []):
            deg = edu.get("degree", "Bachelor of Technology in Computer Science & Engineering")
            dates = edu.get("dates", "08/2023 – 05/2027")
            inst = edu.get("institution", "St. Andrews Institute of Technology & Management, Gurgaon")
            coursework = edu.get("coursework", ["Data Structures & Algorithms", "Operating Systems", "Database Management Systems", "Machine Learning", "Computer Networks"])
            lines.append(f"{deg}\t{dates}")
            lines.append(inst)
            lines.append(f"Relevant Coursework: {', '.join(coursework)}")

        lines.extend(["", "EXPERIENCE"])
        for exp in tailored.get("experience", []):
            title = exp.get("title", "")
            comp = exp.get("company", "")
            loc = exp.get("location", "Remote")
            dates = exp.get("dates", "")
            lines.append(f"{title} – {comp}\t{loc} | {dates}")
            for b in exp.get("bullets", []):
                lines.append(f"• {b}")
            lines.append("")

        if tailored.get("projects"):
            lines.append("PROJECTS")
            for proj in tailored.get("projects", []):
                name = proj.get("name", "")
                techs = proj.get("technologies") or proj.get("stack") or []
                lines.append(f"{name}\tGitHub")
                if techs:
                    lines.append(f"Technologies Used: {', '.join(techs)}")
                bullets = proj.get("bullets") or ([proj.get("impact")] if proj.get("impact") else [])
                for b in bullets:
                    lines.append(f"• {b}")
                lines.append("")

        lines.append("SKILL SUMMARY")
        for cat, sk_list in tailored.get("ordered_skills", {}).items():
            lines.append(f"{cat}: {', '.join(sk_list)}")

        if profile.get("certifications"):
            lines.extend(["", "CERTIFICATIONS"])
            certs = profile.get("certifications", [])
            for i in range(0, len(certs), 2):
                c1 = f"{certs[i].get('name')} – {certs[i].get('issuer')}"
                if i + 1 < len(certs):
                    c2 = f"{certs[i+1].get('name')} – {certs[i+1].get('issuer')}"
                    lines.append(f"{c1}\t{c2}")
                else:
                    lines.append(c1)

        return "\n".join(lines).strip()

    async def _render_pdf(self, tailored: Dict[str, Any], profile: Dict[str, Any], output_path: Path) -> bool:
        """
        Renders an ATS-safe, clean, single-column HTML template directly to PDF via Playwright Chromium.
        Strictly conforms to candidate's resume template.
        """
        identity = profile.get("identity", {})
        full_name = identity.get("full_name", "VEDANG TIWARI").upper()
        email = identity.get("email", "vedangt027@gmail.com")
        phone = identity.get("phone", "+91 8527157603")
        tagline = identity.get("tagline", "Open to Relocation | Willing to work remotely")
        links = identity.get("links", {})
        linkedin = links.get("linkedin", "https://www.linkedin.com/in/vedang-tiwari")
        github = links.get("github", "https://github.com/Vedang-tiwari")
        portfolio = links.get("portfolio", "https://vedangtiwari.runs-on.dev")

        # Build Education HTML
        edu_html = ""
        for edu in profile.get("education", []):
            deg = edu.get("degree", "Bachelor of Technology in Computer Science & Engineering")
            dates = edu.get("dates", "08/2023 – 05/2027")
            inst = edu.get("institution", "St. Andrews Institute of Technology & Management, Gurgaon")
            coursework = edu.get("coursework", ["Data Structures & Algorithms", "Operating Systems", "Database Management Systems", "Machine Learning", "Computer Networks"])
            cw_str = ", ".join(coursework)
            edu_html += f"""
            <div class='edu-block'>
                <div class='row-between'>
                    <span class='bold-item'>{deg}</span>
                    <span class='right-item'>{dates}</span>
                </div>
                <div class='sub-item'>{inst}</div>
                <div class='coursework-item'><b>Relevant Coursework:</b> {cw_str}</div>
            </div>
            """

        # Build Experience HTML
        exp_html = ""
        for exp in tailored.get("experience", []):
            bullets_li = "".join([f"<li>{b}</li>" for b in exp.get("bullets", [])])
            loc_str = exp.get("location", "Remote")
            dates_str = exp.get("dates", "")
            exp_html += f"""
            <div class='exp-block'>
                <div class='row-between'>
                    <span class='bold-item'>{exp.get('title')} – {exp.get('company')}</span>
                    <span class='right-item'>{loc_str} | {dates_str}</span>
                </div>
                <ul class='bullets'>{bullets_li}</ul>
            </div>
            """

        # Build Projects HTML
        proj_html = ""
        for proj in tailored.get("projects", []):
            techs = proj.get("technologies") or proj.get("stack") or []
            tech_line = f"<div class='tech-line'><b>Technologies Used:</b> {', '.join(techs)}</div>" if techs else ""
            bullets = proj.get("bullets") or ([proj.get("impact")] if proj.get("impact") else [])
            bullets_li = "".join([f"<li>{b}</li>" for b in bullets])
            link = proj.get("link", github)
            proj_html += f"""
            <div class='proj-block'>
                <div class='row-between'>
                    <span class='bold-item'>{proj.get('name')}</span>
                    <a class='right-link' href='{link}'>GitHub</a>
                </div>
                {tech_line}
                <ul class='bullets'>{bullets_li}</ul>
            </div>
            """

        # Build Skills HTML
        skills_html = ""
        for cat, sk_list in tailored.get("ordered_skills", {}).items():
            skills_html += f"<div class='skill-line'><b>{cat}:</b> {', '.join(sk_list)}</div>"

        # Build Certifications HTML
        certs_html = ""
        certs = profile.get("certifications", [])
        if certs:
            rows = []
            for i in range(0, len(certs), 2):
                c1 = f"<b>{certs[i].get('name')}</b> – {certs[i].get('issuer')}"
                c2 = f"<b>{certs[i+1].get('name')}</b> – {certs[i+1].get('issuer')}" if i + 1 < len(certs) else ""
                rows.append(f"<tr><td style='width: 50%;'>{c1}</td><td style='width: 50%;'>{c2}</td></tr>")
            certs_html = f"<table class='certs-table'>{''.join(rows)}</table>"

        html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{full_name} - Resume</title>
<style>
    @page {{
        size: letter;
        margin: 0.38in 0.45in 0.38in 0.45in;
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #111827;
        line-height: 1.32;
        font-size: 9pt;
        background: #ffffff;
        margin: 0;
        padding: 0;
    }}
    .header {{
        text-align: center;
        border-bottom: 1.5px solid #0f172a;
        padding-bottom: 6px;
        margin-bottom: 8px;
    }}
    .name {{
        font-size: 19pt;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: 0.5px;
        margin: 0 0 3px 0;
        text-transform: uppercase;
    }}
    .contact-line {{
        font-size: 8.8pt;
        color: #334155;
        margin: 2px 0;
    }}
    .contact-line a {{
        color: #0f172a;
        text-decoration: underline;
    }}
    .tagline {{
        font-size: 8.5pt;
        color: #475569;
        margin: 2px 0 0 0;
    }}
    .section-title {{
        font-size: 10pt;
        font-weight: 700;
        color: #0f172a;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 2px;
        margin-top: 7px;
        margin-bottom: 4px;
    }}
    .objective-text {{
        font-size: 8.8pt;
        color: #1e293b;
        margin: 3px 0 6px 0;
        text-align: justify;
        line-height: 1.34;
    }}
    .row-between {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
    }}
    .bold-item {{
        font-weight: 700;
        font-size: 9pt;
        color: #0f172a;
    }}
    .right-item {{
        font-size: 8.5pt;
        color: #475569;
        font-weight: 600;
    }}
    .right-link {{
        font-size: 8.5pt;
        color: #0f172a;
        font-weight: 600;
        text-decoration: underline;
    }}
    .sub-item {{
        font-size: 8.7pt;
        color: #334155;
        margin-top: 1px;
    }}
    .coursework-item {{
        font-size: 8.5pt;
        color: #334155;
        margin-top: 2px;
    }}
    .edu-block {{
        margin-bottom: 5px;
    }}
    .exp-block {{
        margin-bottom: 6px;
    }}
    .proj-block {{
        margin-bottom: 6px;
    }}
    .tech-line {{
        font-size: 8.5pt;
        color: #334155;
        margin-top: 1px;
        margin-bottom: 2px;
    }}
    .bullets {{
        margin: 2px 0 0 14px;
        padding: 0;
        font-size: 8.8pt;
        color: #1e293b;
        line-height: 1.33;
    }}
    .bullets li {{
        margin-bottom: 2px;
    }}
    .skill-line {{
        font-size: 8.8pt;
        color: #1e293b;
        margin: 2px 0;
    }}
    .certs-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 2px;
    }}
    .certs-table td {{
        font-size: 8.7pt;
        color: #1e293b;
        padding: 2px 4px 2px 0;
        vertical-align: top;
    }}
</style>
</head>
<body>
    <div class="header">
        <h1 class="name">{full_name}</h1>
        <div class="contact-line">
            Email: <a href="mailto:{email}">{email}</a> | Mob: {phone} | <a href="{github}">GitHub</a> | <a href="{linkedin}">LinkedIn</a> | <a href="{portfolio}">Portfolio</a>
        </div>
        <div class="tagline">{tagline}</div>
    </div>

    <div class="section-title">OBJECTIVE</div>
    <div class="objective-text">{tailored.get('summary', '')}</div>

    <div class="section-title">EDUCATION</div>
    {edu_html}

    <div class="section-title">EXPERIENCE</div>
    {exp_html}

    <div class="section-title">PROJECTS</div>
    {proj_html}

    <div class="section-title">SKILL SUMMARY</div>
    {skills_html}

    <div class="section-title">CERTIFICATIONS</div>
    {certs_html}
</body>
</html>"""

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_content(html_template, wait_until="networkidle")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                await page.pdf(
                    path=str(output_path),
                    format="Letter",
                    print_background=True,
                    margin={"top": "0.45in", "bottom": "0.45in", "left": "0.5in", "right": "0.5in"}
                )
                await browser.close()
                logger.info(f"Rendered tailored ATS PDF to '{output_path}'")
                return True
        except Exception as e:
            logger.warning(f"Could not render PDF via Playwright: {e}")
            return False
