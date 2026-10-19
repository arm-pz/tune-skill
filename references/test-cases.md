# Test cases for a tuned skill

A description is only tuned once you have tried it against requests it should and shouldn't catch. Write the cases down even if you can't run them yet.

## What to write per skill

At least eight cases:

- **3 clear triggers.** Realistic messages in the user's own words, without the skill's name.
- **2 implicit triggers.** The user wants the outcome but describes it differently ("why am I not getting callbacks" for a resume judging skill).
- **3 near-misses.** Messages that should not trigger this skill:
  - the sibling skill's job
  - an adjacent task that is out of scope
  - a message that shares keywords with the description but wants something else

## Boundary pairs

Every boundary you changed gets one case on each side, written as a pair:

| Message | Should trigger | Why |
| --- | --- | --- |
| "Rewrite my bullets for this role" | applicant-kit | writes the better version |
| "Which of my bullets are weakest?" | recruiter-lens | diagnoses only, then offers the handoff |

Add one case for a message that spans both ("check my resume and then fix it"). It should start with the judging skill, hand over the findings block, and end with the writing skill.

## Case format

| # | Message | Expected skill | Expected mode or command | Pass condition |
| --- | --- | --- | --- | --- |

The pass condition is something you can check: "does not rewrite any bullet", "ends with a one-line handoff offer", "asks once for the missing JD".

## Running them

- **By hand:** read only the descriptions and decide, for each message, which skill an agent would pick. Mark each case pass or fail. This is quick and catches most overlaps.
- **With tooling:** some agents ship a description-improvement loop that runs cases against real triggering. It does not run in a plain chat, so don't claim it did — record it as not run.

Record the results in the report: how many cases, how many were run, which failed, and what you changed because of them.
