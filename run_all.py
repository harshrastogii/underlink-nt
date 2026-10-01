"""Regenerate every Underlink number and figure.

    python run_all.py            # analysis + figures from data/processed (what judges run)
    python run_all.py --prepare  # also rebuild data/processed from the raw downloads

Every number in the report and deck is read from outputs/public/numbers.json.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from underlink import pipeline  # noqa: E402

if __name__ == "__main__":
    if "--prepare" not in sys.argv and not (ROOT / "data" / "processed" / "places.csv").exists():
        # The public GitHub copy leaves data/processed/ out: with the code it rebuilds the restricted relay register.
        sys.exit("data/processed/ is not here. It ships in the submission ZIP. To rebuild it from the public raw\n"
                 "downloads listed in data/manifest.csv, put them under data_probe/ and run: python run_all.py --prepare")
    if "--prepare" in sys.argv:
        from underlink import prepare
        print("1/3 preparing processed data from raw downloads ...")
        prepare.main()
    print("2/3 running the analysis ...")
    n = pipeline.run()
    print("3/3 drawing figures and the single-score illustration ...")
    runpy.run_path(str(ROOT / "scripts" / "report_figures.py"), run_name="__main__")
    runpy.run_path(str(ROOT / "scripts" / "single_score_probe.py"), run_name="__main__")
    runpy.run_path(str(ROOT / "scripts" / "export_web_data.py"), run_name="__main__")   # public numbers for web/
    c = n["chains"]
    print(f"\nDone. {c['with_ge1_spof']} of {c['radio_chain_places']} radio-chain places depend on at least one relay "
          f"with no alternative licensed path; numbers in outputs/public/numbers.json")
