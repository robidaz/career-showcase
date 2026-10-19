"""
Link-preview images for texts and social posts, written to assets/share/:

  share-card.png        1200×630 og:image, drawn like the site masthead
  apple-touch-icon.png  180×180 home-screen / link icon

Both are screenshots of scripts/templates/share-card.html.j2 taken with the
same headless Chrome that prints the résumé. Called by
generate_career_showcase.py on a full build (skipped with --skip-pdf).
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile

from jinja2 import Environment, FileSystemLoader, select_autoescape

from resume_pdf import CHROME_TIMEOUT, _find_chrome, _warn

SHARE_DIR = ("assets", "share")
CARD_NAME = "share-card.png"
ICON_NAME = "apple-touch-icon.png"
CARD_SIZE = (1200, 630)
ICON_SIZE = (180, 180)


def _screenshot(chrome: pathlib.Path, page: pathlib.Path, out: pathlib.Path,
                size: tuple[int, int], profile: pathlib.Path) -> str:
    """Screenshot one page; return "" on success, else a short reason."""
    out.unlink(missing_ok=True)
    cmd = [str(chrome), "--headless", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1", "--virtual-time-budget=4000",
           "--force-prefers-reduced-motion",                 # arcs paint one still frame, so reruns match
           "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}",
           f"--window-size={size[0]},{size[1]}", f"--screenshot={out}", page.as_uri()]
    for attempt in (cmd, [*cmd[:-1], "--no-sandbox", cmd[-1]]):
        try:
            proc = subprocess.run(attempt, capture_output=True, text=True, errors="replace",
                                  timeout=CHROME_TIMEOUT)
        except (subprocess.TimeoutExpired, OSError) as exc:
            return str(exc)
        if proc.returncode == 0 and out.is_file():
            return ""
        if "sandbox" not in proc.stderr.lower():
            break
    return f"exit code {proc.returncode}"


def build_share_images(context: dict, workspace: pathlib.Path) -> None:
    chrome = _find_chrome()
    if not chrome:
        _warn("Chrome not found, so the link-preview images were not rebuilt.")
        return
    out_dir = workspace.joinpath(*SHARE_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(str(workspace / "scripts" / "templates")),
                      autoescape=select_autoescape(["html", "j2"]))
    template = env.get_template("share-card.html.j2")
    shared = {
        "person":   context["person"],
        "font_url": (workspace / "assets" / "fonts" / "archivo-variable.woff2").as_uri(),
        "arcs_url": (workspace / "assets" / "js" / "masthead-arcs.js").as_uri(),
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = pathlib.Path(tmp)
        for mode, name, size in (("card", CARD_NAME, CARD_SIZE), ("icon", ICON_NAME, ICON_SIZE)):
            page = tmp_dir / f"{mode}.html"
            page.write_text(template.render(mode=mode, width=size[0], height=size[1], **shared),
                            encoding="utf-8")
            shot = tmp_dir / name
            error = _screenshot(chrome, page, shot, size, tmp_dir / "profile")
            if error:
                _warn(f"Chrome could not render {name}; the existing file was kept.\n  Error: {error}")
            else:
                shutil.move(shot, out_dir / name)
                print(f"Generated: {out_dir / name}  ({size[0]}×{size[1]})")
