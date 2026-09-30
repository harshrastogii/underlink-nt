"""Paths and parameters shared by every Underlink module."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data_probe"            # raw downloads (2.2 GB, not shipped)
PROCESSED = ROOT / "data" / "processed"
REFERENCE = ROOT / "data" / "reference"
OUTPUTS = ROOT / "outputs"
PUBLIC = OUTPUTS / "public"
RESTRICTED = OUTPUTS / "restricted"
FIGURES = PUBLIC / "figures"

with open(ROOT / "config" / "params.yaml") as fh:
    P = yaml.safe_load(fh)


def ensure_dirs() -> None:
    for d in (PROCESSED, REFERENCE, PUBLIC, RESTRICTED, FIGURES):
        d.mkdir(parents=True, exist_ok=True)
