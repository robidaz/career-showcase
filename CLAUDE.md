# Career Builder – Claude Instructions

## Purpose

This repository is a structured system for transforming raw career data into a polished, multi-tab HTML showcase.

Act as a **data synthesizer + narrative builder + UI content generator**.

The final output is not just text — it is **content intentionally shaped for an HTML viewer** using predefined tabs and components.

---

## Repository Structure (CRITICAL)

```
career-showcase/
├── documentation/                  (private, gitignored, read-only source material)
│   ├── additional information/
│   ├── eoy_reviews/
│   └── resumes/
├── career-data.md                  (compiled content — the single source for the site and the PDF)
├── scripts/
│   ├── generate_career_showcase.py (parses career-data.md → index.html, calls resume_pdf.py)
│   ├── resume_pdf.py               (one-page résumé PDF + preview image via headless Chrome)
│   ├── make_resume_fonts.py        (one-time: static Archivo instances for the PDF)
│   └── templates/
│       ├── career-showcase.html.j2 (site layout, CSS, tab script)
│       └── resume.html.j2          (print layout for the PDF)
├── assets/                         (fonts, venture logos, résumé PDF, viewer script)
├── index.html                      (generated — never edit by hand)
├── server.js                       (Express: serves index.html + assets/)
├── visuals.md
```

### Build

Edit `career-data.md`, then run `.venv/bin/python scripts/generate_career_showcase.py` (add `--skip-pdf` to leave the PDF alone). See README.md for setup.

### Data Sources

#### 1. EOY Reviews (`documentation/eoy_reviews/`)

Primary source of:
- accomplishments
- impact
- leadership evidence
- technical growth
- testimonials (raw material)

#### 2. Resume (`documentation/resumes/`)

Primary source of:
- roles
- timeline
- education
- baseline skills

#### 3. Additional Information (`documentation/additional information/`)

Used for:
- contact info
- hobbies
- personality
- books
- personal narrative
- current work context

#### 4. `visuals.md`

Defines the **FINAL OUTPUT STRUCTURE**. This file is LAW.

---

## Core Objective

Transform all available data into a **cohesive, high-impact professional showcase** optimized for:
- HTML rendering
- recruiter readability
- executive credibility
- technical depth
- storytelling clarity

---

## Output Must Map to UI Tabs

Structure all output according to these four tabs. No exceptions.

- Tab 1: Profile (includes the exportable résumé)
- Tab 2: Work (▾ menu: Experience, Projects, Skills)
- Tab 3: Side Ventures
- Tab 4: About Me

---

## Tab-Specific Instructions

### Tab 1: Profile

Purpose: Immediate first impression. High signal. No fluff.

Include:
- Name
- Job Title (modern, slightly elevated but accurate)
- Professional Summary (3–5 sentences max)
- Education (clean, minimal)
- Contact Info (from JSON)
- Cover Letter (on hold: kept in career-data.md, not shown on the site)
- Exportable Résumé (see below)

Exportable Résumé:
- One-page US Letter PDF generated from `career-data.md` (`## Resume Export` controls the PDF summary and bullets per role)
- A small thumbnail in the header title block opens the PDF viewer (Syncfusion, loaded only when opened), which has Download
- Must stay concise enough for one page and structurally clean (ATS-friendly real text)

Rules:
- This is NOT a resume summary — this is positioning
- Must emphasize: AI usage, automation mindset, technical + business bridge, leadership trajectory

---

### Tab 2: Work Experience & Projects

This is the core of the entire system.

#### Section A: Skills with Proficiency

Group skills into categories:
- AI & Automation
- Programming & Scripting
- Data & Analysis
- Design & UI Systems
- Systems & Architecture
- Tools & Platforms

Each skill should include:
- proficiency level (Beginner / Intermediate / Advanced / Expert)
- optional short justification if meaningful

#### Section B: HTML Resume

Rewrite the resume using:
- clean, modern structure
- bullet-driven impact statements
- outcome-first phrasing

Each role should include:
- role + company
- timeframe
- 3–6 high-impact bullets

Bullet format: **[Impact] + [What you did] + [How/tech used]**

Example: "Reduced manual testing effort by 70% by designing and implementing a Python-based automation framework."

#### Section C: Project Highlights

Pull from EOY reviews and extract **top-tier projects only**.

Each project should include:
- Title
- Problem
- Solution
- Technical Approach
- Outcome/Impact

Focus heavily on: automation, AI usage, system design, process improvement, cross-team influence.

The exportable PDF résumé lives on Tab 1 and is built from the same work history.

---

### Tab 3: Side Ventures

Purpose: show what Zach builds outside the day job. Brief by design; the venture websites carry the detail.

Include, per venture:
- logo and brand colors (respect each brand's rules, e.g. Holigram's mark only on its dark navy)
- role and timeframe
- 1–2 sentence description and 2–3 highlights
- a link out to the venture's website

Rules:
- Only publicly shareable facts. Never use investor or NDA material (pricing, market sizing, funding, user counts), and never claim a legal entity or trademark that doesn't exist
- Don't take credit for a venture's results beyond Zach's actual role

---

### Tab 4: About Me — Testimonials

Testimonials are kept in `career-data.md` but are not currently shown on the site (removed at Zach's request). If they return, use accordions: a punchy pull quote in the header, the full quote on expand.

Source: EOY reviews

Rules:
- Extract **REAL sentiment**, not corporate filler
- Rewrite into **clean, punchy quotes**
- Remove jargon
- Keep authenticity

Good example: "Zach consistently identifies problems before they surface and builds solutions that make the entire team more efficient."

Bad example: "Zach is a valuable contributor and team player."

Group testimonials by:
- Managers
- Peers
- Leadership / Stakeholders

Awards and recognition sit beside the testimonials, stated plainly (not as quotes).

---

### Tab 4: About Me — Personal

Pull from hobbies.md, relevant_books.md, and other personal files.

Include:

**1. Personal Interests** — hobbies, creative outlets, non-work passions

**2. Influential Books** — list + 1-liner insight per book (focus on thinking, not summary)

**3. Personality / Work Style** — how you think, approach problems, and work with others

Tone: natural, confident, slightly conversational, not corporate.

---

## Audience

Writing for:
- hiring managers
- technical leaders
- decision makers

NOT for:
- HR checklists
- generic resumes

---

## Key Narrative Themes

When supported by data, reinforce:
- Rapid technical learning ability
- Automation-first mindset
- AI as a practical tool (not hype)
- Strong system-level thinking
- Ability to bridge business ↔ technical and design ↔ implementation
- Leadership through enablement (not authority)
- Process improvement at scale

---

## Writing Rules

Do:
- Be concise
- Be specific
- Show impact
- Use strong verbs
- Combine evidence across sources

Do NOT:
- Repeat content across tabs
- Use generic phrases
- Over-explain obvious things
- Inflate titles or responsibilities
- Write long paragraphs

---

## Synthesis Rules

1. **Merge overlapping data** — if multiple sources say similar things, combine into a stronger insight
2. **Prefer patterns over one-offs** — repeated strengths > isolated wins
3. **Upgrade weak wording** — if evidence is strong but wording is weak, improve it

---

## HTML Awareness

All output should be modular, sectioned, and easy to map into components:
- cards
- sections
- panels
- tabs

NOT essays.

---

## Final Quality Check

Before completing output, verify:
- Each tab is clearly defined
- No redundant content across tabs
- Strong technical positioning is present
- AI + automation are meaningfully included
- Output feels like a premium professional showcase

The final product should feel like: "A high-performing technical design leader who leverages AI and automation to solve complex problems and elevate team output." If it doesn't hit that — rewrite it.
