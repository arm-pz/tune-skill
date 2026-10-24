#!/usr/bin/env python3
"""Regression check for a family of skills: what got worse since the last snapshot.

Usage:
  python regress.py ROOT [ROOT ...] --baseline health.json           # compare, exit 1 on regression
  python regress.py ROOT [ROOT ...] --baseline health.json --write   # accept the current state
  python regress.py ROOT ... --external seo-audit,programmatic-seo   # handoff targets you know exist elsewhere

Every folder under a ROOT that holds a SKILL.md is checked with check_skill.py (same folder as this
script). Two checks span the family, because no single file can show them:
  dangling   a description hands off with "(use X)" and no skill named X is in the family
  collision  two descriptions quote the same trigger phrase, so either may load for it

A regression is a finding that is in the current run and not in the baseline, or a skill that was in
the baseline and is gone. Fixed findings are reported as improvements; --write records them.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from itertools import combinations
from pathlib import Path

CHECK = Path(__file__).resolve().parent / "check_skill.py"
SKIP = {".git", "node_modules", "__pycache__", "dist", "out"}
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def find_skills(roots):
    found = {}
    for root in map(Path, roots):
        for skill in sorted(root.rglob("SKILL.md")):
            if SKIP & set(skill.relative_to(root).parts):
                continue
            text = skill.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
            m = re.search(r"^name:\s*['\"]?([A-Za-z0-9_-]+)", text, re.M)
            name = m.group(1) if m else skill.parent.name
            found.setdefault(name, (skill.parent, text))  # first root wins on duplicates
    return found


def description(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return ""
    block = m.group(1)
    d = re.search(r"^description:[ \t]*(.*?)(?=^\S|\Z)", block, re.M | re.S)
    if not d:
        return ""
    value = re.sub(r"^[>|][+-]?\s*", "", d.group(1).strip())
    return " ".join(value.strip("'\"").split())


def check(folder):
    p = subprocess.run([sys.executable, "-I", str(CHECK), str(folder)],
                       capture_output=True, text=True, encoding="utf-8")
    out = {"fail": [], "warn": [], "note": []}
    for line in p.stdout.splitlines():
        kind = line[:4].strip().lower()
        if kind in out:
            out[kind].append(line[6:].strip())
    # A missing PyYAML is a property of the machine, not of the skill.
    out["warn"] = [w for w in out["warn"] if not w.startswith("PyYAML not installed")]
    return out


def handoffs(desc):
    targets = set()
    for group in re.findall(r"\(use ([^)]*)\)", desc, re.I):
        for part in re.split(r",| or | and ", group):
            word = part.strip().strip("`'\"").split(" ")[0]
            if NAME.fullmatch(word):
                targets.add(word)
    return targets


def phrases(desc):
    return {p.lower().strip(" .,") for p in re.findall(r"\"([^\"]{8,})\"", desc)}


def snapshot(roots, external):
    skills = find_skills(roots)
    names = set(skills) | set(external)
    state = {"skills": {}, "dangling": [], "collisions": []}
    descs = {}
    for name, (folder, text) in sorted(skills.items()):
        desc = description(text)
        descs[name] = desc
        state["skills"][name] = {**check(folder),
                                 "description_sha": hashlib.sha256(desc.encode()).hexdigest()[:12]}
        # A one-word target ("use it") is too ambiguous to call dangling.
        for target in sorted(t for t in handoffs(desc) - names - {name} if "-" in t):
            state["dangling"].append(f"{name} -> {target}")
    for a, b in combinations(sorted(descs), 2):
        for phrase in sorted(phrases(descs[a]) & phrases(descs[b])):
            state["collisions"].append(f"{a} & {b}: \"{phrase}\"")
    return state


def findings(state):
    items = set()
    for name, s in state["skills"].items():
        for kind in ("fail", "warn", "note"):
            items.update(f"{name}: {kind.upper()} {msg}" for msg in s[kind])
    items.update(f"dangling handoff: {d}" for d in state["dangling"])
    items.update(f"trigger collision: {c}" for c in state["collisions"])
    return items


def key(finding):
    # "description is 980 characters" and "... 975 characters" are the same finding; a count
    # moving inside a message must not read as one regression plus one improvement.
    return re.sub(r"\d+", "#", finding)


def compare(old, new):
    old_f, new_f = findings(old), findings(new)
    old_keys, new_keys = {key(f) for f in old_f}, {key(f) for f in new_f}
    worse = sorted(f for f in new_f if key(f) not in old_keys)
    worse += [f"{n}: skill is gone" for n in sorted(set(old["skills"]) - set(new["skills"]))]
    better = sorted(f for f in old_f if key(f) not in new_keys)
    added = sorted(set(new["skills"]) - set(old["skills"]))
    return worse, better, added


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--write", action="store_true", help="save the current state as the baseline")
    ap.add_argument("--external", default="", help="comma-separated skills that live outside the roots")
    ap.add_argument("--json", action="store_true", help="print the comparison as JSON")
    a = ap.parse_args(argv)

    external = {e.strip() for e in a.external.split(",") if e.strip()}
    new = snapshot(a.roots, external)
    base = Path(a.baseline)
    old = json.loads(base.read_text(encoding="utf-8")) if base.is_file() else {"skills": {}, "dangling": [], "collisions": []}
    worse, better, added = compare(old, new)

    if a.json:
        print(json.dumps({"regressions": worse, "improvements": better, "new_skills": added,
                          "skills": len(new["skills"])}, indent=2))
    else:
        print(f"{len(new['skills'])} skills checked against {base if base.is_file() else 'an empty baseline'}")
        for title, rows in (("REGRESSION", worse), ("IMPROVED", better), ("NEW SKILL", added)):
            for row in rows:
                print(f"{title:<10}  {row}")
        print(f"\n{len(worse)} regressions, {len(better)} improvements, {len(added)} new skills")
    if a.write:
        base.write_text(json.dumps(new, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"baseline written: {base}")
        return 0
    return 1 if worse else 0


if __name__ == "__main__":
    sys.exit(main())
