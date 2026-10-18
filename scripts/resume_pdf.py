"""
resume_pdf.py
Builds the one-page résumé PDF, plus a PNG preview of it, from the same context
the site uses (load_career_data() in generate_career_showcase.py):
  - scripts/templates/resume.html.j2       (print layout, US Letter)
  - assets/fonts/resume/*.ttf              (static Archivo instances, see make_resume_fonts.py)

Outputs, in assets/resume/:
  - <Resume Export → File Name>            e.g. Zach-Robida-Resume.pdf
  - resume-preview.png                     page 1, 1200 px wide

Needs headless Chrome or Chromium; set CHROME_PATH to choose the binary.
poppler-utils (pdfinfo, pdftoppm, pdffonts) are optional: they run the page-count
check, the preview and the font check, and are skipped with a warning if missing.

Usage:
  python scripts/resume_pdf.py      # résumé only, from career-data.md
"""

from __future__ import annotations

import datetime as dt
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from markupsafe import Markup, escape

# ---------------------------------------------------------------------------
# Paths & settings
# ---------------------------------------------------------------------------
TEMPLATE_NAME = "resume.html.j2"                  # in scripts/templates/
OUTPUT_REL = pathlib.Path("assets", "resume")

# Static Archivo instances written by scripts/make_resume_fonts.py. Chrome embeds
# static fonts as TrueType with real spaces in the PDF text layer; the site's
# variable font would go in as Type 3 outlines whose extracted text loses them.
FONT_DIR = pathlib.Path("assets", "fonts", "resume")
RESUME_FONTS = (                                  # (role, weight, width %), as the template uses them
    ("body",    400, 100),                        # running text, dates, links
    ("display", 740, 75),                         # name, section headings, companies, ventures
    ("label",   600, 80),                         # title line, role titles, skill labels, degrees
)
PREVIEW_NAME = "resume-preview.png"               # = RESUME_PREVIEW_NAME in generate_career_showcase.py
PREVIEW_WIDTH = 1200                              # px
FIT_STEPS = (1.0, 0.985, 0.973)                   # zoom retries on overflow (body stays ≥ 9pt)
CHROME_TIMEOUT = 60                               # seconds; a normal print takes about one
TOOL_TIMEOUT = 30                                 # seconds per poppler call

CHROME_FLAGS = (
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    "--run-all-compositor-stages-before-draw",
    "--virtual-time-budget=10000",                # lets @font-face finish loading first
    "--no-first-run",
    "--no-default-browser-check",
)

# ---------------------------------------------------------------------------
# Locate headless Chrome: CHROME_PATH, then PATH, then standard installs,
# then the newest Playwright / Puppeteer download
# ---------------------------------------------------------------------------
CHROME_NAMES = (
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "chrome", "chrome-headless-shell",
)
CHROME_LOCATIONS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
)
CHROME_CACHES = (                                 # relative to ~/.cache
    "ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
    "ms-playwright/chromium-*/chrome-linux64/chrome",
    "puppeteer/chrome-headless-shell/*/chrome-headless-shell-linux64/chrome-headless-shell",
    "puppeteer/chrome/*/chrome-linux64/chrome",
)


def _is_executable(path: pathlib.Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _version_key(path: pathlib.Path) -> list:
    """Natural sort key: chromium-1243 > chromium-999, 150.0.7871 > 148.0.7778."""
    return [int(tok) if tok.isdigit() else tok for tok in re.split(r"(\d+)", str(path))]


def _find_chrome() -> pathlib.Path | None:
    override = os.environ.get("CHROME_PATH", "").strip()
    if override:
        path = pathlib.Path(override).expanduser()
        if _is_executable(path):
            return path
        _warn(f"CHROME_PATH={override} is not an executable file; searching the usual places.")

    for name in CHROME_NAMES:
        found = shutil.which(name)
        if found:
            return pathlib.Path(found)

    for location in CHROME_LOCATIONS:
        expanded = os.path.expandvars(location)
        if "%" not in expanded and _is_executable(pathlib.Path(expanded)):
            return pathlib.Path(expanded)

    cache = pathlib.Path.home() / ".cache"
    for pattern in CHROME_CACHES:
        matches = [path for path in cache.glob(pattern) if _is_executable(path)]
        if matches:
            return max(matches, key=_version_key)
    return None


# ---------------------------------------------------------------------------
# Shape the site context for the one-page layout
# ---------------------------------------------------------------------------
def _typeset(text: str) -> Markup:
    """Print typography: curly apostrophes, en-dash year ranges ("2013 - 2018"),
    no line starting with an em dash, no break inside "AI-driven"-style compounds."""
    text = re.sub(r"(?<=\w)'", "\u2019", str(text))
    text = re.sub(r"\b((?:19|20)\d{2})\s*-\s*((?:19|20)\d{2})\b", "\\1 \u2013 \\2", text)
    html = str(escape(text.replace(" \u2014 ", "\u00a0\u2014 ")))
    return Markup(re.sub(r"\w+(?:-\w+)+", lambda m: f'<span class="nobr">{m.group(0)}</span>', html))


def _bullet_limit(per_role: list[int], index: int) -> int | None:
    """Resume Export → Bullets Per Role (None = all); roles past the list reuse its last value."""
    return per_role[min(index, len(per_role) - 1)] if per_role else None


def _span(roles: list[dict]) -> str:
    """Overall period for a company block: '2018 – Present'."""
    if len(roles) == 1:
        return roles[0]["period"]
    start = min(role["start"] for role in roles)
    if any(role["is_current"] for role in roles):
        return f"{start} – Present"
    return f"{start} – {int(max(role['end'] for role in roles))}"


def _group_roles(roles: list[dict], per_role: list[int]) -> list[dict]:
    """Merge consecutive roles at the same company so the progression reads as one block."""
    groups: list[dict] = []
    for index, role in enumerate(roles):
        if not groups or groups[-1]["company"] != role["company"]:
            name, _, detail = role["company"].partition(" — ")
            groups.append({"company": role["company"], "name": name.strip(),
                           "detail": detail.strip(), "sources": [], "roles": []})
        groups[-1]["sources"].append(role)
        groups[-1]["roles"].append({
            "title_parts": [part.strip() for part in role["title"].split("→")],
            "period":      role["period"],
            "bullets":     role["bullets"][:_bullet_limit(per_role, index)],
        })
    for group in groups:
        group["period"] = _span(group.pop("sources"))
    return groups


def _skill_lines(groups: list[dict], limit: int) -> list[dict]:
    """First `limit` skills of each category, in the order career-data.md lists them."""
    return [
        {"category": group["category"],
         "names": [skill["name"] for skill in group["skills"][:limit or None]]}
        for group in groups
    ]


def _education(item: dict) -> dict:
    """Split 'Summer 2017 | Selected as …' into a date column and a note."""
    dates, _, note = item["detail"].partition(" | ")
    if not re.search(r"\b(?:19|20)\d{2}\b", dates):
        dates, note = "", item["detail"]
    school, _, place = item["school"].partition(" — ")
    return {
        "degree": item["degree"],
        "school": f"{school.strip()}, {place.strip()}" if place else school.strip(),
        "dates":  dates.strip(),
        "note":   note.strip(),
    }


def _resume_view(context: dict) -> dict:
    resume = context["resume"]
    return {
        "person":    context["person"],
        "summary":   resume.get("summary", ""),
        "groups":    _group_roles(context["roles"], resume.get("bullets_per_role", [])),
        "ventures":  context.get("ventures", []),
        "skills":    _skill_lines(context["skills"], resume.get("skills_per_category", 0)),
        "education": [_education(item) for item in context["education"]],
    }


def font_file(role: str, weight: int, width: int) -> str:
    """File name of one static instance in FONT_DIR (shared with make_resume_fonts.py)."""
    return f"archivo-{role}-{weight}-{width}.ttf"


def _font_faces(workspace: pathlib.Path) -> list[dict]:
    """@font-face entries for the template; warns about any instance that is missing."""
    faces = []
    for role, weight, width in RESUME_FONTS:
        path = workspace / FONT_DIR / font_file(role, weight, width)
        if not path.is_file():
            _warn(f"{path} is missing; run scripts/make_resume_fonts.py to recreate it.")
        faces.append({"url": path.as_uri(), "weight": weight, "width": width})
    return faces


def _load_template(workspace: pathlib.Path) -> Template:
    env = Environment(
        loader=FileSystemLoader(str(workspace / "scripts" / "templates")),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["typeset"] = _typeset
    return env.get_template(TEMPLATE_NAME)


# ---------------------------------------------------------------------------
# Print with Chrome
# ---------------------------------------------------------------------------
def _run_chrome(cmd: list[str], pdf: pathlib.Path) -> str:
    """Run one print job; return "" on success, else a short reason."""
    pdf.unlink(missing_ok=True)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                              timeout=CHROME_TIMEOUT)
    except subprocess.TimeoutExpired:
        return f"timed out after {CHROME_TIMEOUT}s"
    except OSError as exc:
        return str(exc)
    if proc.returncode == 0 and pdf.is_file() and pdf.read_bytes()[:5] == b"%PDF-":
        return ""
    tail = [line for line in proc.stderr.splitlines() if line.strip()][-3:]
    return f"exit code {proc.returncode}" + "".join(f"\n    {line}" for line in tail)


def _print_pdf(chrome: pathlib.Path, page: pathlib.Path, pdf: pathlib.Path,
               profile: pathlib.Path) -> bool:
    flags = [*CHROME_FLAGS, f"--user-data-dir={profile}", f"--print-to-pdf={pdf}"]
    error = _run_chrome([str(chrome), *flags, page.as_uri()], pdf)
    if error and "sandbox" in error.lower():
        # Root, containers and AppArmor-restricted hosts can't start Chrome's
        # sandbox; the page is our own local file, so print without it.
        error = _run_chrome([str(chrome), *flags, "--no-sandbox", page.as_uri()], pdf)
    if error:
        _warn(f"Chrome could not print the résumé, so the existing PDF was kept.\n"
              f"  Chrome: {chrome}\n  Error:  {error}")
    return not error


def _pin_dates(pdf: pathlib.Path, day: dt.date) -> None:
    """Chrome stamps the print time into the PDF. Pin it to the day so same-day
    rebuilds are byte-identical (stable cache-busting hash on the site)."""
    data = pdf.read_bytes()
    stamp = f"D:{day:%Y%m%d}000000+00'00'".encode()
    pinned = re.sub(rb"(/(?:CreationDate|ModDate) \()D:\d{14}[+-]\d{2}'\d{2}'",
                    lambda m: m.group(1) + stamp, data)
    if len(pinned) == len(data):              # same length keeps the xref offsets valid
        pdf.write_bytes(pinned)


# ---------------------------------------------------------------------------
# Checks & preview (poppler-utils; all optional)
# ---------------------------------------------------------------------------
def _run_tool(cmd: list[str]) -> str | None:
    if not shutil.which(cmd[0]):
        return None
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                              timeout=TOOL_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _page_count(pdf: pathlib.Path) -> int:
    """pdfinfo when available, else count the page objects (Skia writes them uncompressed)."""
    info = _run_tool(["pdfinfo", str(pdf)])
    match = re.search(r"^Pages:\s+(\d+)", info or "", re.MULTILINE)
    if match:
        return int(match.group(1))
    return len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes()))


def _pdf_fonts(pdf: pathlib.Path) -> list[tuple[str, str, bool]] | None:
    """(name, type, embedded) per font from pdffonts, or None when pdffonts is unavailable."""
    listing = _run_tool(["pdffonts", str(pdf)])
    if listing is None:
        return None
    fonts = []
    for line in listing.splitlines()[2:]:     # columns: name, type…, encoding, emb, sub, uni, obj, gen
        fields = line.split()
        if len(fields) >= 8:
            name = re.sub(r"^[A-Z]{6}\+", "", fields[0])
            fonts.append((name, " ".join(fields[1:-6]), fields[-5] == "yes"))
    return fonts


def _compact_png(path: pathlib.Path) -> None:
    """pdftoppm writes 24-bit RGB; a 256-colour palette of this flat page looks the
    same (every channel within 4/255, checked) at about a third of the size. Pillow optional."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return
    with Image.open(path) as image:
        rgb = image.convert("RGB")
    palette = rgb.quantize(colors=256, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE)
    error = max(high for _, high in ImageChops.difference(rgb, palette.convert("RGB")).getextrema())
    if error <= 4:                            # otherwise (gradients, photos) keep the RGB file
        palette.save(path, optimize=True)


def _render_preview(pdf: pathlib.Path, dest: pathlib.Path, tmp: pathlib.Path) -> bool:
    prefix = tmp / "preview"
    done = _run_tool(["pdftoppm", "-png", "-singlefile", "-f", "1", "-l", "1",
                      "-scale-to-x", str(PREVIEW_WIDTH), "-scale-to-y", "-1",
                      str(pdf), str(prefix)])
    png = prefix.with_suffix(".png")
    if done is None or not png.is_file():
        return False
    _compact_png(png)
    shutil.copyfile(png, dest)
    return True


def _png_size(path: pathlib.Path) -> tuple[int, int]:
    width, height = struct.unpack(">II", path.read_bytes()[16:24])
    return width, height


def _kb(path: pathlib.Path) -> str:
    return f"{path.stat().st_size / 1024:.0f} KB"


def _warn(message: str) -> None:
    sys.stdout.flush()                        # keep warnings in order with the progress lines
    print(f"WARNING (résumé): {message}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_resume(context: dict, workspace: pathlib.Path) -> dict:
    """Render the résumé into assets/resume/ and describe what is on disk afterwards:
    {"pdf": Path|None, "preview": Path|None, "pages": int}.

    Never raises for a missing tool: without Chrome the existing PDF is kept;
    without poppler-utils the checks and the preview are skipped.
    """
    workspace = pathlib.Path(workspace).resolve()
    out_dir = workspace / OUTPUT_REL
    pdf_path = out_dir / context["resume"]["file_name"]
    preview_path = out_dir / PREVIEW_NAME

    def on_disk(pages: int | None = None) -> dict:
        has_pdf = pdf_path.is_file()
        return {
            "pdf":     pdf_path if has_pdf else None,
            "preview": preview_path if preview_path.is_file() else None,
            "pages":   (pages if pages is not None else _page_count(pdf_path)) if has_pdf else 0,
        }

    chrome = _find_chrome()
    if chrome is None:
        _warn("no Chrome/Chromium found, so the résumé PDF was not rebuilt (any existing one "
              "is kept). Set CHROME_PATH to a Chrome, Chromium or chrome-headless-shell binary.")
        return on_disk()

    faces = _font_faces(workspace)
    template = _load_template(workspace)
    view = _resume_view(context)

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="resume-pdf-", ignore_cleanup_errors=True) as tmp_dir:
        tmp = pathlib.Path(tmp_dir)
        page, printed = tmp / "resume.html", tmp / "resume.pdf"
        for fit in FIT_STEPS:                 # shrink slightly rather than spill onto page 2
            page.write_text(template.render(fonts=faces, fit=fit, **view), encoding="utf-8")
            if not _print_pdf(chrome, page, printed, tmp / "chrome-profile"):
                return on_disk()
            pages = _page_count(printed)
            if pages <= 1:
                break
        _pin_dates(printed, dt.date.today())
        shutil.copyfile(printed, pdf_path)

        noun = "page" if pages == 1 else "pages"
        print(f"Generated: {pdf_path}  ({pages} {noun}, {_kb(pdf_path)})")
        print(f"  Chrome:   {chrome}")
        if fit != 1 and pages == 1:
            print(f"  Fit:      printed at {fit:.1%} scale to stay on one page")
        if pages == 0:
            _warn("could not count the PDF's pages, so the one-page check was skipped.")
        elif pages != 1:
            _warn("\n" + "!" * 78 + f"\n  The résumé PDF is {pages} {noun} even at {fit:.1%} scale; "
                  "it must fit on ONE.\n"
                  "  Lower 'Bullets Per Role' / 'Skills Per Category' under 'Resume Export' in\n"
                  "  career-data.md, or tighten scripts/templates/resume.html.j2.\n" + "!" * 78)

        fonts = _pdf_fonts(pdf_path)
        if fonts is None:
            _warn("pdffonts not found (poppler-utils), so font embedding was not checked.")
        else:
            print(f"  Fonts:    {', '.join(sorted({f'{name} ({kind})' for name, kind, _ in fonts}))}")
            stray = sorted({name for name, kind, embedded in fonts
                            if kind == "Type 3" or not embedded or not name.startswith("ArchivoResume-")})
            if stray:
                _warn(f"unexpected font(s) in the PDF: {', '.join(stray)}. Every glyph should come "
                      "from assets/fonts/resume/ (Type 3 fonts drop the spaces from the text layer); "
                      "add missing characters in scripts/make_resume_fonts.py and re-run it.")

        if _render_preview(pdf_path, preview_path, tmp):
            width, height = _png_size(preview_path)
            print(f"Generated: {preview_path}  ({width}×{height}, {_kb(preview_path)})")
        else:
            _warn("pdftoppm (poppler-utils) is unavailable or failed, so the preview image "
                  "was not updated" + (" and may be stale." if preview_path.is_file() else "."))

    return on_disk(pages)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------
def main() -> None:
    from generate_career_showcase import DATA_PATH, load_career_data

    build_resume(load_career_data(DATA_PATH), pathlib.Path(__file__).resolve().parent.parent)


if __name__ == "__main__":
    main()
