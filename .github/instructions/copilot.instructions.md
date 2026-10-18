---
applyTo: "**"
---

# Career Builder – AI Instructions

## Purpose

This repository is a structured system for transforming raw career data into a polished, multi-tab HTML showcase.

The AI must act as a **data synthesizer + narrative builder + UI content generator**.

The final output is not just text—it is **content intentionally shaped for an HTML viewer** using predefined tabs and components.

---

## Repository Awareness (CRITICAL)

The AI MUST understand and use the repo structure:

career-showcase/
├── documentation/ (private, gitignored, read-only source material)
│ ├── additional information/
│ ├── eoy_reviews/
│ └── resumes/
├── career-data.md (compiled content — the single source for the site and the PDF)
├── scripts/
│ ├── generate_career_showcase.py (career-data.md → index.html; calls resume_pdf.py)
│ ├── resume_pdf.py (one-page résumé PDF + preview image via headless Chrome)
│ └── templates/
│   ├── career-showcase.html.j2 (site layout)
│   └── resume.html.j2 (PDF print layout)
├── assets/ (fonts, venture logos, résumé PDF, viewer script)
├── index.html (generated — never edit by hand)
├── visuals.md

Build: edit career-data.md, then run `.venv/bin/python scripts/generate_career_showcase.py` (`--skip-pdf` keeps the existing PDF). See README.md.

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

#### 4. visuals.md

Defines the **FINAL OUTPUT STRUCTURE**.

This file is LAW.

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

The AI MUST structure output according to:

# Tab 1: Profile (includes the exportable résumé)

# Tab 2: Work Experience & Projects

# Tab 3: Side Ventures

# Tab 4: About Me

No exceptions.

---

## Tab-Specific Instructions

---

### 🔹 Tab 1: Profile

Purpose: Immediate first impression. High signal. No fluff.

Include:

- Name
- Job Title (modern, slightly elevated but accurate)
- Professional Summary (3–5 sentences max)
- Education (clean, minimal)
- Contact Info (from JSON)
- Cover Letter (tailored, confident, not generic)
- Exportable Résumé: one-page US Letter PDF generated from career-data.md (`## Resume Export` sets the PDF summary and bullets per role), with a download link and an embedded PDF viewer (Syncfusion, loaded only when opened). Keep it to one page, structurally clean, ATS-friendly real text.

#### Rules:

- This is NOT a resume summary
- This is positioning
- Must emphasize:
  - AI usage
  - automation mindset
  - technical + business bridge
  - leadership trajectory

---

### 🔹 Tab 2: Work Experience & Projects

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

---

#### Section B: HTML Resume

Rewrite the resume using:

- clean, modern structure
- bullet-driven impact statements
- outcome-first phrasing

Each role should include:

- role + company
- timeframe
- 3–6 high-impact bullets

#### Bullet Rules:

Each bullet must follow:

**[Impact] + [What you did] + [How/tech used]**

Example:
"Reduced manual testing effort by 70% by designing and implementing a Python-based automation framework."

---

#### Section C: Project Highlights

Pull from EOY reviews and extract **top-tier projects only**.

Each project should include:

- Title
- Problem
- Solution
- Technical Approach
- Outcome/Impact

Focus heavily on:

- automation
- AI usage
- system design
- process improvement
- cross-team influence

---

The exportable PDF résumé lives on Tab 1 and is built from the same work history.

---

### 🔹 Tab 3: Side Ventures

Purpose: show what Zach builds outside the day job. Brief by design; the venture websites carry the detail.

Include, per venture:

- logo and brand colors (respect each brand's rules, e.g. Holigram's mark only on its dark navy)
- role and timeframe
- 1–2 sentence description and 2–3 highlights
- a link out to the venture's website

#### Rules:

- Only publicly shareable facts. Never use investor or NDA material (pricing, market sizing, funding, user counts), and never claim a legal entity or trademark that doesn't exist
- Don't take credit for a venture's results beyond Zach's actual role

---

### 🔹 Tab 4: About Me — Testimonials

Testimonials are kept in career-data.md but are not currently shown on the site (removed at Zach's request). If they return, use accordions: a punchy pull quote in the header, the full quote on expand. Awards and recognition sit beside them, stated plainly (not as quotes).

Source: EOY reviews

This is where most people screw up—you won’t.

#### Rules:

- Extract **REAL sentiment**, not corporate filler
- Rewrite into **clean, punchy quotes**
- Remove jargon
- Keep authenticity

#### Good Example:

"Zach consistently identifies problems before they surface and builds solutions that make the entire team more efficient."

#### Bad Example:

"Zach is a valuable contributor and team player."

Group testimonials by:

- Managers
- Peers
- Leadership / Stakeholders

---

### 🔹 Tab 4: About Me — Personal

This is where you become human (without being cringe).

Pull from:

- hobbies.md
- relevant_books.md
- other personal files

Include:

#### Sections:

**1. Personal Interests**

- hobbies
- creative outlets
- non-work passions

**2. Influential Books**

- list + 1-liner insight per book
- focus on thinking, not summary

**3. Personality / Work Style**

- how you think
- how you approach problems
- how you work with others

#### Tone:

- natural
- confident
- slightly conversational
- not corporate

---

## AI Positioning Rules (Important)

You are NOT writing for:

- HR checklists
- generic resumes

You ARE writing for:

- hiring managers
- technical leaders
- decision makers

---

## Key Narrative Themes to Emphasize

When supported by data, reinforce:

- Rapid technical learning ability
- Automation-first mindset
- AI as a practical tool (not hype)
- Strong system-level thinking
- Ability to bridge:
  - business ↔ technical
  - design ↔ implementation
- Leadership through enablement (not authority)
- Process improvement at scale

---

## Writing Rules

### Do:

- Be concise
- Be specific
- Show impact
- Use strong verbs
- Combine evidence across sources

### Do NOT:

- Repeat content across tabs
- Use generic phrases
- Over-explain obvious things
- Inflate titles or responsibilities
- Write long paragraphs

---

## Synthesis Rules

### 1. Merge overlapping data

If multiple sources say similar things → combine into stronger insight

### 2. Prefer patterns over one-offs

Repeated strengths > isolated wins

### 3. Upgrade weak wording

If evidence is strong but wording is weak → improve it

---

## HTML Awareness

All output should be:

- modular
- sectioned
- easy to map into components
- visually scannable

Think:

- cards
- sections
- panels
- tabs

NOT:

- essays

---

## Final Quality Check

Before completing output, ensure:

- Each tab is clearly defined
- No redundant content across tabs
- Strong technical positioning is present
- AI + automation are meaningfully included
- Output feels like a premium professional showcase

---

## One-Line Standard

The final product should feel like:

"A high-performing technical design leader who leverages AI and automation to solve complex problems and elevate team output."

If it doesn’t hit that—rewrite it.
