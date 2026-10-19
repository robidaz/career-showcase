"""
generate_career_showcase.py
Renders index.html and the one-page résumé PDF from:
  - scripts/templates/career-showcase.html.j2  (site layout)
  - scripts/templates/resume.html.j2           (résumé layout — see resume_pdf.py)
  - career-data.md                              (all content — edit this file)

Usage:
  python scripts/generate_career_showcase.py             # site + résumé PDF
  python scripts/generate_career_showcase.py --skip-pdf  # site only, keep the existing PDF
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import pathlib
import re
import sys

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
WORKSPACE = pathlib.Path(__file__).parent.parent
TEMPLATE_PATH = WORKSPACE / "scripts" / "templates" / "career-showcase.html.j2"
OUTPUT_PATH = WORKSPACE / "index.html"
AVATAR_PATH = WORKSPACE / "documentation" / "additional information" / "profile_picture.jpg"
DATA_PATH = WORKSPACE / "career-data.md"
RESUME_DIR = WORKSPACE / "assets" / "resume"
RESUME_PREVIEW_NAME = "resume-preview.png"
RESUME_THUMB_NAME = "resume-thumb.png"         # header thumbnail (336px wide = 168px at 2x)

LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"]

# ---------------------------------------------------------------------------
# Inline the avatar as a data URI so the HTML is fully self-contained
# ---------------------------------------------------------------------------
def _avatar_data_uri(path: pathlib.Path) -> str:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:image/jpeg;base64,{b64}"


def _asset_url(rel_path: str) -> str:
    """Relative URL for a file under the repo, cache-busted with a content hash."""
    path = WORKSPACE / rel_path
    if not path.is_file():
        return rel_path
    digest = hashlib.sha1(path.read_bytes()).hexdigest()[:8]
    return f"{rel_path}?v={digest}"


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

def _split_by_heading(text: str, level: int) -> list[tuple[str, str]]:
    """Return [(heading_text, body_text), ...] for every H{level} in text."""
    prefix = "#" * level + " "
    pattern = re.compile(r"^" + re.escape(prefix) + r"(.+)$", re.MULTILINE)
    parts = pattern.split(text)
    # parts[0] is preamble before first heading; skip it
    result = []
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        result.append((heading, body))
    return result


def _h2_sections(text: str) -> dict[str, str]:
    return {h: b for h, b in _split_by_heading(text, 2)}


def _bold_kv(text: str) -> dict[str, str]:
    """Parse '- **Key:** Value' lines into {key: value}."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*-\s+\*\*(.+?):\*\*\s*(.+)$", line)
        if m:
            result[m.group(1).strip()] = m.group(2).strip()
    return result


def _bullets(text: str) -> list[str]:
    """Parse '- item' lines into a list (skips bold-KV lines)."""
    result = []
    for line in text.splitlines():
        # skip bold-KV lines like '- **Key:** value'
        if re.match(r"^\s*-\s+\*\*.+?\*\*", line):
            continue
        m = re.match(r"^\s*-\s+(.+)$", line)
        if m:
            result.append(m.group(1).strip())
    return result


def _nested_bullets(text: str) -> list[dict]:
    """Parse a two-level '- item' / '  - sub-item' list into [{name, items}]."""
    result: list[dict] = []
    for line in text.splitlines():
        m = re.match(r"^(\s*)-\s+(.+)$", line)
        if not m:
            continue
        if m.group(1) and result:
            result[-1]["items"].append(m.group(2).strip())
        else:
            result.append({"name": m.group(2).strip(), "items": []})
    return result


def _paragraphs(text: str) -> str:
    """Collapse text into paragraphs separated by \\n\\n."""
    blocks = re.split(r"\n{2,}", text.strip())
    joined = []
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if lines:
            joined.append(" ".join(lines))
    return "\n\n".join(joined)


def _prose(text: str) -> str:
    """Body text with bold-KV lines removed, collapsed into paragraphs."""
    kept = [l for l in text.splitlines() if not re.match(r"^\s*-\s+\*\*.+?:\*\*", l)]
    return _paragraphs("\n".join(kept))


def _first_sentence(text: str) -> str:
    """'Did X. Then Y.' → 'Did X.'"""
    head, sep, _ = text.partition(". ")
    return head + "." if sep else text


# -- Section parsers ----------------------------------------------------------

def _strip_angle(s: str) -> str:
    """Strip Markdown autolink angle brackets: <value> → value."""
    s = s.strip()
    if s.startswith("<") and s.endswith(">"):
        return s[1:-1]
    return s


def _display_url(url: str) -> str:
    """https://www.example.com/path/ → example.com/path"""
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


def _parse_person(body: str) -> dict:
    kv = _bold_kv(body)
    title = kv.get("Title", "")
    role, _, focus = title.partition(" — ")
    phone = kv.get("Phone", "")
    linkedin = _strip_angle(kv.get("LinkedIn", ""))
    return {
        "name":     kv.get("Name", ""),
        "title":    title,
        "role":     role.strip(),
        "focus":    focus.strip(),
        "email":    _strip_angle(kv.get("Email", "")),
        "phone":    phone,
        "phone_href": "+" + re.sub(r"\D", "", phone),
        "location": kv.get("Location", ""),
        "linkedin": linkedin,
        "linkedin_display": _display_url(linkedin),
    }


def _parse_education(body: str) -> list[dict]:
    items = []
    for degree, content in _split_by_heading(body, 3):
        kv = _bold_kv(content)
        items.append({
            "degree": degree,
            "school": kv.get("School", ""),
            "detail": kv.get("Detail", ""),
        })
    return items


def _parse_skills(body: str) -> list[dict]:
    groups = []
    for category, content in _split_by_heading(body, 3):
        skills = []
        for line in content.splitlines():
            m = re.match(r"^\s*-\s+(.+?)\s*\|\s*(.+?)\s*\|\s*(\d+)\s*$", line)
            if m:
                level = m.group(2).strip()
                skills.append({
                    "name":  m.group(1).strip(),
                    "level": level,
                    "level_index": LEVELS.index(level) + 1 if level in LEVELS else 0,
                    "pct":   int(m.group(3).strip()),
                })
        if skills:
            groups.append({"category": category, "skills": skills})
    return groups


def _parse_period(period: str, now: float) -> tuple[int, float, bool]:
    """'2021 – 2024' → (2021, 2024.0, False); '2024 – Present' → (2024, now, True)."""
    years = [int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", period)]
    start = years[0] if years else int(now)
    is_current = "present" in period.lower()
    end = now if is_current else float(years[-1] if len(years) > 1 else start + 1)
    return start, end, is_current


def _short_title(title: str) -> str:
    """Label for the timeline: 'Consultant → Senior Consultant' → 'Consultant'."""
    short = title.split(" → ")[0].strip()
    return short.split()[-1] if len(short) > 20 else short


def _parse_work_history(body: str, now: float) -> list[dict]:
    roles = []
    for heading, content in _split_by_heading(body, 3):
        parts = heading.split(" | ", 2)
        period = parts[2].strip() if len(parts) > 2 else ""
        start, end, is_current = _parse_period(period, now)
        title = parts[0].strip()
        roles.append({
            "title":   title,
            "short":   _short_title(title),
            "company": parts[1].strip() if len(parts) > 1 else "",
            "period":  period,
            "start":   start,
            "end":     end,
            "is_current": is_current,
            "bullets": _bullets(content),
        })
    return roles


def _build_timeline(roles: list[dict]) -> list[dict]:
    """Chronological segments for the dimension-line timeline (gaps become breaks)."""
    ordered = sorted(enumerate(roles), key=lambda pair: pair[1]["start"])
    segments: list[dict] = []
    prev_end = None
    for index, role in ordered:
        if prev_end is not None and role["start"] > prev_end:
            segments.append({"kind": "gap", "start": int(prev_end), "end": role["start"]})
        segments.append({
            "kind":  "role",
            "index": index,
            "start": role["start"],
            "end_label": "Now" if role["is_current"] else str(int(role["end"])),
            "span":  round(max(role["end"] - role["start"], 0.5), 2),
        })
        prev_end = role["end"]
    return segments


def _parse_projects(body: str) -> list[dict]:
    projects = []
    for title, content in _split_by_heading(body, 3):
        kv = _bold_kv(content)
        tags_raw = kv.get("Tags", "")
        projects.append({
            "title":    title,
            "featured": kv.get("Featured", "").lower() in ("yes", "true"),
            "status":   kv.get("Status", ""),
            "tags":     [t.strip() for t in tags_raw.split(",") if t.strip()],
            "problem":  kv.get("Problem", ""),
            "solution": kv.get("Solution", ""),
            "tech":     kv.get("Tech", ""),
            "impact":   kv.get("Impact", ""),
            "impact_short": _first_sentence(kv.get("Impact", "")),
            "next":     kv.get("Next", ""),
        })
    return projects


def _parse_ventures(body: str) -> list[dict]:
    ventures = []
    for name, content in _split_by_heading(body, 3):
        kv = _bold_kv(content)
        url = _strip_angle(kv.get("URL", ""))
        ventures.append({
            "name":       name,
            "role":       kv.get("Role", ""),
            "period":     kv.get("Period", ""),
            "status":     kv.get("Status", ""),
            "tagline":    kv.get("Tagline", ""),
            "url":        url,
            "url_display": _display_url(url),
            "logo":       _asset_url(kv.get("Logo", "")) if kv.get("Logo") else "",
            "theme":      kv.get("Theme", ""),
            "summary":    kv.get("Summary", ""),
            "tags":       [t.strip() for t in kv.get("Tags", "").split(",") if t.strip()],
            "highlights": _bullets(content),
        })
    return ventures


def _parse_testimonials(body: str) -> list[dict]:
    groups = []
    for group_name, group_body in _split_by_heading(body, 3):
        quotes = []
        for heading, content in _split_by_heading(group_body, 4):
            parts = heading.split(" | ", 1)
            role = parts[1].strip() if len(parts) > 1 else ""
            year = re.search(r"\b(?:19|20)\d{2}\b", role)
            quotes.append({
                "name":      parts[0].strip(),
                "role":      role,
                "year":      year.group(0) if year else "",
                "highlight": _bold_kv(content).get("Highlight", ""),
                "quote":     _prose(content),
            })
        if quotes:
            groups.append({"group": group_name, "quotes": quotes})
    return groups


def _parse_recognition(body: str) -> list[dict]:
    return [
        {
            "title":  title,
            "issuer": _bold_kv(content).get("Issuer", ""),
            "detail": _prose(content),
        }
        for title, content in _split_by_heading(body, 3)
    ]


def _parse_personality(body: str) -> list[dict]:
    result = []
    for label, content in _split_by_heading(body, 3):
        if " — " in label:
            group = "test"
        elif label.strip().lower() == "family":
            group = "family"
        else:
            group = "style"
        sub_items = [
            {"label": sl, "value": sc.strip()}
            for sl, sc in _split_by_heading(content, 4)
        ]
        system, _, result_label = label.partition(" — ")
        result.append({
            "label": label,
            "system": system.strip(),
            "result": result_label.strip(),
            "value": content.strip(),
            "group": group,
            "sub_items": sub_items,
        })
    return result


def _parse_books(body: str) -> list[dict]:
    books = []
    for heading, content in _split_by_heading(body, 3):
        title, _, author = heading.partition(" — ")
        books.append({"title": title.strip(), "author": author.strip(), "insight": content.strip()})
    return books


def _parse_resume_config(body: str) -> dict:
    kv = _bold_kv(body)
    per_role = [int(n) for n in re.findall(r"\d+", kv.get("Bullets Per Role", ""))]
    return {
        "file_name":           kv.get("File Name", "resume.pdf"),
        "summary":             kv.get("Summary", ""),
        "bullets_per_role":    per_role,
        "skills_per_category": int(kv.get("Skills Per Category", "0") or 0),
    }


# ---------------------------------------------------------------------------
# Main data loader — reads career-data.md
# ---------------------------------------------------------------------------
def load_career_data(md_path: pathlib.Path, today: dt.date | None = None) -> dict:
    text = md_path.read_text(encoding="utf-8")
    sections = _h2_sections(text)
    today = today or dt.date.today()
    now = today.year + (today.timetuple().tm_yday - 1) / 365

    person = _parse_person(sections.get("Person", ""))
    education = _parse_education(sections.get("Education", ""))
    summary = _paragraphs(sections.get("Professional Summary", ""))
    cover_letter = _paragraphs(sections.get("Cover Letter", ""))
    disclaimer = _paragraphs(sections.get("Disclaimer", ""))
    skills = _parse_skills(sections.get("Skills", ""))
    roles = _parse_work_history(sections.get("Work History", ""), now)
    projects = _parse_projects(sections.get("Project Highlights", ""))
    ventures = _parse_ventures(sections.get("Side Ventures", ""))
    testimonials = _parse_testimonials(sections.get("Testimonials", ""))
    recognition = _parse_recognition(sections.get("Recognition", ""))
    hobbies = _nested_bullets(sections.get("Hobbies", ""))
    personality = _parse_personality(sections.get("Personality", ""))
    books = _parse_books(sections.get("Books", ""))
    resume = _parse_resume_config(sections.get("Resume Export", ""))

    return {
        "person":    person,
        "education": education,
        "profile": {
            "summary":      summary,
            "cover_letter": cover_letter,
            "disclaimer":   disclaimer,
            "compiled":     f"{today:%B} {today.day}, {today.year}",
        },
        "skills":       skills,
        "roles":        roles,
        "timeline":     _build_timeline(roles),
        "projects":     projects,
        "ventures":     ventures,
        "testimonials": testimonials,
        "recognition":  recognition,
        "about": {
            "hobbies":     hobbies,
            "personality": personality,
            "books":       books,
        },
        "resume": resume,
        "tabs": [
            {"id": "profile",  "label": "Profile",         "short": "Profile"},
            {"id": "work",     "label": "Work",            "short": "Work"},
            {"id": "ventures", "label": "Side Ventures",   "short": "Ventures"},
            {"id": "about",    "label": "About Me",        "short": "About"},
        ],
    }


# ---------------------------------------------------------------------------
# Legacy hardcoded context (kept for reference — no longer used)
# ---------------------------------------------------------------------------
def build_context(avatar_src: str) -> dict:
    return {
        "person": {
            "name": "Zach Robida",
            "title": "Design Lead — Supply Chain Software & AI-Driven Solutions",
            "email": "robidaz@gmail.com",
            "phone": "+1 (678) 524-3186",
            "location": "Atlanta, GA",
            "linkedin": "https://linkedin.com/in/zach-robida",
            "avatar_src": avatar_src,
        },

        "tabs": [
            {"id": "profile",       "label": "Profile"},
            {"id": "work",          "label": "Work Experience & Projects"},
            {"id": "testimonials",  "label": "Testimonials"},
            {"id": "about",         "label": "About Me"},
        ],

        # ── Tab 1: Profile ──────────────────────────────────────────────────
        "profile": {
            "summary": (
                "Zach Robida is a Design Lead at Manhattan Associates with 8 years of experience "
                "delivering high-impact supply chain software solutions for federal government clients. "
                "He bridges the gap between functional design and technical implementation — "
                "translating complex business requirements into scalable, well-documented solutions "
                "on platforms ranging from cloud-native FedRAMP environments to modern Angular-based "
                "logistics applications. Zach is an automation-first thinker who actively embeds AI "
                "into his workflow, using GitHub Copilot and Claude Sonnet to accelerate design "
                "documentation, reduce manual overhead, and raise the quality bar for his entire team. "
                "Recognized with a Spirit Award for Master Mentor in 2025, he consistently elevates "
                "the consultants around him through structured coaching, delegated ownership, and a "
                "relentless focus on process improvement."
            ),
            "cover_letter": (
                "Dear Hiring Manager,\n\n"
                "I have spent eight years solving hard problems at the intersection of enterprise "
                "software, federal supply chain operations, and rapidly evolving technology — and I "
                "have done it by staying two steps ahead of what is possible.\n\n"
                "At Manhattan Associates, I grew from a new consultant who rebuilt an automated "
                "testing framework from scratch into a Design Lead responsible for multi-million-dollar "
                "project delivery for FEMA. Along the way I designed and shipped a FedRAMP-compliant "
                "cloud vulnerability automation system, led the end-to-end design of a custom State "
                "Portal used during active disaster response, and spearheaded the adoption of a modern "
                "UI component framework that measurably improved both developer velocity and product "
                "quality.\n\n"
                "What sets me apart is not a list of tools — it is an automation-first mindset "
                "combined with genuine curiosity about how systems actually work. I leverage AI daily "
                "as a force multiplier: from generating complex HTML mockups with GitHub Copilot to "
                "building a centralized documentation repository where Claude Sonnet drives the "
                "entire specification pipeline. I do not just adopt new technology — I introduce it "
                "to my teams, train them on it, and build repeatable processes around it.\n\n"
                "I am looking for an organization where technical depth, cross-functional leadership, "
                "and a genuine drive to improve how work gets done are valued. If that sounds like "
                "your team, I would love to have a conversation.\n\n"
                "Zach Robida"
            ),
        },

        "education": [
            {
                "degree": "B.S. in Mechanical Engineering",
                "school": "Clemson University — Clemson, SC",
                "detail": "GPA 3.21 | Certified SolidWorks Professional | Emphasis: Renewable Energy & Machine Design",
            },
            {
                "degree": "Sustainable Cities of Scandinavia Program",
                "school": "Linnaeus University — Kalmar, Sweden",
                "detail": "Summer 2017 | Selected as commencement speaker out of 300 students",
            },
        ],

        # ── Tab 2: Work Experience & Projects ───────────────────────────────
        "skills": [
            {
                "category": "AI & Automation",
                "skills": [
                    {"name": "GitHub Copilot / Claude Sonnet", "level": "Expert",        "pct": 95},
                    {"name": "Python Automation",               "level": "Expert",        "pct": 95},
                    {"name": "Automated Testing (Manhrobo)",    "level": "Expert",        "pct": 95},
                    {"name": "AI Workflow Integration",         "level": "Advanced",      "pct": 85},
                    {"name": "PowerShell Scripting",            "level": "Advanced",      "pct": 80},
                ],
            },
            {
                "category": "Design & UI Systems",
                "skills": [
                    {"name": "Functional / Extension Design",   "level": "Expert",        "pct": 95},
                    {"name": "Figma",                           "level": "Advanced",      "pct": 85},
                    {"name": "Angular / Syncfusion Components", "level": "Intermediate",  "pct": 65},
                    {"name": "UI/UX Mockups & Prototyping",     "level": "Advanced",      "pct": 80},
                ],
            },
            {
                "category": "Programming & Scripting",
                "skills": [
                    {"name": "Python",                          "level": "Expert",        "pct": 95},
                    {"name": "SQL",                             "level": "Advanced",      "pct": 85},
                    {"name": "PowerShell",                      "level": "Advanced",      "pct": 80},
                    {"name": "HTML / CSS / JavaScript",         "level": "Intermediate",  "pct": 65},
                    {"name": "Jinja2 Templating",               "level": "Intermediate",  "pct": 65},
                ],
            },
            {
                "category": "Systems & Architecture",
                "skills": [
                    {"name": "AWS (EC2, S3, SSM, Athena)",      "level": "Advanced",      "pct": 80},
                    {"name": "FedRAMP / Security Compliance",   "level": "Advanced",      "pct": 80},
                    {"name": "Manhattan SCPP / MASC / MATM",    "level": "Expert",        "pct": 95},
                    {"name": "Windows Server Administration",   "level": "Intermediate",  "pct": 65},
                ],
            },
            {
                "category": "Data & Analysis",
                "skills": [
                    {"name": "Jira / Confluence",               "level": "Expert",        "pct": 95},
                    {"name": "SQL Query Development",           "level": "Advanced",      "pct": 85},
                    {"name": "Excel / Macro Development",       "level": "Advanced",      "pct": 80},
                    {"name": "Amazon Athena / Data Pipelines",  "level": "Intermediate",  "pct": 65},
                ],
            },
            {
                "category": "Tools & Platforms",
                "skills": [
                    {"name": "WebInspect / Nessus (DAST/SAST)", "level": "Advanced",      "pct": 80},
                    {"name": "Figma",                           "level": "Advanced",      "pct": 85},
                    {"name": "Git / GitHub",                    "level": "Advanced",      "pct": 80},
                    {"name": "ServiceNow / ServiceDesk",        "level": "Intermediate",  "pct": 60},
                ],
            },
        ],

        "roles": [
            {
                "title":   "Design Lead",
                "company": "Manhattan Associates — PSO Government Division",
                "period":  "2024 – Present",
                "bullets": [
                    "Lead end-to-end functional design for FEMA's MATM/MASC platform upgrade, authoring the Solution Design Document and orchestrating 120+ slide design overview presentations delivered to FEMA TMD stakeholders.",
                    "Pioneered the adoption of GitHub Copilot and Claude Sonnet across the team, introducing AI-driven workflows for design documentation, mockup generation, and gap analysis — measurably reducing spec authoring time.",
                    "Built a centralized, version-controlled documentation repository with Jinja2-based automation tooling that scaffolds new functional specs on demand, enforcing consistent standards across the entire implementation pipeline.",
                    "Spearheaded the adoption of the Syncfusion Angular UI framework and Figma for the LogX1 application, reducing developer-functional back-and-forth and delivering a higher-quality product within budget.",
                    "Mentored a rotating cast of consultants through structured design reviews, open-door coaching, and delegated extension spec ownership — earning a Q4 2025 Spirit Award for Master Mentor.",
                    "Completed 18 campus recruiting interviews (top 5 company-wide) while maintaining full delivery responsibilities.",
                ],
            },
            {
                "title":   "Senior Consultant → Design Lead",
                "company": "Manhattan Associates — PSO Government Division",
                "period":  "2021 – 2024",
                "bullets": [
                    "Served as sole Design Lead for the $1M+ FEMA State Portal project on the LogX1 Angular platform, owning all design documentation, scope management, and client-facing presentations from kick-off through delivery.",
                    "Led the design of a custom Capacity Finder solution (~$600K) enabling mass bid solicitation and awarding for FEMA transportation equipment and lanes, facilitating in-person stakeholder design sessions to achieve conceptual design sign-off.",
                    "Took full ownership of the LSCMS monthly release process — revamped Jira dashboards, established bi-weekly defect prioritization cadence, and managed the full CAB compliance trail that withstood FedRAMP audit scrutiny.",
                    "Served as FEMA client liaison for change requests, Tier 3 support, and the Cloud IPT; traveled bi-monthly to FEMA HQ and provided extended on-site hurricane response support during Hurricane Ian.",
                    "Designed and delivered the Parcel Carrier API Integration projects (UPS, FedEx, USPS, DHL) as both PM and design lead, achieving SPI of 1.0 on a $90K budget.",
                ],
            },
            {
                "title":   "Consultant → Senior Consultant",
                "company": "Manhattan Associates — PSO Government Division",
                "period":  "2018 – 2021",
                "bullets": [
                    "Designed and developed Manhrobo, a Python-based automated testing framework that replaced 80% of manual consultant testing — reducing a full regression cycle from one week of 6 consultants' work to 30 minutes.",
                    "Architected a fully autonomous DAST vulnerability detection and reporting pipeline on AWS (WebInspect + Nessus + S3 + Athena + Jira), saving hundreds of hours of manual vulnerability management per year.",
                    "Led FedRAMP High cloud migration for FEMA's LSCMS solution, pioneering all Windows server hardening procedures, GPO-based DISA STIG alignment, and continuous monitoring SOPs.",
                    "Built the SCPP-Configurator tool in Python + JDBC to automatically detect configuration discrepancies across environments, eliminating a major source of upgrade-related defects.",
                    "Developed 23 of 40 extension specification documents during the 2019 upgrade cycle, spanning 6 application components — establishing a personal baseline as the team's most prolific functional designer.",
                ],
            },
            {
                "title":   "Manufacturing Engineering Co-Op",
                "company": "Itron, Inc. — West Union, SC",
                "period":  "2015 – 2016",
                "bullets": [
                    "Sole mechanical engineer on a Kaizen team; designed custom ESD workstations while managing a $30,000 budget.",
                    "Designed and implemented automated test equipment using precision load cells and a Unitronics PLC/HMI, reducing manual process time by up to 50%.",
                ],
            },
        ],

        "projects": [
            {
                "title":   "Manhrobo — Automated Testing Framework",
                "tags":    ["Python", "Automation", "FedRAMP", "AWS"],
                "problem": "Manual regression testing required 6 consultants a full week per cycle. Monthly patching made this schedule untenable.",
                "solution": "Designed and built Manhrobo, a lightweight portable Python framework purpose-built for supply chain application testing, with randomized input data, auto-generated logs, and cloud-native execution via AWS SSM.",
                "tech":    "Python (OOP), AWS SSM, Robot Framework, REST/JDBC integrations, CI execution pipeline",
                "impact":  "Reduced full regression cycle from ~240 consultant-hours to 30 minutes. Eliminated 70+ consultant-hours per monthly patch cycle across 10+ environments. Replaced ~80% of all manual consultant testing.",
            },
            {
                "title":   "FedRAMP Cloud Vulnerability Automation Pipeline",
                "tags":    ["Python", "AWS", "Security", "FedRAMP", "WebInspect"],
                "problem": "All DAST vulnerability scanning, reporting, and Jira ticket creation was fully manual, creating compliance risk and hundreds of hours of analyst overhead per year.",
                "solution": "Designed a fully autonomous vulnerability detection and reporting framework: parallel WebInspect scans feed auto-exported results to S3, trigger Jira ticket creation, and populate Amazon Athena for POA&M and continuous-monitoring reports.",
                "tech":    "Python, AWS S3 / Athena, WebInspect, Nessus, Jira API, PowerShell",
                "impact":  "Saved hundreds of annual hours on vulnerability management. Provided a compliant, auditable evidence trail that supported FEMA's FedRAMP High authorization.",
            },
            {
                "title":   "FEMA State Portal — LogX1 Angular Platform",
                "tags":    ["Design Lead", "Angular", "Syncfusion", "Figma", "$1M+ Project"],
                "problem": "FEMA needed extended LSCMS visibility for State Emergency Management Associations, requiring a custom portal with a novel inventory model entirely decoupled from the existing ASN/Order flow.",
                "solution": "Served as sole Design Lead, authoring the Conceptual Design Document, designing a custom POD inventory snapshot data model, and creating a data access control layer for state-level companies — all on the new Angular/Syncfusion platform.",
                "tech":    "Manhattan SCPP / LogX1, Angular, Syncfusion, Figma, extension spec framework",
                "impact":  "Delivered on time with scope held near-perfectly to original plan. Client POCs expressed satisfaction with solution quality. Laid the foundation for future LogX1 expansion.",
            },
            {
                "title":   "AI-Driven Documentation Repository (Current)",
                "tags":    ["GitHub Copilot", "Claude Sonnet", "Python", "Jinja2", "AI"],
                "problem": "Functional design documentation was inconsistent, repetitive to scaffold, and disconnected from the development pipeline — creating delays and quality variance across projects.",
                "solution": "Designed and built a centralized, version-controlled documentation repository with Jinja2-based automation tooling that scaffolds new specs on demand. Custom GitHub Copilot instructions and Claude Sonnet-powered agents are embedded directly in the repo as live context, driving high-quality output at scale.",
                "tech":    "Python, Jinja2, GitHub Copilot, Claude Sonnet 4.6, Markdown, Git",
                "impact":  "Eliminated repetitive document setup, enforced consistent specification standards, and measurably accelerated functional documentation throughput across the implementation team.",
            },
            {
                "title":   "Syncfusion + Figma Design System (LogX1)",
                "tags":    ["Figma", "Syncfusion", "Angular", "UI/UX", "Process Improvement"],
                "problem": "Significant gap between design intent and developer output on the LogX1 Angular application. Developers lacked fidelity mockups; the team had no reusable component library.",
                "solution": "Independently identified and prototyped the Syncfusion Angular component framework, built a business case with long-term cost analysis, convinced leadership to adopt it, and then integrated components into a Figma library for the team.",
                "tech":    "Figma, Syncfusion Angular, LogX1 application platform",
                "impact":  "Reduced developer/functional back-and-forth on UI issues during build and test phases. Phase 4 design and functional output quality measurably exceeded Phase 3. Became the standard design workflow for the team.",
            },
        ],

        # ── Tab 3: Testimonials ─────────────────────────────────────────────
        "testimonials": [
            {
                "group": "Managers",
                "quotes": [
                    {
                        "quote": "Zach is off to an outstanding start in his career at MA. He has made contributions beyond what is expected of a new consultant — a very quick learner, a hard worker, and able to understand complex systems.",
                        "name":  "Ellie Kelly",
                        "role":  "Manager, 2018 Year-End Review",
                    },
                    {
                        "quote": "Zach has continued to grow in many areas of his professional and technical development. He has proven that he can work on some of the most challenging tasks and master them as quickly as anyone. He has continued to show some of the best initiative I've seen at Manhattan.",
                        "name":  "Michaela McGinty",
                        "role":  "Manager, 2019 Year-End Review",
                    },
                    {
                        "quote": "Zach played a critical role in our COVID response for FEMA. He worked long hours and solved difficult functional problems. His input will be invaluable as we move into 2021 with many new projects and initiatives on the horizon.",
                        "name":  "Thomas Adams",
                        "role":  "Manager, 2020 Year-End Review",
                    },
                    {
                        "quote": "Zach had another great year and is performing well-beyond the role of a Senior Consultant. His FEMA solution knowledge, technical and design skills, and ability to work well within our team makes him an invaluable resource to our department and Manhattan as a whole.",
                        "name":  "Thomas Adams",
                        "role":  "Manager, 2023 Year-End Review",
                    },
                    {
                        "quote": "Zach has had a great first year as a Design Lead — not just leading design phases, but spearheading internal initiatives to help us deliver higher-quality solutions more quickly and efficiently. These efforts were impactful from both a design and development perspective.",
                        "name":  "Thomas Adams",
                        "role":  "Manager, 2024 Year-End Review",
                    },
                    {
                        "quote": "Zach ramped up on the MATM solution, helped translate FEMA's SCPP solution into MATM, and established key contacts throughout the company to enhance his skills and progress his projects forward. In the coming year, Zach will be critical in designing FEMA's MASC solution and driving the project to a successful 2027 go-live.",
                        "name":  "Thomas Adams",
                        "role":  "Manager, 2025 Year-End Review",
                    },
                ],
            },
            {
                "group": "Peers & Colleagues",
                "quotes": [
                    {
                        "quote": "He has exhibited a talent I have only seen in two or three new consultants over my time with MA. Certainly has plenty to learn, but is someone we 100% want to keep around.",
                        "name":  "Matt Perry",
                        "role":  "Senior Consultant (quoted in 2018 Review)",
                    },
                    {
                        "quote": "Zach has done a superb job in this area. His contributions to automated testing go far above expectations.",
                        "name":  "Matt Perry",
                        "role":  "Senior Consultant (quoted in 2018 Review)",
                    },
                    {
                        "quote": "Zach has been knocking the spec updates and creation for parcel tracking out of the park. He's been taking initiative to get them completed, asking questions when needed, and really has been crucial to the successful design of the project.",
                        "name":  "Peer Consultant",
                        "role":  "Quoted in 2020 Year-End Review",
                    },
                ],
            },
            {
                "group": "Spirit Awards & Recognition",
                "quotes": [
                    {
                        "quote": "Zach received the Q4 2025 Spirit Award for Master Mentor — recognized for building durable design instincts across the consulting team through structured coaching, delegated ownership, and an open-door approach to knowledge transfer.",
                        "name":  "Manhattan Associates",
                        "role":  "Q4 2025 Spirit Award — Master Mentor",
                    },
                    {
                        "quote": "Completed 18 campus recruiting interviews in Fall 2025 — ranking in the top 5 interviewers company-wide — demonstrating sustained commitment to bringing top talent into the organization.",
                        "name":  "Manhattan Associates",
                        "role":  "2025 Recruiting Recognition",
                    },
                ],
            },
        ],

        # ── Tab 4: About Me ─────────────────────────────────────────────────
        "about": {
            "hobbies": [
                "Woodworking",
                "Cutting & Charcuterie Boards",
                "Commissioned Projects",
                "DIY Home Projects",
                "Carpentry",
                "Bathroom Renovations",
                "Tiling & Electrical Work",
                "Family",
                "Cavalier King Charles Spaniels",
            ],
            "personality": [
                {
                    "label": "Problem Approach",
                    "value": "Identifies inefficiencies before being asked, then builds systematic solutions rather than one-off fixes. Driven by a belief that the best way to keep doing interesting work is to make the current work better.",
                },
                {
                    "label": "Learning Style",
                    "value": "Learns by doing and by mapping knowledge gaps to the people who have already solved the problem. Comfortable going deep on technical topics outside his formal background — mechanical engineering to Python to AI workflows.",
                },
                {
                    "label": "Leadership",
                    "value": "Leads through enablement rather than authority. Prefers to delegate, review, and develop rather than do it himself — because a team of skilled people scales infinitely better than one person who does everything.",
                },
                {
                    "label": "Work Style",
                    "value": "Automation-first. Openly curious about AI as a practical accelerant. Brings structured thinking to ambiguous problems and communicates with a bias toward clarity and brevity.",
                },
                {
                    "label": "Family",
                    "value": "Married to Molly McCullough Robida. Two Cavalier King Charles Spaniels: Nova and Bentley.",
                },
            ],
            "books": [
                {
                    "title":   "The Singularity Is Near / The Singularity Is Nearer — Ray Kurzweil",
                    "insight": "Technology compounds. Understanding the trajectory of exponential growth changes how you think about what is coming — and how fast.",
                },
                {
                    "title":   "Nexus — Yuval Noah Harari",
                    "insight": "Information networks have always shaped civilization. AI is the latest — and most powerful — iteration of that pattern.",
                },
                {
                    "title":   "Sapiens & Homo Deus — Yuval Noah Harari",
                    "insight": "Where we came from defines the hidden assumptions we carry into the future. Understanding history is the prerequisite for designing what comes next.",
                },
                {
                    "title":   "The Master Algorithm — Pedro Domingos",
                    "insight": "ML is not magic — it is a search for a unifying learning framework. Demystifying the mechanism makes you a better practitioner.",
                },
                {
                    "title":   "Scary Smart — Mo Gawdat",
                    "insight": "The question is not whether AI becomes capable, but what values we embed in it along the way. Agency matters now, not later.",
                },
                {
                    "title":   "Smart Brevity — VandeHei, Allen & Schwartz",
                    "insight": "Saying more with less is a skill, not a shortcut. Respecting the reader's time is the foundation of effective communication.",
                },
                {
                    "title":   "The Five Dysfunctions of a Team — Patrick Lencioni",
                    "insight": "Trust is the root. Every team dysfunction traces back to an unwillingness to be vulnerable. Fix the root, not the symptoms.",
                },
                {
                    "title":   "The First Time Manager — Belker, McCormick & Topchik",
                    "insight": "Managing people is a craft, not a promotion. The shift from doing to enabling is the hardest and most important transition in a career.",
                },
                {
                    "title":   "Freakonomics — Levitt & Dubner",
                    "insight": "Incentives explain almost everything. Look at the data, question the conventional narrative, and find the hidden lever.",
                },
                {
                    "title":   "Conscious — Annaka Harris",
                    "insight": "Consciousness may be far more fundamental — and far stranger — than our intuitions suggest. Staying humble about what we don't know keeps thinking sharp.",
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def _make_thumb(pdf: pathlib.Path, dest: pathlib.Path) -> None:
    """Render page one of the résumé as a small PNG for the header (needs pdftoppm)."""
    import shutil
    import subprocess
    if not pdf.is_file() or (dest.is_file() and dest.stat().st_mtime >= pdf.stat().st_mtime):
        return
    if not shutil.which("pdftoppm"):
        print("WARNING: pdftoppm not found; the header uses the full-size preview instead.")
        return
    subprocess.run(["pdftoppm", "-png", "-singlefile", "-scale-to-x", "336", "-scale-to-y", "-1",
                    str(pdf), str(dest.with_suffix(""))], check=True, timeout=30)


def _site_assets(resume: dict) -> dict:
    """Cache-busted URLs for the files the page links to (call after the PDF build)."""
    pdf_rel = f"assets/resume/{resume['file_name']}"
    preview_rel = f"assets/resume/{RESUME_PREVIEW_NAME}"
    thumb_rel = f"assets/resume/{RESUME_THUMB_NAME}"
    _make_thumb(WORKSPACE / pdf_rel, WORKSPACE / thumb_rel)
    return {
        "resume_pdf":     _asset_url(pdf_rel) if (WORKSPACE / pdf_rel).is_file() else "",
        "resume_preview": _asset_url(preview_rel) if (WORKSPACE / preview_rel).is_file() else "",
        "resume_thumb":   _asset_url(thumb_rel) if (WORKSPACE / thumb_rel).is_file() else "",
        "viewer_js":      _asset_url("assets/js/resume-viewer.js"),
        "viewer_css":     _asset_url("assets/css/resume-viewer.css"),
        "masthead_js":    _asset_url("assets/js/masthead-arcs.js"),
        "font_archivo":   _asset_url("assets/fonts/archivo-variable.woff2"),
        "font_roboto":    _asset_url("assets/fonts/roboto-800.woff2"),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render index.html and the résumé PDF from career-data.md.")
    parser.add_argument("--skip-pdf", action="store_true",
                        help="Render index.html only and keep the existing résumé PDF.")
    args = parser.parse_args(argv)

    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError:
        print("ERROR: jinja2 not installed. Run: pip install -r requirements.txt")
        sys.exit(1)

    # Load all content from career-data.md
    context = load_career_data(DATA_PATH)

    # Embed the profile picture as a self-contained data URI
    context["person"]["avatar_src"] = _avatar_data_uri(AVATAR_PATH)

    # One-page résumé PDF + preview image (assets/resume/)
    if not args.skip_pdf:
        from resume_pdf import build_resume
        build_resume(context, WORKSPACE)

    context["assets"] = _site_assets(context["resume"])

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_PATH.parent)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(TEMPLATE_PATH.name)
    html = template.render(**context)

    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Generated: {OUTPUT_PATH}")
    print(f"  Source:   {DATA_PATH}")


if __name__ == "__main__":
    main()
