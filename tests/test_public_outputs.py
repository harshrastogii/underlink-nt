"""Public files must not carry relay keys, relay coordinates or site columns."""
import csv
import json
import re

import pytest

from underlink.config import PUBLIC, ROOT

KEY = re.compile(r"\bR[0-9a-f]{8}\b")
TEXT = {".csv", ".json", ".html", ".htm", ".md", ".txt", ".sql", ".svg", ".js", ".css", ".tex"}
BANNED_COLUMNS = {"lat", "lon", "latitude", "longitude", "site_key", "lat_full", "lon_full", "site_id"}


def public_files():
    for base in (PUBLIC, ROOT / "docs", ROOT / "web"):
        for p in sorted(base.rglob("*")):
            # skip macOS AppleDouble files on the exFAT drive
            if p.is_file() and not p.name.startswith("._") and p.suffix.lower() in TEXT:
                yield p


FILES = list(public_files())


def test_there_are_public_files():
    assert any(p.name == "numbers.json" for p in FILES)


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_relay_keys(path):
    hits = KEY.findall(path.read_text(errors="ignore"))
    assert not hits, f"{path.name} contains relay keys such as {hits[:3]}"


@pytest.mark.parametrize("path", [p for p in FILES if p.suffix == ".csv"], ids=lambda p: str(p.relative_to(ROOT)))
def test_no_site_or_coordinate_columns(path):
    with open(path, newline="") as fh:
        header = {h.strip().lower() for h in next(csv.reader(fh), [])}
    assert not header & BANNED_COLUMNS, f"{path.name} has columns {header & BANNED_COLUMNS}"


def test_numbers_json_has_no_site_keys():
    text = (PUBLIC / "numbers.json").read_text()
    assert not KEY.search(text)
    assert "site_key" not in json.loads(text)


def test_public_csvs_have_no_per_place_rows():
    """Public tables are aggregates. A per-place table could be joined to the
    shipped place list (data/processed/places.csv) and name each community's
    chain class, so no public CSV may carry place keys, names or chain lists."""
    import pandas as pd
    from underlink.config import PUBLIC
    for f in PUBLIC.rglob("*.csv"):
        if f.name.startswith("._"):
            continue
        cols = {c.lower() for c in pd.read_csv(f, nrows=0).columns}
        assert not cols & {"place_key", "name", "spof_relays", "end_site"}, f"{f.name} carries per-place columns"


# The web app is public and names no community (Section 4 of the report says so).
# Darwin appears only in the acknowledgement of Country.
ALLOWED_WEB_NAMES = {"darwin"}
WEB_FILES = [p for p in FILES if p.is_relative_to(ROOT / "web") and "downloads" not in p.parts]


def test_web_app_has_no_coordinates():
    data = (ROOT / "web" / "data" / "public.js").read_text()
    assert '"lat"' not in data and '"lon"' not in data and "latitude" not in data.lower()


def test_web_app_names_no_community():
    import pandas as pd
    names = {n.strip().lower() for n in pd.read_csv(ROOT / "data" / "processed" / "places.csv").name.dropna() if len(n.strip()) >= 5}
    text = " ".join(p.read_text(errors="ignore").lower() for p in WEB_FILES)
    found = {n for n in names if re.search(r"\b" + re.escape(n) + r"\b", text)}
    assert found <= ALLOWED_WEB_NAMES, f"web app names communities: {sorted(found - ALLOWED_WEB_NAMES)}"
