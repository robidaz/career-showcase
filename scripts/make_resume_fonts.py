"""
make_resume_fonts.py
One-time tool: writes the static Archivo instances the résumé PDF embeds
(assets/fonts/resume/*.ttf). Re-run it only to change an instance or the
character set; the build reads the committed files and never needs fontTools.

Why static fonts: Chrome embeds a variable font in a PDF as Type 3 outlines with
no space characters, so text extracted from the PDF (ATS parsers) can run words
together. Static TrueType instances embed as CID TrueType with real spaces.

Source: Archivo[wdth,wght].ttf from https://github.com/google/fonts/tree/main/ofl/archivo
(the full font, not the site's latin-only woff2), pinned to a google/fonts commit
and checked by SHA-256. Licensed under the SIL Open Font License 1.1, see
assets/fonts/LICENSE-Archivo-OFL.txt. Each instance keeps the copyright and
license name records, gets its own family name ("Archivo Resume Body", …), and
drops kerning against the space glyph so no word gap is narrower than a space.

The instances (role, weight, width) are RESUME_FONTS in resume_pdf.py; they are
subset to Google Fonts' "latin" range plus the arrows (→ is in role titles).

Usage:
  .venv/bin/pip install fonttools                     # one-time tool, not in requirements.txt
  .venv/bin/python scripts/make_resume_fonts.py       # downloads the pinned source font
  .venv/bin/python scripts/make_resume_fonts.py "path/to/Archivo[wdth,wght].ttf"
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
import tempfile
import urllib.request

try:
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
except ImportError:
    sys.exit("ERROR: fontTools not installed. Run: .venv/bin/pip install fonttools")

from resume_pdf import FONT_DIR, RESUME_FONTS, font_file

# ---------------------------------------------------------------------------
# Source font & subset
# ---------------------------------------------------------------------------
WORKSPACE = pathlib.Path(__file__).parent.parent
SOURCE_COMMIT = "95f4904fc8bcf26d3420fe315560c96417c6dec7"          # google/fonts, 2026-03-03
SOURCE_URL = (f"https://raw.githubusercontent.com/google/fonts/{SOURCE_COMMIT}"
              "/ofl/archivo/Archivo%5Bwdth%2Cwght%5D.ttf")
SOURCE_SHA256 = "0e094a7d3c7c4c25cf1310c4b30014f1dae9332220b1c2c88f4fa996f0b05053"

UNICODES = [                                      # Google Fonts "latin" + arrows
    *range(0x20, 0x7F), *range(0xA0, 0x100), 0x131, 0x152, 0x153, 0x2BB, 0x2BC,
    0x2C6, 0x2DA, 0x2DC, 0x304, 0x308, 0x329, *range(0x2000, 0x2070), 0x20AC,
    0x2122, *range(0x2190, 0x2194), 0x2212, 0x2215, 0xFEFF, 0xFFFD,
]
NAME_IDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14]   # incl. copyright (0) and license (13, 14)


# ---------------------------------------------------------------------------
# Build the instances
# ---------------------------------------------------------------------------
def _download(dest: pathlib.Path) -> pathlib.Path:
    print(f"Downloading {SOURCE_URL}")
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
        dest.write_bytes(response.read())
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        sys.exit(f"ERROR: downloaded font has SHA-256 {digest}, expected {SOURCE_SHA256}.")
    return dest


def _drop_space_kerning(font: TTFont) -> int:
    """Remove kerning pairs with the space glyph (Archivo kerns "P " by -45 units).
    A word gap then never shrinks below a full space, which is what text
    extractors (pdftotext -raw) need to see it as a space. Returns pairs removed."""
    space, removed = font.getBestCmap()[0x20], 0
    for lookup in font["GPOS"].table.LookupList.Lookup:
        for table in lookup.SubTable:
            table = getattr(table, "ExtSubTable", table)
            if type(table).__name__ != "PairPos" or table.Format != 1:   # Archivo kerns space
                continue                                                 # only in glyph pairs
            for first, pair_set in zip(table.Coverage.glyphs, table.PairSet):
                kept = [rec for rec in pair_set.PairValueRecord if space not in (first, rec.SecondGlyph)]
                removed += len(pair_set.PairValueRecord) - len(kept)
                pair_set.PairValueRecord, pair_set.PairValueCount = kept, len(kept)
    return removed


def _instance(source: pathlib.Path, role: str, weight: int, width: int) -> TTFont:
    """Pin both axes, subset, and rename so the instance is a standalone family."""
    font = instancer.instantiateVariableFont(TTFont(source), {"wght": weight, "wdth": width})

    options = subset.Options()
    options.layout_features = ["*"]               # keep every feature Chrome could apply
    options.name_IDs = NAME_IDS
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=UNICODES)
    subsetter.subset(font)
    _drop_space_kerning(font)

    family, ps_name = f"Archivo Resume {role.title()}", f"ArchivoResume-{role.title()}"
    version = font["name"].getDebugName(5).removeprefix("Version ")
    for name_id, value in ((1, family), (2, "Regular"), (3, f"{version};{ps_name}"),
                           (4, family), (6, ps_name)):
        font["name"].setName(value, name_id, 3, 1, 0x409)
    font["OS/2"].fsSelection = (font["OS/2"].fsSelection & ~0b100001) | 0b1000000  # REGULAR
    font["head"].macStyle &= ~0b11                                                 # not bold/italic
    font.recalcTimestamp = False                  # same input, same bytes
    return font


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write the résumé's static Archivo instances.")
    parser.add_argument("source", nargs="?", type=pathlib.Path,
                        help="Archivo[wdth,wght].ttf (default: download the pinned google/fonts copy)")
    args = parser.parse_args(argv)

    out_dir = WORKSPACE / FONT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        source = args.source or _download(pathlib.Path(tmp) / "Archivo[wdth,wght].ttf")
        for role, weight, width in RESUME_FONTS:
            path = out_dir / font_file(role, weight, width)
            _instance(source, role, weight, width).save(path)
            print(f"Wrote {path}  (wght {weight}, wdth {width}, {path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
