"""Render a set of deck slide files into one PDF at 1920x1080, one slide per page.

Usage: python render_deck.py <out.pdf> <slide1.html> [slide2.html ...]

Each input is a fragment holding exactly one <section>, as the deck stores them.
Speaker notes (<aside>) are hidden. Slides paginate one per page.
"""

import pathlib
import subprocess
import sys

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap">
<style>
  @page {{ size: 1920px 1080px; margin: 0; }}
  html, body {{ margin: 0; padding: 0; width: 1920px; }}
  section {{
    position: relative; box-sizing: border-box;
    width: 1920px; height: 1080px; overflow: hidden;
    break-after: page; page-break-after: always;
  }}
  section:last-child {{ break-after: auto; page-break-after: auto; }}
  aside {{ display: none; }}
  h1, h2, h3, p, ul, ol, table {{ margin: 0; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ padding: 0.35em 0.6em; border-bottom: 1px solid #363C42; }}
  /* The deck's custom elements, approximated for preview. */
  x-shape {{ display: block; }}
  x-shape[kind="ellipse"] {{ border-radius: 50%; }}
  x-shape[kind="diamond"] {{ transform: rotate(45deg); }}
  x-icon {{ display: inline-block; }}
</style></head>
<body>
{sections}
</body></html>
"""


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    out = pathlib.Path(sys.argv[1]).resolve()
    sources = [pathlib.Path(a).resolve() for a in sys.argv[2:]]

    fragments = []
    for src in sources:
        text = src.read_text(encoding="utf-8")
        if "<section" not in text:
            print(f"{src} does not contain a <section>")
            return 1
        fragments.append(text)

    page = out.with_suffix(".build.html")
    page.write_text(PAGE.format(sections="\n".join(fragments)), encoding="utf-8")

    subprocess.run(
        [
            CHROME,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--virtual-time-budget=10000",
            f"--print-to-pdf={out}",
            page.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    page.unlink()

    print(f"{out}  {out.stat().st_size:,} bytes  ({len(sources)} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
