"""Stage the public GitHub copy of the code in ../underlink-nt.

Same file list as the submission ZIP (package.code_files), minus what must not
be public:
  - data/processed/: with the code it rebuilds the restricted relay register
  - the two submission-logistics scripts, which carry student IDs
Student IDs are also stripped from every other file, and the staged tree is
checked for relay keys, IDs and email addresses before anything is written.

    python docs/submission/publish_repo.py      # stage only; git push is a separate step
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import package  # noqa: E402

ROOT = package.ROOT
STAGE = ROOT.parent / "underlink-nt"
LEAVE_OUT_DIRS = ("data/processed/",)
LEAVE_OUT_FILES = {"docs/submission/package.py", "docs/submission/patch_report_pdf.py"}
TEXT = {".py", ".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".sql", ".html", ".js", ".css", ".ipynb", ".svg", ""}

FRONT = (ROOT / "docs/report/underlink_report.md").read_text().split("---", 2)[1]
IDS = re.findall(r"\((\d{6})\)", FRONT)                 # student IDs, read from the report front matter
ID_RE = re.compile(r"\s*\((?:%s)\)" % "|".join(IDS)) if IDS else None
KEY = re.compile(r"\bR[0-9a-f]{8}\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[A-Za-z]{2,})+")
ALLOWED_EMAILS = {"itcodefair@cdu.edu.au"}

GITIGNORE = """\
# raw downloads, restricted outputs and derived data never go to the public repository
/data_probe/
/data/processed/
/outputs/restricted/
/submission/
/research/
__pycache__/
.pytest_cache/
.ipynb_checkpoints/
._*
.DS_Store
"""


def main() -> None:
    STAGE.mkdir(exist_ok=True)
    for p in STAGE.iterdir():                          # refresh everything except git history
        if p.name != ".git" and not p.name.startswith("._"):
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    n = 0
    problems = []
    for src, rel in package.code_files():
        if rel in LEAVE_OUT_FILES or rel.startswith(LEAVE_OUT_DIRS):
            continue
        dst = STAGE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in TEXT:
            text = src.read_text(errors="ignore")
            if ID_RE:
                text = ID_RE.sub("", text)
            if KEY.search(text):
                problems.append(f"relay key in {rel}")
            bad = set(EMAIL.findall(text)) - ALLOWED_EMAILS
            if bad:
                problems.append(f"email {sorted(bad)} in {rel}")
            if any(i in text for i in IDS):
                problems.append(f"student ID in {rel}")
            dst.write_text(text)
        else:
            shutil.copy2(src, dst)
        n += 1
    (STAGE / ".gitignore").write_text(GITIGNORE)
    if problems:
        raise SystemExit("not staged, fix first:\n  " + "\n  ".join(problems))
    print(f"staged {n} files in {STAGE}")


if __name__ == "__main__":
    main()
