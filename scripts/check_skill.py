#!/usr/bin/env python3
"""Deterministic checks for a skill folder.

Usage: python check_skill.py <path-to-skill-folder> [--lint]

Exit code 1 if any FAIL, otherwise 0. WARN lines need judgement.

--lint adds three pass-or-fail rules for how the workflow is written (after Uber's skill linter):
  numbered-steps    steps are numbered; each has one objective and some way to verify it
  command-checked   each step gives a concrete command and checks its result before the next
  error-recovery    a section with a table of failures and their fixes; "try again" is not a fix
They print as LINT lines, which regress.py ignores, so a family baseline does not move until a
caller opts in. A failed lint rule makes the exit code 1.
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


NUMBERS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten".split())}


def list_sizes(body):
    """Entry counts of every Markdown table (data rows) and top-level list in the body."""
    sizes, rows, items = set(), 0, 0
    for line in body.split("\n") + [""]:
        s = line.strip()
        if s.startswith("|"):
            if not re.fullmatch(r"\|[\s:|-]+\|?", s):
                rows += 1
            continue
        if rows:
            sizes.add(rows - 1)  # minus the header row
            rows = 0
        if re.match(r"(\d+[.)]|[-*])\s", line):
            items += 1
            continue
        if items and (not s or line.startswith((" ", "\t"))):
            continue  # a blank line or an indented continuation stays in the list
        if items:
            sizes.add(items)
            items = 0
    if items:
        sizes.add(items)  # a list that runs to the end of the body
    return sizes


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


# --lint: how the workflow is written. Heuristics, so each rule names the steps it flagged.
VERBS = ("add|apply|ask|build|check|classify|clone|commit|confirm|create|deploy|draft|fetch|fix|"
         "install|merge|open|push|read|record|remove|report|run|save|score|send|test|update|"
         "validate|write")
MULTI_RE = re.compile(rf"\bthen\b|;|\band (?:{VERBS})\b", re.I)
VERIFY_RE = re.compile(
    r"\b(verif\w*|confirm\w*|check\w*|expect\w*|make sure|ensure|wait for|until|pass(es|ed)?|"
    r"fail(s|ed)?|exit(s)? (code )?\d|exit code|should (print|show|return|list|read|say|match)|"
    r"compare|look for|shows?|prints?|returns?|matches|count(s)?|non-?empty|empty|"
    r"stop (if|and|when)|if (it|this|that|the|any|nothing|not)\b)", re.I)
RESULT_RE = re.compile(
    r"\b(exit(s)? (code )?\d|exit code|exits|prints?|returns?|outputs?|result|pass(es|ed)?|"
    r"fail(s|ed)?|should|expect\w*|shows?|lists?|count|empty|error|matches|succeed\w*)\b", re.I)
CMD_SPAN_RE = re.compile(r"`([^`\n]+)`")
RECOVERY_HEAD_RE = re.compile(
    r"^#{2,4}\s+.*\b(error|errors|failure|failures|recover\w*|troubleshoot\w*|when .* (fails|breaks)|"
    r"goes wrong|gotchas?)\b", re.I | re.M)
RETRY_ONLY_RE = re.compile(r"^(just )?(try( it)? again|retry( it)?|re-?run( it)?|run( it)? again)\.?$", re.I)


def find_steps(body):
    """Numbered steps: '### 1. Title' headings, else the longest top-level '1.' list (3+ items)."""
    heads = list(re.finditer(r"^(#{2,4})\s+(\d+)[.)]\s+(.+)$", body, re.M))
    if len(heads) >= 2:
        steps = []
        for i, h in enumerate(heads):
            level = len(h.group(1))
            end = len(body)
            for nxt in re.finditer(r"^(#{1,4})\s", body[h.end():], re.M):
                if len(nxt.group(1)) <= level:
                    end = h.end() + nxt.start()
                    break
            steps.append((h.group(2), h.group(3).strip(), body[h.end():end]))
        return steps
    best, cur = [], []
    for line in body.split("\n") + [""]:
        m = re.match(r"(\d+)[.)]\s+(.*)", line)
        if m:
            cur.append([m.group(1), m.group(2), m.group(2)])
        elif cur and (line.startswith((" ", "\t")) or not line.strip()):
            if line.strip():
                cur[-1][2] += "\n" + line
        else:
            if len(cur) > len(best):
                best = cur
            cur = []
    if len(cur) > len(best):
        best = cur
    if len(best) < 3:
        return []
    return [(n, title.split(". ")[0][:80], text) for n, title, text in best]


def has_command(text):
    if re.search(r"^```", text, re.M) or re.search(r"^( {4}|\t)\S", text, re.M):
        return True
    for span in CMD_SPAN_RE.findall(text):
        if re.search(r"\s-{1,2}\w|\.(py|sh|js|mjs|ts)\b|^(python3?|node|npx|npm|git|gh|bash|sh|"
                     r"curl|make|claude|uv|pip|pytest)\b", span.strip()):
            return True
    return False


def lint(body):
    """Return [(rule, ok, detail)]."""
    out = []
    steps = find_steps(body)
    if not steps:
        out.append(("numbered-steps", False, "no numbered steps (use '### 1. Title' or a 1. 2. 3. list)"))
        out.append(("command-checked", False, "no numbered steps to check"))
    else:
        multi = [n for n, title, _ in steps if MULTI_RE.search(title)]
        unverified = [n for n, title, text in steps if not VERIFY_RE.search(title + "\n" + text)]
        bad = []
        if multi:
            bad.append(f"more than one objective in step {', '.join(multi)}")
        if unverified:
            bad.append(f"no way to verify step {', '.join(unverified)}")
        out.append(("numbered-steps", not bad,
                    "; ".join(bad) if bad else f"{len(steps)} steps, one objective each, each verifiable"))
        no_cmd = [n for n, title, text in steps if not has_command(text)]
        no_result = [n for n, title, text in steps if has_command(text) and not RESULT_RE.search(text)]
        bad = []
        if no_cmd:
            bad.append(f"no concrete command in step {', '.join(no_cmd)}")
        if no_result:
            bad.append(f"command result not checked in step {', '.join(no_result)}")
        out.append(("command-checked", not bad,
                    "; ".join(bad) if bad else f"{len(steps)} steps, each with a command and a result check"))

    section = None
    for h in RECOVERY_HEAD_RE.finditer(body):
        nxt = re.search(r"^#{1,4}\s", body[h.end():], re.M)
        text = body[h.end(): h.end() + nxt.start()] if nxt else body[h.end():]
        rows = [l.strip() for l in text.splitlines()
                if l.strip().startswith("|") and not re.fullmatch(r"\|[\s:|-]+\|?", l.strip())]
        if len(rows) >= 3:  # header + two failures
            section = rows[1:]
            break
    if section is None:
        out.append(("error-recovery", False, "no error recovery section with a failure | fix table (2+ rows)"))
    else:
        retry = [r.split("|")[1].strip() for r in section
                 if RETRY_ONLY_RE.match([c.strip() for c in r.strip("|").split("|")][-1])]
        out.append(("error-recovery", not retry,
                    f"'try again' is not a fix for: {', '.join(retry)}" if retry
                    else f"{len(section)} failures, each with a fix"))
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--lint"]
    do_lint = len(args) != len(sys.argv) - 1
    if len(args) != 1:
        print(__doc__)
        return 2

    folder = Path(args[0]).resolve()
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

    # count claims like "six workflows": some table or list in the body should have that many entries
    for m in re.finditer(r"\b(two|three|four|five|six|seven|eight|nine|ten)\s+(workflows|modes|commands|steps)\b", body, re.I):
        claimed = NUMBERS[m.group(1).lower()]
        if claimed not in list_sizes(body):
            warns.append(f"body says '{m.group(0)}' but no table or list in it has {claimed} entries")

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
    lint_failed = 0
    if do_lint:
        results = lint(body)
        lint_failed = sum(not ok for _, ok, _ in results)
        print()
        for rule, ok, detail in results:
            print(f"LINT  {'PASS' if ok else 'FAIL'} {rule}: {detail}")
        print(f"lint: {len(results) - lint_failed} pass, {lint_failed} fail")
    return 1 if fails or lint_failed else 0


if __name__ == "__main__":
    sys.exit(main())
