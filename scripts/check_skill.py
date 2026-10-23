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
    yaml = None

MAX_DESC = 1024
SOFT_DESC = 950
MAX_BODY_LINES = 500

# Wording that says the skill must run at a moment Claude does not choose. A description cannot
# make that reliable; a mod can (see skill-to-mod).
MOMENT_RE = re.compile(
    r"\b(before|prior to)\b[^.\n]{0,50}\b(push(ing)?|deploy(ing)?|ship(ping)?|releas(e|ing)|"
    r"publish(ing)?|merg(e|ing)|going live)\b", re.I)


def parse_simple(block):
    """Frontmatter without PyYAML: `key: value`, quoted values and > or | block scalars."""
    # ponytail: covers the flat frontmatter skills use; install PyYAML for nested keys or lists.
    meta, key, folded, lines = {}, None, False, []

    def flush():
        if key is not None and lines:
            meta[key] = (" " if folded else "\n").join(lines)

    for raw in block.split("\n"):
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if m:
            flush()
            key, value, lines = m.group(1), m.group(2).strip(), []
            folded = value.startswith(">")
            if value[:1] in (">", "|"):
                continue
            if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            elif re.search(r":\s|\s#", value):
                # Strict YAML loaders reject an unquoted ": " and drop text after " #"; installers use them.
                raise ValueError(f"unquoted '{key}' value contains ': ' or ' #'; quote it or use a >- block")
            meta[key], key = value, None
        elif key is not None and raw.strip():
            lines.append(raw.strip())
    flush()
    return meta


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

    # utf-8-sig and the newline fix: files saved on Windows carry a BOM or CRLF line endings.
    text = skill_file.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        print("FAIL  SKILL.md has no YAML frontmatter between --- lines")
        return 1

    if yaml is None:
        try:
            meta = parse_simple(match.group(1))
        except ValueError as exc:
            print(f"FAIL  frontmatter is not valid YAML: {exc}")
            return 1
        warns.append("PyYAML not installed; frontmatter read with the simple parser")
    else:
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
    for m in re.finditer(r"\b(two|three|four|five|six|seven|eight|nine|ten)\s+(workflows|modes|commands|steps)\b", body, re.I):
        warns.append(f"body says '{m.group(0)}'; check it matches the list that follows")

    # a skill that must run at a moment: description tuning cannot make that reliable
    moments = MOMENT_RE.findall(body)
    note = None
    if len(moments) >= 2:
        note = (f"body ties the skill to {len(moments)} moments like 'before pushing or deploying'; "
                "if a skipped run is costly, skill-to-mod can add a trigger")

    for msg in fails:
        print(f"FAIL  {msg}")
    for msg in warns:
        print(f"WARN  {msg}")
    if note:
        print(f"NOTE  {note}")
    if not fails and not warns:
        print("OK    no findings")
    print(f"\n{len(fails)} fail, {len(warns)} warn ({len(desc)} description chars, {lines} body lines)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
