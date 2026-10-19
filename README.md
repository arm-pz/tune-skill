# tune-skill

An agent skill that audits and fine-tunes a skill that **already exists**. Give it a `SKILL.md` and its
siblings, and it checks the description that does the triggering, finds where two skills claim the same
request, catches stale names and counts, fixes handoff contracts and command routing, makes the smallest
evidenced edits, and validates them with a script rather than by eye.

It is explicitly not a rewrite. Every finding has to carry the quoted line, a severity, and the smallest
fix — and the skill is required to say which checks ran, which test cases were only written, and which
files it never got to see.

## Install

```
npx skills add arm-pz/tune-skill --skill tune-skill
```

Or copy the `tune-skill/` folder into `~/.qoder/skills/` (Qoder) or `~/.claude/skills/` (Claude Code),
then start a new session.

The validator is plain Python 3 and needs PyYAML:

```bash
pip install pyyaml
python scripts/check_skill.py /path/to/any-skill-folder
```

You can use `check_skill.py` on its own, without the skill, as a structural linter for any `SKILL.md`.

## Ask it things like

- "This skill fires on the wrong requests — what's wrong with its description?"
- "I have two skills that both claim SEO audits. Split them cleanly."
- "Review this SKILL.md I just pasted and fix it minimally."
- "Make sure this skill hands off to its sibling instead of duplicating it."

## What the validator checks

| Check | Level |
|---|---|
| `name` is lowercase-hyphen and 64 characters or fewer | FAIL |
| Description within 1024 characters | FAIL |
| Description has trigger wording and a boundary clause | WARN |
| Folder name, frontmatter `name` and H1 agree | WARN |
| Every backticked `references/`, `scripts/`, `examples/`, `assets/` path exists | WARN |
| Body under about 500 lines | WARN |
| A stated count ("three steps") matches what follows | WARN |

Exit code 1 on any FAIL. Description is reported in characters and the body in lines, so a run is
reproducible.

## Layout

```
tune-skill/
├── SKILL.md
├── LICENSE
├── references/
│   ├── audit-checklist.md   # the eight audit sections, with severity rules
│   └── test-cases.md        # the >=8-case format: clear, implicit, near-miss, boundary pairs
└── scripts/
    └── check_skill.py       # the deterministic validator, runnable standalone
```

## Boundaries

- **Handles:** a skill that exists and needs tightening, debugging or reviewing.
- **Does not handle:** creating a skill from scratch ([`draft-skill`](https://github.com/arm-pz/draft-skill)),
  or from a list of prompts
  ([`prompts-to-skill`](https://github.com/arm-pz/prompts-to-skill)).
- **Related:** [`prompts-to-skill-release`](https://github.com/arm-pz/prompts-to-skill-release) releases
  what this skill tunes, and checks its gate against this skill's validator.

## Provenance and status

Written by the author and used on this machine since 2026-10-18 to audit and tune the other `arm-pz`
skills. `SKILL.md` passes its own validator: 0 FAIL, 0 WARN, 769 description characters, 58 body lines.
The skill's own trigger test cases have **not** been run in a live session, and no `evals/` file is
shipped.

## License

MIT. See `LICENSE`.
