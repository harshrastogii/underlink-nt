"""Let `pytest` find the package in src/ without setting PYTHONPATH."""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


import pytest  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "processed" / "places.csv"


def pytest_collection_modifyitems(config, items):
    """Without data/processed/ (the public GitHub copy), skip the tests that need it instead of failing."""
    if DATA.exists():
        return
    skip = pytest.mark.skip(reason="data/processed/ is not in the public repository; it ships in the submission ZIP")
    for item in items:
        if "processed" in item.nodeid or item.module.__name__.split(".")[-1] in {"test_integrity"}:
            item.add_marker(skip)
