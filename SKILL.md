---
name: tune-skill
description: Audit and fine-tune an existing agent skill so it triggers when it should and hands off cleanly to its siblings. Reads the real SKILL.md and references, checks the description, sibling overlaps, stale names and counts, handoffs and command routing, makes minimal evidenced edits, validates them with a script, writes near-miss test cases, and re-checks the whole family against a saved baseline. Use whenever the user wants to fine tune, improve, tighten, debug or review a skill, says a skill is not triggering or fires on the wrong requests, wants two skills to work together or split cleanly, asks whether anything in a set of skills got worse, or pastes a SKILL.md or repo link and asks what is wrong with it, even if they never say "audit". Not for creating a skill from scratch (use draft-skill) or from a list of prompts (use prompts-to-skill), or for making a skill run automatically at a moment such as before git push (use skill-to-mod).
---

# Tune skill

Fine-tuning is a set of small, evidenced edits to a skill that already exists. It is not a rewrite. The goal is a skill that triggers on the right requests, stays out of its siblings' way, and passes work along in a defined shape.

## Ground rules

- **Read the real SKILL.md first.** READMEs, repo descriptions and listings drift from the file the agent actually loads. Any claim about a skill must come from its SKILL.md or its references. If you can't open a file, name it and say what you are inferring instead.
- **Check your own claims.** If a file you read later contradicts something you said earlier, say so plainly and correct it. Don't quietly route around it.
- **Minimal edits, the author's voice.** Change what the audit found and nothing else. Keep frontmatter keys you don't recognise (`version`, `argument-hint`, `user-invocable`). Never weaken honesty, safety or privacy rules.
- **Don't claim what you didn't run.** Say which checks ran, which test cases were only written, and which files you never saw.

## Workflow

### 1. Collect

Get the SKILL.md of the target skill and of every sibling it touches, plus any references you can reach. If the user gives a link you can't open, ask for the file text or its URL. If the skill is a folder on disk, run the check script (step 6) now for a first read.

### 2. Map

Write a short inventory per skill: what its description promises, its modes or commands, the reference files it names, and what it hands off and to whom. Put sibling descriptions and command lists side by side. Overlaps only show up when you can see both.

### 3. Audit

Work through `references/audit-checklist.md`. For each finding record the evidence (quote the line), the severity (breaks triggering, confusing, or cosmetic) and the smallest fix. Report the most severe first.

### 4. Settle boundaries

When two skills claim the same request, give it one owner. Use the split the user's own design already uses (for example verdict versus artifact: one skill judges, the other writes). Ask the user only when their design doesn't settle it, and ask once.

### 5. Edit

Make the smallest change that fixes each finding. When the user will drop the result straight into a repo, hand back whole replacement files and copy untouched text exactly. When a fix needs a new shared piece (a handoff format, say), add a new reference file instead of editing one you haven't seen. List any reference files that probably need a matching update.

### 6. Validate

Run the check script on each skill folder:

```
python scripts/check_skill.py <path-to-skill-folder>
```

It checks that the name matches the folder, the description fits the 1024-character limit and has trigger and boundary wording, the H1 matches the name, referenced files exist, and the body stays a reasonable length. Fix every FAIL. Judge each WARN. A NOTE means the body ties the skill to a moment Claude does not choose (before pushing, deploying, releasing); see section H of the checklist. The script reads CRLF and BOM files and works without PyYAML; `python -I scripts/test_check_skill.py` is its self-check. If you only have pasted text, save the SKILL.md into a folder named after the skill and run it there; missing-reference warnings are expected in that case.

### 7. Write test cases

Follow `references/test-cases.md`. Every boundary you changed gets one case on each side. Run them by hand against the descriptions. Some agents ship an automated triggering loop in their authoring tooling; if you didn't run one, don't imply you did. Say which you did.

### 8. Regress the family

One skill's fix can break a sibling: a reworded description now shares a trigger phrase, or a
renamed skill leaves "(use old-name)" behind elsewhere. After editing, re-check every skill in the
family against the last accepted state:

```
python scripts/regress.py <folder-of-skills> [more folders] --baseline health.json
python scripts/regress.py <folders> --baseline health.json --write   # accept, once reviewed
```

It runs `check_skill.py` on every SKILL.md it finds and adds two family-wide checks: a dangling
handoff (a description says "(use X)" and no X is in the family) and a trigger collision (two
descriptions quote the same phrase). Anything new since the baseline is a regression and exits 1;
anything that went away is an improvement. Pass skills that live elsewhere with
`--external name,name`. Write the baseline only after reading the regressions, never to silence
them. Keep `health.json` next to the family (a site repo, a marketplace) so a scheduled CI job can
run the same command and open an issue when it fails; `python -I scripts/test_regress.py` is its
self-check.

### 9. Report

Keep it short:

- What changed, per skill, and why (one line each).
- Corrections to anything you said earlier.
- What you could not see or did not run.
- One next step.

Lead with the changes, not with the process.
