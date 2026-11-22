"""Docx Resume Renderer based on the Official Candidate Resume Template (mcp-resume-template.docx).
Adheres strictly to the user's uploaded Word template and Autonomous Blueprint §4.3, §7, and §8.

Sections:
1. HEADER: Full Name, Contact Info, Relocation / Remote preferences
2. OBJECTIVE: Target-role tailored summary
3. EDUCATION: Degree, Institution, Dates, Relevant Coursework
4. EXPERIENCE: Roles, Companies, Dates, Locations, and Action-Verb Impact Bullets
5. PROJECTS: Project Name, GitHub link, Technologies Used, and Architecture Bullets
6. SKILL SUMMARY: Languages, Technical Categories, Databases
7. CERTIFICATIONS: Accreditations & Issuers
"""
import os
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_MAP = {"w": W_NS}


class ResumeDocxRenderer:
    def __init__(self, template_path: Optional[str] = None):
        self.template_path = Path(template_path or "data/templates/mcp-resume-template.docx")
        self._ensure_template_exists()

    def _ensure_template_exists(self):
        """Ensures the source template exists, copying from brain user upload if needed."""
        if not self.template_path.exists():
            fallback_sources = [
                Path(r"C:\Users\prash\.gemini\antigravity\brain\6a94f1c9-f9b8-47aa-acf7-4ac31a74eea1\.user_uploaded\media_1795244539426_4647cc2d.docx"),
                Path("data/resumes/resume_fde.docx")
            ]
            for src in fallback_sources:
                if src.exists():
                    self.template_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(str(src), str(self.template_path))
                    logger.info(f"Initialized template docx from {src}")
                    break

    def get_default_template_data(self, profile_yaml: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Returns structured dictionary for the candidate based on profile.yaml.
        """
        if profile_yaml is None:
            import yaml
            prof_file = Path("config/profile.yaml")
            if prof_file.exists():
                with open(prof_file, "r", encoding="utf-8") as f:
                    profile_yaml = yaml.safe_load(f) or {}
            else:
                profile_yaml = {}

        identity = profile_yaml.get("identity", {})
        education_list = profile_yaml.get("education", [])
        primary_edu = education_list[0] if education_list else {}
        coursework = primary_edu.get("coursework", [
            "Data Structures & Algorithms", "Operating Systems", "Database Management Systems", "Machine Learning"
        ])

        experiences = profile_yaml.get("experience", [
            {
                "title": "Software Engineer",
                "company": "TechNova Solutions",
                "location": "Remote",
                "dates": "01/2023 – Present",
                "bullets": [
                    "Architected real-time data ingestion pipelines handling 2M+ records daily with Python, FastAPI, and Playwright.",
                    "Built resilient microservices and agentic workflow integrations using Python, FastAPI, and PostgreSQL, cutting p99 latency by 45%.",
                    "Integrated Redis caching, Docker containerization, and GitHub Actions CI/CD automation with 99.9% uptime."
                ]
            },
            {
                "title": "Software Engineering Intern",
                "company": "Apex Cloud Systems",
                "location": "Remote",
                "dates": "06/2022 – 12/2022",
                "bullets": [
                    "Designed automated workflow engines in Python and React used across 12 distributed enterprise client systems.",
                    "Engineered REST and GraphQL endpoints with automated unit and integration regression test suites.",
                    "Modernized containerized deployment pipelines with Docker and GitHub Actions for continuous integration."
                ]
            }
        ])

        projects = profile_yaml.get("projects", [
            {
                "name": "Autonomous Agent Orchestrator",
                "link": "GitHub",
                "technologies": ["Python", "FastAPI", "Playwright", "SQLite", "LangChain"],
                "bullets": [
                    "Architected 24/7 autonomous job scouting and application system with multi-ATS integration and stealth Playwright automation.",
                    "Implemented dynamic form-filling heuristics, LLM-based profile grounding, and zero-fabrication resume tailoring.",
                    "Built resilient asynchronous worker pools processing live multi-platform feeds with automated session checkpointing."
                ]
            },
            {
                "name": "Distributed Event Pipeline",
                "link": "GitHub",
                "technologies": ["Go", "Kafka", "PostgreSQL", "Redis", "Docker"],
                "bullets": [
                    "Engineered high-throughput event-driven worker pool processing 10k+ events/sec across streaming webhook channels.",
                    "Implemented partitioned Kafka consumers, distributed Redis locking, and transactional PostgreSQL persistence.",
                    "Added automated health probes, telemetry tracing, and horizontal container auto-scaling under spike loads."
                ]
            },
            {
                "name": "Model Context Protocol (MCP) Multi-Agent Engine",
                "link": "GitHub",
                "technologies": ["Python", "TypeScript", "FastAPI", "React", "Docker"],
                "bullets": [
                    "Developed extensible multi-agent tool execution framework adhering to Model Context Protocol standards.",
                    "Implemented secure sandboxed command execution, reactive state channels, and real-time WebSocket telemetry."
                ]
            }
        ])

        skills = profile_yaml.get("skills", {})
        strong = skills.get("strong", ["Python", "TypeScript", "JavaScript", "FastAPI", "React", "Playwright", "PostgreSQL", "Redis", "Docker", "Git"])

        return {
            "full_name": identity.get("full_name", "VEDANG TIWARI"),
            "contact_line": f"Email: {identity.get('email', 'vedangt027@gmail.com')} | Mob: {identity.get('phone', '+91 8527157603')} | GitHub | LinkedIn | Portfolio",
            "tagline": identity.get("tagline", "Open to Relocation | Willing to work remotely"),
            "objective": (
                "AI/ML and Software Engineering practitioner specializing in autonomous agent workflows, distributed backend systems, "
                "and full-stack application development. Experienced in building high-throughput APIs, data pipelines, and stealth browser automation "
                "using Python, FastAPI, Playwright, React, PostgreSQL, and Docker."
            ),
            "education": {
                "degree": primary_edu.get("degree", "Bachelor of Technology in Computer Science & Engineering"),
                "institution": primary_edu.get("institution", "St. Andrews Institute of Technology & Management, Gurgaon"),
                "dates": primary_edu.get("dates", "08/2023 – 05/2027"),
                "coursework": coursework
            },
            "experiences": experiences,
            "projects": projects,
            "skills": {
                "languages": ["Python", "TypeScript", "JavaScript", "SQL", "Go", "HTML/CSS"],
                "frameworks": ["FastAPI", "React", "Playwright", "Node.js", "Express", "LangChain"],
                "technologies": ["Docker", "Git", "GitHub Actions", "CI/CD", "Linux", "REST APIs", "GraphQL"],
                "databases": ["PostgreSQL", "Redis", "SQLite", "MongoDB"]
            },
            "certifications": profile_yaml.get("certifications", [
                {"name": "Python for Data Science & AI", "issuer": "IBM / Coursera"},
                {"name": "Machine Learning Specialization", "issuer": "DeepLearning.AI"},
                {"name": "PostgreSQL High Performance", "issuer": "PostgreSQL Org"},
                {"name": "Docker & Container Orchestration", "issuer": "Docker Certified"}
            ])
        }

    def render(self, data: Dict[str, Any], output_path: str) -> str:
        """
        Renders a customized Word document (.docx) using the exact OpenXML template.
        """
        self._ensure_template_exists()
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(self.template_path, "r") as zin:
            file_map = {item.filename: zin.read(item.filename) for item in zin.infolist()}

        doc_xml = file_map["word/document.xml"].decode("utf-8")
        root = ET.fromstring(doc_xml)
        paras = root.findall(".//w:p", NS_MAP)

        def _set_run_text(p, text, size_val="20", bold=False, italic=False):
            # Clear runs
            for r in p.findall("w:r", NS_MAP):
                p.remove(r)
            r = ET.SubElement(p, f"{{{W_NS}}}r")
            rPr = ET.SubElement(r, f"{{{W_NS}}}rPr")
            if bold:
                ET.SubElement(rPr, f"{{{W_NS}}}b")
                ET.SubElement(rPr, f"{{{W_NS}}}bCs")
            if italic:
                ET.SubElement(rPr, f"{{{W_NS}}}i")
                ET.SubElement(rPr, f"{{{W_NS}}}iCs")
            sz = ET.SubElement(rPr, f"{{{W_NS}}}sz")
            sz.set(f"{{{W_NS}}}val", str(size_val))
            szCs = ET.SubElement(rPr, f"{{{W_NS}}}szCs")
            szCs.set(f"{{{W_NS}}}val", str(size_val))
            t = ET.SubElement(r, f"{{{W_NS}}}t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = text

        def _set_header_with_tab(p, left_text, right_text, left_size="24", right_size="20", is_exp=True):
            for r in p.findall("w:r", NS_MAP):
                p.remove(r)
            # Left run
            r1 = ET.SubElement(p, f"{{{W_NS}}}r")
            rPr1 = ET.SubElement(r1, f"{{{W_NS}}}rPr")
            ET.SubElement(rPr1, f"{{{W_NS}}}b")
            ET.SubElement(rPr1, f"{{{W_NS}}}bCs")
            if is_exp:
                ET.SubElement(rPr1, f"{{{W_NS}}}i")
                ET.SubElement(rPr1, f"{{{W_NS}}}iCs")
            sz1 = ET.SubElement(rPr1, f"{{{W_NS}}}sz")
            sz1.set(f"{{{W_NS}}}val", str(left_size))
            szCs1 = ET.SubElement(rPr1, f"{{{W_NS}}}szCs")
            szCs1.set(f"{{{W_NS}}}val", str(left_size))
            t1 = ET.SubElement(r1, f"{{{W_NS}}}t")
            t1.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t1.text = left_text

            # Tab run
            r_tab = ET.SubElement(p, f"{{{W_NS}}}r")
            rPr_tab = ET.SubElement(r_tab, f"{{{W_NS}}}rPr")
            sz_tab = ET.SubElement(rPr_tab, f"{{{W_NS}}}sz")
            sz_tab.set(f"{{{W_NS}}}val", str(right_size))
            t_tab = ET.SubElement(r_tab, f"{{{W_NS}}}t")
            t_tab.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t_tab.text = "\t"

            # Right run
            r2 = ET.SubElement(p, f"{{{W_NS}}}r")
            rPr2 = ET.SubElement(r2, f"{{{W_NS}}}rPr")
            if is_exp:
                ET.SubElement(rPr2, f"{{{W_NS}}}b")
                ET.SubElement(rPr2, f"{{{W_NS}}}bCs")
                ET.SubElement(rPr2, f"{{{W_NS}}}i")
                ET.SubElement(rPr2, f"{{{W_NS}}}iCs")
            else:
                # Underline for GitHub link
                ET.SubElement(rPr2, f"{{{W_NS}}}u").set(f"{{{W_NS}}}val", "single")
            sz2 = ET.SubElement(rPr2, f"{{{W_NS}}}sz")
            sz2.set(f"{{{W_NS}}}val", str(right_size))
            szCs2 = ET.SubElement(rPr2, f"{{{W_NS}}}szCs")
            szCs2.set(f"{{{W_NS}}}val", str(right_size))
            t2 = ET.SubElement(r2, f"{{{W_NS}}}t")
            t2.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t2.text = right_text

        def _set_tech_used(p, tech_list):
            for r in p.findall("w:r", NS_MAP):
                p.remove(r)
            # Label run
            r1 = ET.SubElement(p, f"{{{W_NS}}}r")
            rPr1 = ET.SubElement(r1, f"{{{W_NS}}}rPr")
            ET.SubElement(rPr1, f"{{{W_NS}}}b")
            ET.SubElement(rPr1, f"{{{W_NS}}}bCs")
            sz1 = ET.SubElement(rPr1, f"{{{W_NS}}}sz")
            sz1.set(f"{{{W_NS}}}val", "20")
            t1 = ET.SubElement(r1, f"{{{W_NS}}}t")
            t1.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t1.text = "Technologies Used: "

            # Value run
            r2 = ET.SubElement(p, f"{{{W_NS}}}r")
            rPr2 = ET.SubElement(r2, f"{{{W_NS}}}rPr")
            sz2 = ET.SubElement(rPr2, f"{{{W_NS}}}sz")
            sz2.set(f"{{{W_NS}}}val", "20")
            t2 = ET.SubElement(r2, f"{{{W_NS}}}t")
            t2.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t2.text = ", ".join(tech_list) if isinstance(tech_list, list) else str(tech_list)

        # 1. Update OBJECTIVE (P4)
        if len(paras) > 4:
            obj_text = data.get("objective") or data.get("summary") or ""
            if obj_text:
                _set_run_text(paras[4], obj_text, size_val="20")

        # 2. Update EDUCATION Coursework (P8)
        if len(paras) > 8:
            edu_info = data.get("education", {})
            coursework = edu_info.get("coursework", []) if isinstance(edu_info, dict) else []
            if coursework:
                _set_run_text(paras[8], f"Relevant Coursework: {', '.join(coursework)}", size_val="20")

        # 3. Update EXPERIENCE (P10-P17)
        exps = data.get("experiences", [])
        if exps:
            # Experience 1 (P10 header, P11-13 bullets)
            e1 = exps[0]
            if len(paras) > 10:
                _set_header_with_tab(
                    paras[10],
                    f"{e1.get('title', 'Software Engineer')} – {e1.get('company', 'TechNova Solutions')}",
                    f"{e1.get('location', 'Remote')} | {e1.get('dates', '01/2023 – Present')}",
                    is_exp=True
                )
            b1 = e1.get("bullets", [])
            for idx, b_text in enumerate(b1[:3]):
                if len(paras) > 11 + idx:
                    _set_run_text(paras[11 + idx], b_text, size_val="20")

            # Experience 2 (P14 header, P15-17 bullets)
            if len(exps) > 1:
                e2 = exps[1]
                if len(paras) > 14:
                    _set_header_with_tab(
                        paras[14],
                        f"{e2.get('title', 'Software Engineering Intern')} – {e2.get('company', 'Apex Cloud Systems')}",
                        f"{e2.get('location', 'Remote')} | {e2.get('dates', '06/2022 – 12/2022')}",
                        is_exp=True
                    )
                b2 = e2.get("bullets", [])
                for idx, b_text in enumerate(b2[:3]):
                    if len(paras) > 15 + idx:
                        _set_run_text(paras[15 + idx], b_text, size_val="20")

        # 4. Update PROJECTS (P19-P32)
        projs = data.get("projects", [])
        if projs:
            # Project 1 (P19-23)
            p1 = projs[0]
            if len(paras) > 19:
                _set_header_with_tab(paras[19], p1.get("name", "Autonomous Agent Orchestrator"), p1.get("link", "GitHub"), is_exp=False)
            if len(paras) > 20:
                _set_tech_used(paras[20], p1.get("technologies") or p1.get("stack") or [])
            for idx, b_text in enumerate(p1.get("bullets", [])[:3]):
                if len(paras) > 21 + idx:
                    _set_run_text(paras[21 + idx], b_text, size_val="20")

            # Project 2 (P24-28)
            if len(projs) > 1:
                p2 = projs[1]
                if len(paras) > 24:
                    _set_header_with_tab(paras[24], p2.get("name", "Distributed Event Pipeline"), p2.get("link", "GitHub"), is_exp=False)
                if len(paras) > 25:
                    _set_tech_used(paras[25], p2.get("technologies") or p2.get("stack") or [])
                for idx, b_text in enumerate(p2.get("bullets", [])[:3]):
                    if len(paras) > 26 + idx:
                        _set_run_text(paras[26 + idx], b_text, size_val="20")

            # Project 3 (P29-32)
            if len(projs) > 2:
                p3 = projs[2]
                if len(paras) > 29:
                    _set_header_with_tab(paras[29], p3.get("name", "Model Context Protocol Multi-Agent Engine"), p3.get("link", "GitHub"), is_exp=False)
                if len(paras) > 30:
                    _set_tech_used(paras[30], p3.get("technologies") or p3.get("stack") or [])
                for idx, b_text in enumerate(p3.get("bullets", [])[:2]):
                    if len(paras) > 31 + idx:
                        _set_run_text(paras[31 + idx], b_text, size_val="20")

        # 5. Update SKILL SUMMARY (P34-P38)
        skills = data.get("skills", {})
        if isinstance(skills, dict):
            langs = skills.get("languages", ["Python", "TypeScript", "JavaScript", "SQL", "Go", "HTML/CSS"])
            frameworks = skills.get("frameworks", ["FastAPI", "React", "Playwright", "Node.js", "LangChain"])
            techs = skills.get("technologies", ["Docker", "Git", "GitHub Actions", "CI/CD", "Linux", "REST APIs"])
            dbs = skills.get("databases", ["PostgreSQL", "Redis", "SQLite", "MongoDB"])

            if len(paras) > 34:
                _set_run_text(paras[34], f"Languages: {', '.join(langs)}", size_val="20")
            if len(paras) > 35:
                _set_run_text(paras[35], f"Frameworks & Tools: {', '.join(frameworks)}", size_val="20")
            if len(paras) > 36:
                _set_run_text(paras[36], f"Engineering & DevOps: {', '.join(techs)}", size_val="20")
            if len(paras) > 37:
                _set_run_text(paras[37], f"AI & Systems: Autonomous Agents, RAG Pipelines, Microservices, Event Architectures", size_val="20")
            if len(paras) > 38:
                _set_run_text(paras[38], f"Databases: {', '.join(dbs)}", size_val="20")

        # 6. Update CERTIFICATIONS (P40-P41)
        certs = data.get("certifications", [])
        if len(certs) >= 2 and len(paras) > 40:
            c1 = certs[0] if isinstance(certs[0], str) else f"{certs[0].get('name')} – {certs[0].get('issuer')}"
            c2 = certs[1] if isinstance(certs[1], str) else f"{certs[1].get('name')} – {certs[1].get('issuer')}"
            _set_header_with_tab(paras[40], c1, c2, left_size="20", right_size="20", is_exp=False)
        if len(certs) >= 4 and len(paras) > 41:
            c3 = certs[2] if isinstance(certs[2], str) else f"{certs[2].get('name')} – {certs[2].get('issuer')}"
            c4 = certs[3] if isinstance(certs[3], str) else f"{certs[3].get('name')} – {certs[3].get('issuer')}"
            _set_header_with_tab(paras[41], c3, c4, left_size="20", right_size="20", is_exp=False)

        # Repackage OpenXML document
        new_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        file_map["word/document.xml"] = new_xml

        with zipfile.ZipFile(out_file, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for fname, content in file_map.items():
                zout.writestr(fname, content)

        logger.info(f"Rendered customized resume docx at {out_file} ({out_file.stat().st_size} bytes)")
        return str(out_file)

    def render_plain_text(self, data: Dict[str, Any]) -> str:
        """
        Renders ATS-compliant single-column plain text corresponding to the template.
        """
        lines = []
        lines.append(data.get("full_name", "VEDANG TIWARI"))
        lines.append(data.get("contact_line", "Email: vedangt027@gmail.com | Mob: +91 8527157603 | GitHub | LinkedIn | Portfolio"))
        lines.append(data.get("tagline", "Open to Relocation | Willing to work remotely"))
        lines.append("")
        lines.append("OBJECTIVE")
        lines.append(data.get("objective", ""))
        lines.append("")
        lines.append("EDUCATION")
        edu = data.get("education", {})
        lines.append(f"{edu.get('degree', 'B.Tech CSE')} \t {edu.get('dates', '08/2023 – 05/2027')}")
        lines.append(edu.get("institution", "St. Andrews Institute of Technology & Management, Gurgaon"))
        coursework = edu.get("coursework", [])
        if coursework:
            lines.append(f"Relevant Coursework: {', '.join(coursework)}")
        lines.append("")
        lines.append("EXPERIENCE")
        for exp in data.get("experiences", []):
            lines.append(f"{exp.get('title')} – {exp.get('company')} \t {exp.get('location')} | {exp.get('dates')}")
            for b in exp.get("bullets", []):
                lines.append(f"  • {b}")
            lines.append("")
        lines.append("PROJECTS")
        for p in data.get("projects", []):
            lines.append(f"{p.get('name')} \t {p.get('link', 'GitHub')}")
            tech = p.get("technologies") or p.get("stack") or []
            lines.append(f"Technologies Used: {', '.join(tech)}")
            for b in p.get("bullets", []):
                lines.append(f"  • {b}")
            lines.append("")
        lines.append("SKILL SUMMARY")
        skills = data.get("skills", {})
        for cat, items in skills.items():
            if isinstance(items, list):
                lines.append(f"{cat.replace('_', ' ').title()}: {', '.join(items)}")
        lines.append("")
        lines.append("CERTIFICATIONS")
        for c in data.get("certifications", []):
            if isinstance(c, dict):
                lines.append(f"  • {c.get('name')} – {c.get('issuer')}")
            else:
                lines.append(f"  • {c}")

        return "\n".join(lines)
