#!/usr/bin/env python3
"""Deterministic checks for a skill folder.

Usage: python check_skill.py <path-to-skill-folder>

Exit code 1 if any FAIL, otherwise 0. WARN lines need judgement.
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml --break-system-packages")

MAX_DESC = 1024
SOFT_DESC = 950
MAX_BODY_LINES = 500


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    folder = Path(sys.argv[1]).resolve()
    skill_file = folder / "SKILL.md"
    fails, warns = [], []

    if not skill_file.is_file():
        print(f"FAIL  no SKILL.md in {folder}")
        return 1

    text = skill_file.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        print("FAIL  SKILL.md has no YAML frontmatter between --- lines")
        return 1

    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        print(f"FAIL  frontmatter is not valid YAML: {exc}")
        return 1
    body = match.group(2)

    # name
    name = meta.get("name")
    if not name:
        fails.append("frontmatter has no name")
    else:
        if name != folder.name:
            warns.append(f"name '{name}' differs from folder '{folder.name}'")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(name)):
            fails.append(f"name '{name}' should be lowercase words joined by hyphens")
        if len(str(name)) > 64:
            fails.append("name is longer than 64 characters")

    # description
    desc = " ".join(str(meta.get("description", "")).split())
    if not desc:
        fails.append("frontmatter has no description")
    else:
        n = len(desc)
        if n > MAX_DESC:
            fails.append(f"description is {n} characters, over the {MAX_DESC} limit")
        elif n > SOFT_DESC:
            warns.append(f"description is {n} characters, close to the {MAX_DESC} limit")
        low = desc.lower()
        if "use when" not in low and "use whenever" not in low and "use this" not in low:
            warns.append("description has no 'Use when/whenever' trigger wording")
        if "not for" not in low and "do not use" not in low:
            warns.append("description has no 'Not for' boundary (fine for a skill with no siblings)")

    # H1 vs name
    h1 = re.search(r"^#\s+(.+)$", body, re.M)
    if h1 and name:
        slug = re.sub(r"[^a-z0-9]+", "-", h1.group(1).lower()).strip("-")
        if slug != name:
            warns.append(f"H1 '{h1.group(1)}' does not match name '{name}' (stale name?)")

    # body length
    lines = len(body.splitlines())
    if lines > MAX_BODY_LINES:
        warns.append(f"body is {lines} lines; move detail into references/")

    # referenced files
    refs = set(re.findall(r"`((?:references|scripts|examples|assets)/[^`\s]+)`", body))
    for ref in sorted(refs):
        if not (folder / ref).exists():
            warns.append(f"body points to {ref}, which is not in this folder")

    # count claims like "six workflows" next to a numbered table
    words = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10}
    for m in re.finditer(r"\b(two|three|four|five|six|seven|eight|nine|ten)\s+(workflows|modes|commands|steps)\b", body, re.I):
        warns.append(f"body says '{m.group(0)}'; check it matches the list that follows")

    for msg in fails:
        print(f"FAIL  {msg}")
    for msg in warns:
        print(f"WARN  {msg}")
    if not fails and not warns:
        print("OK    no findings")
    print(f"\n{len(fails)} fail, {len(warns)} warn ({len(desc)} description chars, {lines} body lines)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
