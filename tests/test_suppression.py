"""Small cells in public tables are shown as '<3', never as 1 or 2."""
import json

import pandas as pd
import pytest

from underlink import governance, pipeline
from underlink.config import P, PUBLIC, RESTRICTED

FLOOR = P["privacy"]["min_places"]


@pytest.fixture(scope="module")
def table():
    return pd.read_csv(PUBLIC / "region_classes.csv", dtype=str).set_index("land_council")


def test_no_small_integers(table):
    cells = table.values.ravel()
    assert not {"1", "2"} & set(cells)
    for v in cells:
        assert v == f"<{FLOOR}" or int(v) == 0 or int(v) >= FLOOR


def test_small_cells_are_marked(table):
    assert (table == f"<{FLOOR}").values.sum() > 0


def test_matches_unsuppressed_where_available(table):
    raw_path = RESTRICTED / "region_classes_unsuppressed.csv"
    if not raw_path.exists():
        pytest.skip("restricted tier not present (expected on a judge's machine)")
    raw = pd.read_csv(raw_path).set_index("land_council")
    for lc, row in raw.iterrows():
        for col, n in row.items():
            assert table.loc[lc, col] == str(governance.suppress_count(int(n), FLOOR))


def test_numbers_json_regions_suppressed():
    N = json.loads((PUBLIC / "numbers.json").read_text())
    cells = [v for row in N["regions"].values() for v in row.values()]
    cells += [v for e in N["replay"]["primary"] for v in e.get("by_land_council", {}).values()]
    assert all(v == f"<{FLOOR}" or v == 0 or v >= FLOOR for v in cells)


@pytest.mark.parametrize("n", [0, 1, 2, 3, 9, 10, 250])
def test_helper_matches_pipeline(n):
    for floor in (3, 10):
        assert governance.suppress_count(n, floor) == pipeline.suppress(n, floor)
