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

code, out = run("# no frontmatter\n")
assert code == 1 and "no YAML frontmatter" in out, out

print("ok")
