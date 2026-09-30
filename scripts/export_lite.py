"""Write outputs/public/underlink_lite.html: the Government view as one offline file.

    python scripts/export_lite.py

Every value is precomputed from outputs/public/numbers.json and the public CSVs.
All JavaScript and CSS are inlined, so the file opens with no network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import panel as pn  # noqa: E402
from bokeh.resources import INLINE  # noqa: E402

from underlink import app_data as A  # noqa: E402
from underlink.config import PUBLIC  # noqa: E402

OUT = PUBLIC / "underlink_lite.html"
CAP_MB = 5


def main() -> None:
    pn.config.inline = True
    pn.extension(raw_css=[A.CSS], inline=True, design=None, notifications=False)
    pn.config.raw_css = [A.CSS]
    page = pn.Column(
        pn.pane.HTML("<div class='ul-note' style='display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center'>"
                     "<a href='https://underlink-nt.vercel.app/' style='font-weight:700;text-decoration:none'>"
                     "&larr; Back to the Underlink website</a>"
                     "<span><b style='font-size:18px'>Underlink</b> From Signal to System. "
                     "Government summary, public version. Works offline.</span></div>"),
        A.government_view(),
        sizing_mode="stretch_width",
    )
    # embed=True freezes the view; INLINE puts bokeh and panel JS in the file.
    page.save(OUT, embed=True, resources=INLINE, title="Underlink Lite")

    html = OUT.read_text()
    # Panel adds favicon links that point at its CDN. Drop them so nothing loads remotely.
    html = re.sub(r'<link rel="(?:apple-touch-icon|icon)"[^>]*>\s*', "", html)
    # Phones: render at the device width (Panel's template has no viewport tag) with phone-only spacing.
    html = html.replace("<head>", """<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
@media screen and (max-width: 720px) {
  body { margin: 0 !important; padding: 0 10px !important; overflow-x: hidden; }
  table { display: block; overflow-x: auto; max-width: 100%; font-size: 13px; }
}
</style>""", 1)
    OUT.write_text(html)
    # Checks: no remote scripts or stylesheets, no relay keys.
    remote = re.findall(r'<(?:script|link)[^>]+(?:src|href)="https?://[^"]+"', html)
    keys = re.findall(r"\bR[0-9a-f]{8}\b", html)
    mb = OUT.stat().st_size / 1e6
    print(f"wrote {OUT.relative_to(ROOT)}: {mb:.2f} MB ({OUT.stat().st_size:,} bytes), remote resources: {len(remote)}, relay keys: {len(keys)}")
    if mb > CAP_MB or remote or keys:
        sys.exit("Lite file failed a check")


if __name__ == "__main__":
    main()
