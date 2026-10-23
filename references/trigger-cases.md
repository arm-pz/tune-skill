# Trigger cases for tune-skill

Written to the format in `references/test-cases.md` (this skill's own case guide). The skill under
test is `tune-skill`, judged from its `description` frontmatter only, as an agent deciding what to
load would. Competing descriptions read for these cases: `draft-skill`, `prompts-to-skill`,
`prompts-to-skill-release`, `findable`, `upstream-check`, and the user's own chain skills
`skill-launch` and `tune-and-polish`, plus Qoder's built-in `skill-creator`.

**Run:** hand-run on 2026-10-19 against the descriptions only. No automated triggering loop was
run; none exists here.

## Cases

| # | Message | Expected skill | Pass condition | Result |
| --- | --- | --- | --- | --- |
| 1 | "`resume-check` isn't triggering when I paste a CV. Why?" | tune-skill | opens the real `SKILL.md` before saying anything | PASS ("says a skill is not triggering") |
| 2 | "This skill fires on every writing request. It's too greedy, tighten it." | tune-skill | one evidenced edit to the description, not a rewrite | PASS ("fires on the wrong requests") |
| 3 | "Here's my SKILL.md. Tell me what's wrong with it." (pasted text) | tune-skill | saves the text to a folder named after the skill and runs the validator there | PASS ("pastes a SKILL.md … asks what is wrong with it") |
| 4 | "Two of my skills keep fighting over the same requests." | tune-skill | gives one owner per request and writes a boundary pair | PASS ("wants two skills to work together or split cleanly") |
| 5 | "Review this skill repo before I publish it." | tune-skill | names the files it never opened | PASS ("improve, … or review a skill") |
| 6 | "The README says nine modes but I only count seven in the body." | tune-skill | fixes the count from the body, not the reverse | FAIL: three descriptions claim it: tune-skill ("stale names and counts"), `upstream-check` ("why a site and a README list different numbers than GitHub"), `findable`. Which one loads depends on whether the reader thinks the mismatch is internal or published |
| 7 | "I want a skill that does this from scratch." | draft-skill | tune-skill does not load | PASS ("Not for creating a skill from scratch") |
| 8 | "Turn this list of prompts into a skill." | prompts-to-skill | tune-skill does not load as the author | PASS ("… or from a list of prompts") |
| 9 | "Tune the titles on my site pages so they don't cannibalise each other." | keyword-guard / keyword-resolver | tune-skill does not load | PASS: shares the verb "tune", different object |
| 10 | "Update my existing skill." on a machine with Qoder's built-in `skill-creator` | tune-skill alone | only one loads | FAIL: `skill-creator`'s description explicitly covers "or update an existing skill". "update", "improve" and "tweak" are the verbs users actually type, and the built-in claims them |
| 11 | "My skill's description is off, fix it." (no polish requested) | tune-skill | does not drag in a discovery audit | FAIL: `tune-and-polish` claims "fix a skill that isn't triggering correctly or overlaps with siblings" nearly verbatim, and its own description says it chains tune-skill. An agent picking the chain does more work than asked |
| 12 | "I changed three descriptions today. Did anything in my skills folder get worse?" | tune-skill | runs `regress.py` against the saved baseline and lists regressions before any fix | PASS ("asks whether anything in a set of skills got worse"); hand-run 2026-10-23 |

## Boundary pairs

| Message | Should trigger | Why |
| --- | --- | --- |
| "Make me a new skill for invoice parsing" | draft-skill | nothing exists |
| "My invoice skill grabs the wrong requests" | tune-skill | it exists and misfires |
| "Here are eight prompts, make a skill" | prompts-to-skill | prompt list is the input; it calls tune-skill internally at step 3 |
| "The skill from those prompts triggers badly" | tune-skill | the batch is already a skill |
| "Package it and run the tests" | prompts-to-skill-release | edits are done |
| "It fails one of its test cases" | tune-skill | behaviour, not packaging |
| "Tune it and then make the repo findable" | tune-and-polish | two jobs, one named chain |
| "Just tune it" | tune-skill | no polish asked for |

Spans both: "check my skill's triggering and then fix its README for search" → `tune-skill` first,
hand back the findings and the edited description, then `findable` (or the `tune-and-polish` chain
if the user names both in one breath). tune-skill must not rewrite the listing itself.

## Found while writing these cases

`findable`'s description used to end with "Not for tuning a SKILL.md description so an agent
triggers it better; use skill-creator for that." The 2026-10-19 rewire pointed tune-skill, prompts-to-skill and
prompts-to-skill-release at draft-skill, but missed findable: the stale pointer was live in
`findable/skills/findable/SKILL.md` (description and the "Two audiences" body line), in its README,
and in `findable/tests/test-discovery.md` (four rows assign authoring and tuning to skill-creator).
So findable's own test suite expects a skill arm-pz does not ship and cannot vendor: Qoder's
built-in carries no redistribution licence.

**Fixed 2026-10-19**, same day, in `arm-pz/findable` commit `a8581c8`: the description, the
two-audiences body line, the README boundary and all four rows of `tests/test-discovery.md` now
name `draft-skill` and `tune-skill`. The flat install was re-copied from the repo byte-for-byte and
`check_skill.py` reports 0 fail / 0 warn on both copies. `arm-pz/findable-polish` carried the same
stale pointer in two lines and was fixed the same way (`9d9173b`). **Neither commit is pushed**, so
the published READMEs and the findable tarball still carry the old pointer until the owner approves
the push and rebuilds the artifact.

## Fixed 2026-10-19 in the sibling repos

`tune-and-polish` no longer copies this skill's trigger wording: its description requires both
halves at once and its Boundaries send a triggering-only request back here. `skill-launch` dropped
the prompt-list `argument-hint` and hands a prompt batch to prompts-to-skill.
`prompts-to-skill-release` narrowed its "publish to GitHub" trigger to a finished skill folder in
context, and names `upstream-check` for pushing clones. All three are committed locally, **not
pushed**, so the published listings still show the old wording.

## Not verified

- Which skill an agent picks when `skill-creator` is loaded alongside tune-skill; only the
  descriptions were compared, not a real triggering run.
- Whether the validator catches a description that is *semantically* too greedy; it checks length
  and wording, not overlap. Overlap is the audit checklist's job.
