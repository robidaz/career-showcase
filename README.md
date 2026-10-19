# Career Showcase

Zach Robida's career site. It is one static page, `index.html`, generated from `career-data.md`, plus a one-page PDF résumé built from the same data.

## Update the site

1. Edit `career-data.md`. All of the copy lives there.
2. Rebuild:

   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # first time only
   .venv/bin/python scripts/generate_career_showcase.py                  # site + résumé PDF + share images
   .venv/bin/python scripts/generate_career_showcase.py --skip-pdf       # site only, keep the current PDF and share images
   ```

3. Commit `index.html` and anything that changed under `assets/`.

The PDF step needs Chrome or Chromium. The script checks your PATH and the Playwright/Puppeteer browser caches; set `CHROME_PATH` to use a specific binary. `pdfinfo` and `pdftoppm` (poppler-utils) are optional: they confirm the PDF is one page and render the preview image on the Profile tab.

## Preview locally

```bash
npm install --no-package-lock
npm start              # http://localhost:3000
```

## Résumé viewer (Syncfusion)

"View résumé" opens the PDF in an embedded Syncfusion PDF Viewer, version 34.2.9 from Syncfusion's CDN. Nothing from Syncfusion loads until someone opens the viewer.

Syncfusion shows a license banner unless the right key is registered, and since v31 the PDF Viewer needs its own **PDF Viewer SDK** key. A UI Components key alone (like Holigram's) is not enough. The viewer detects the banner, removes it, and falls back, so visitors never see it.

This repo is public, so the key stays out of git:

- **Local:** put `SYNCFUSION_LICENSE_KEY=<ui key>;<pdf viewer key>` in `.env` (gitignored). `server.js` reads it. Several keys can be joined with `;`.
- **Production:** set the same value as an environment variable on the host, for example `heroku config:set SYNCFUSION_LICENSE_KEY=...`. Leave it unset until you have the PDF Viewer SDK key. Otherwise every open downloads about 2 MB of Syncfusion before falling back.

`server.js` hands the key to the page at `/syncfusion-license.js`. Without a key, or on a static host with no server, the viewer falls back to a preview image of the page plus a download link. Keys are tied to a major version, so stay on a 34.x CDN version unless you generate new keys.

When licensed, the first open downloads about 3.8 MB from Syncfusion's CDN (scripts, CSS, and the PDF engine). After that the browser caches it.

## Layout

| Path | What it is |
| --- | --- |
| `career-data.md` | All content: profile, work history, projects, side ventures, testimonials, résumé settings. |
| `scripts/generate_career_showcase.py` | Parses `career-data.md`, renders `index.html`, and calls `resume_pdf.py`. |
| `scripts/resume_pdf.py` | Prints `assets/resume/` (PDF and preview image) with headless Chrome. |
| `scripts/share_card.py` | Screenshots the link-preview images in `assets/share/` (1200×630 `share-card.png` for texts and social posts, 180×180 `apple-touch-icon.png`). Preview tags need absolute URLs, so they use **Site** in `career-data.md`; change it there if the site moves to a custom domain. |
| `scripts/make_resume_fonts.py` | One-time tool (needs `pip install fonttools`) that cuts the static Archivo instances in `assets/fonts/resume/`. The PDF uses static fonts so its text layer has real spaces for applicant-tracking parsers. Re-run only if the résumé needs characters outside the subset; the build warns when that happens. |
| `scripts/templates/` | `career-showcase.html.j2` (site), `resume.html.j2` (PDF layout), and `share-card.html.j2` (link-preview images). |
| `assets/` | Self-hosted fonts (Archivo, Roboto; SIL OFL), venture logos, the résumé, and the viewer script. |
| `server.js` | Express server for `index.html`, `/assets`, and the license script. |
| `documentation/` | Private source material: reviews, old résumé, personal notes. Gitignored. |
| `visuals.md`, `CLAUDE.md` | Page structure spec and AI-assistant instructions. |
