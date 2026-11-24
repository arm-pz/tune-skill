#!/usr/bin/env python3
"""Self-check for check_skill.py: python -I scripts/test_check_skill.py"""
import subprocess
import sys
import tempfile
from pathlib import Path

CHECK = Path(__file__).resolve().parent / "check_skill.py"

SKILL = """---
name: demo-skill
description: >-
  Checks a demo before release. Use when the user says "check the demo".
  Not for real work (use other-skill).
---

# Demo skill

Run this before pushing. Run it again before deploying to production.
"""


# Runs the checker as if PyYAML were missing, to cover the fallback parser.
NO_YAML = ("import runpy, sys; sys.modules['yaml'] = None; sys.argv = sys.argv[1:]; "
           "runpy.run_path(sys.argv[0], run_name='__main__')")


def run(text, newline="\n", bom=False, no_yaml=False):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "demo-skill"
        folder.mkdir()
        data = text.replace("\n", newline).encode("utf-8")
        (folder / "SKILL.md").write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)
        cmd = [sys.executable, "-I"] + (["-c", NO_YAML] if no_yaml else []) + [str(CHECK), str(folder)]
        p = subprocess.run(cmd,
                           capture_output=True, text=True, encoding="utf-8")
        return p.returncode, p.stdout


for newline, bom, no_yaml in (("\n", False, False), ("\r\n", False, False), ("\r\n", True, False),
                              ("\n", False, True), ("\r\n", True, True)):
    code, out = run(SKILL, newline, bom, no_yaml)
    assert code == 0, (newline, bom, no_yaml, out)
    assert "FAIL" not in out, out
    assert "trigger wording" not in out and "'Not for'" not in out, out  # folded description was read
    assert "NOTE" in out and "skill-to-mod" in out, out

code, out = run(SKILL.replace("name: demo-skill", "name: Demo Skill"))
assert code == 1 and "lowercase" in out, out

# An unquoted ": " parses in a lenient reader but breaks strict YAML loaders; both paths must fail it.
BAD = SKILL.replace("description: >-\n  Checks a demo before release.", "description: Checks a demo: before release.")
for no_yaml in (False, True):
    code, out = run(BAD, no_yaml=no_yaml)
    assert code == 1 and "not valid YAML" in out, (no_yaml, out)

# A count claim is checked against the tables and lists in the body, wherever they sit.
TABLE = "\n## Modes\n\n| Mode | Use |\n| --- | --- |\n| a | x |\n| b | y |\n| c | z |\n"
code, out = run(SKILL + "\nIt has three modes.\n" + TABLE)
assert "three modes" not in out, out
code, out = run(SKILL + "\nIt has four modes.\n" + TABLE)
assert "says 'four modes' but no table or list in it has 4 entries" in out, out
code, out = run(SKILL + "\nThree steps:\n\n1. one\n2. two\n   detail\n\n3. three\n")
assert "Three steps" not in out, out
code, out = run(SKILL + "\nTwo steps:\n\n1. one\n2. two\n3. three\n")
assert "says 'Two steps' but no table or list in it has 2 entries" in out, out

code, out = run("# no frontmatter\n")
assert code == 1 and "no YAML frontmatter" in out, out

# --lint: off by default, so default output (and regress.py baselines) never change.
code, out = run(SKILL)
assert "LINT" not in out, out


def run_lint(text):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "demo-skill"
        folder.mkdir()
        (folder / "SKILL.md").write_text(text, encoding="utf-8")
        p = subprocess.run([sys.executable, "-I", str(CHECK), str(folder), "--lint"],
                           capture_output=True, text=True, encoding="utf-8")
        return p.returncode, p.stdout


GOOD = SKILL + """
## Workflow

### 1. Inventory

    python scripts/inventory.py . > inv.json

Check that `inv.json` lists at least one file; if it is empty, stop.

### 2. Score

Run `python scripts/score.py inv.json`. It exits 0 on pass; confirm the exit code before step 3.

### 3. Report

Run `git diff --stat` and check the output names only the files you changed.

## When it fails

| Failure | Fix |
| --- | --- |
| inventory is empty | pass the project root, not a subfolder |
| score exits 2 | write judgments.json, then score again |
"""
code, out = run_lint(GOOD)
assert code == 0 and out.count("LINT  PASS") == 3 and "lint: 3 pass, 0 fail" in out, out

code, out = run_lint(SKILL)
assert code == 1 and "no numbered steps" in out and "no error recovery section" in out, out

code, out = run_lint(GOOD.replace("### 2. Score", "### 2. Score and report"))
assert "more than one objective in step 2" in out, out
code, out = run_lint(GOOD.replace("### 1. Inventory\n\n    python scripts/inventory.py . > inv.json\n",
                                  "### 1. Inventory\n\nLook around the project.\n"))
assert "no concrete command in step 1" in out, out
code, out = run_lint(GOOD.replace("| score exits 2 | write judgments.json, then score again |",
                                  "| score exits 2 | Try again |"))
assert "'try again' is not a fix for: score exits 2" in out, out

print("ok")
