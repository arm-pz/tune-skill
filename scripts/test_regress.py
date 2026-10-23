#!/usr/bin/env python3
"""Self-check for regress.py: python -I scripts/test_regress.py"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REGRESS = Path(__file__).resolve().parent / "regress.py"


def skill(root, name, desc, h1=None):
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: >-\n  {desc}\n---\n\n# {h1 or name}\n\nBody.\n",
                                encoding="utf-8")


def run(root, base, *extra):
    p = subprocess.run([sys.executable, "-I", str(REGRESS), str(root), "--baseline", str(base), "--json", *extra],
                       capture_output=True, text=True)
    out = p.stdout[:p.stdout.rfind("}") + 1]
    return p.returncode, json.loads(out)


with tempfile.TemporaryDirectory() as tmp:
    root, base = Path(tmp) / "skills", Path(tmp) / "health.json"
    good = 'Checks a thing. Use when the user says "check my thing please". Not for writing (use writer-skill).'
    skill(root, "checker", good)
    skill(root, "writer-skill", 'Writes a thing. Use when the user says "write my thing please". Not for checks (use checker).')

    # First run against no baseline, then accept it.
    code, out = run(root, base, "--write")
    assert code == 0 and out["skills"] == 2 and out["new_skills"] == ["checker", "writer-skill"], out
    code, out = run(root, base)
    assert code == 0 and out["regressions"] == [], out

    # A dangling handoff and a shared trigger phrase are regressions.
    skill(root, "checker", good.replace("(use writer-skill)", "(use ghost-skill)"))
    skill(root, "copycat", 'Also checks. Use when the user says "check my thing please". Not for writing (use writer-skill).')
    code, out = run(root, base)
    assert code == 1, out
    assert "dangling handoff: checker -> ghost-skill" in out["regressions"], out
    assert any("trigger collision: checker & copycat" in r for r in out["regressions"]), out

    # --external accepts a skill that lives elsewhere; one-word targets are never dangling.
    skill(root, "copycat", 'Also checks. Use when the user says "copy that". Not for anything (use it).')
    code, out = run(root, base, "--external", "ghost-skill")
    assert code == 0 and out["regressions"] == [], out

    # A stale H1 is a new WARN; fixing it later is reported as an improvement.
    skill(root, "writer-skill", 'Writes a thing. Use when the user says "write my thing please". Not for checks (use checker).', h1="Old Name")
    code, out = run(root, base, "--external", "ghost-skill")
    assert code == 1 and any("writer-skill: WARN H1" in r for r in out["regressions"]), out
    run(root, base, "--external", "ghost-skill", "--write")
    skill(root, "writer-skill", 'Writes a thing. Use when the user says "write my thing please". Not for checks (use checker).')
    code, out = run(root, base, "--external", "ghost-skill")
    assert code == 0 and any("writer-skill: WARN H1" in r for r in out["improvements"]), out

    # A skill that disappears is a regression.
    (root / "copycat" / "SKILL.md").unlink()
    code, out = run(root, base, "--external", "ghost-skill")
    assert code == 1 and "copycat: skill is gone" in out["regressions"], out

print("ok")
