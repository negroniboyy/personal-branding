---
name: pb-linkedin-gm
description: Orchestrate the PersonalBrand LinkedIn operating flow across the installed `pb-linkedin-*` skills plus the diary-memory refresh dependency. Use when Codex needs to review the overall LinkedIn project, refresh diary memory from Notion, inspect the Google-Sheet-managed weekly pipeline, identify what the user must approve, and propose or run a coordinated plan that hands work to `pb-content-strategy`, `pb-linkedin-title`, `pb-linkedin-drafts`, and `pb-linkedin-database`.
---

# pb_linkedin_gm

## Overview

Use this skill as the LinkedIn general manager for the PersonalBrand system.
Start by understanding the current week, the live-sheet-managed commitments, and the current approval state.
Then propose a coordinated run across the narrower `pb-linkedin-*` skills instead of doing their specialist work directly.
For normal LinkedIn operations, this is the required entrypoint. Treat the narrower skills as GM-owned handoffs, not as standalone workflow owners.
Before title planning or draft work, make sure the diary-memory layer is refreshed so downstream skills can use the latest profile and recent lived context.

Read `references/orchestration-map.md` before acting.

## Managed Skills

Treat every installed skill whose name contains `pb-linkedin` as managed scope.
At minimum, coordinate these skills when they are available:

- `$pb-content-strategy`
- `$pb-diary-memory-sync`
- `$pb-linkedin-performance`
- `$pb-linkedin-title`
- `$pb-linkedin-drafts`
- `$pb-linkedin-database`

Do not duplicate their specialist workflows inside this skill unless one of them is missing or broken.
This skill owns sequencing, scope definition, approvals, and user-facing coordination.
It also owns live-sheet state transitions even when the specialist work itself is delegated.
Treat `$pb-diary-memory-sync` as a managed upstream dependency even though its name does not contain `pb-linkedin`.
Use `$pb-content-strategy` as the upstream strategy layer when the system needs content-direction decisions before new title generation.
Use `$pb-linkedin-performance` as the performance-review layer when recent LinkedIn exports or stored metrics should shape the next batch.

## Weekly Review Workflow

Default to a 7-day planning window anchored to the user's current local date unless the user asks for a different horizon.

Run this workflow in order:

1. Read the whole project context, not just LinkedIn.
2. Refresh or verify the diary-memory outputs through `$pb-diary-memory-sync` before downstream content work.
3. Check the live Google Sheet LinkedIn pipeline first. Use the local workbook review helper only as a fallback.
4. Identify the upcoming LinkedIn-relevant due dates and production tasks for the next 7 days.
5. Decide whether the run needs strategy recalibration before more title generation.
6. Decide whether recent exported performance data should be reviewed before changing the queue.
7. Review the current approval state across the content pipeline.
8. Tell the user exactly what needs approval before work should continue.
9. Ask whether to proceed with a coordinated plan.
10. Only after explicit approval, execute the plan and hand work to the narrower skills.

## Project Context Pass

Before checking tasks, read these sources in order:

1. `md/context_memory.md`
2. `brandguide/brandbook.md`
3. `brandguide/linkedin.md`
4. `brandguide/memory_notion/profile.md`
5. `brandguide/memory_notion/recent.md` when recent diary context matters for the current window
6. The live Google Sheet referenced by `PB_CONTENT.gsheet`, active tabs `Content List` and `Content Live`
7. `contents/CONTENT.xlsx` only if the live sheet is unavailable or the user explicitly wants the local backup
8. The SKILL files for the installed `pb-linkedin-*` skills being coordinated plus `$pb-diary-memory-sync`
9. `$pb-content-strategy` when strategy recalibration is likely needed
10. `$pb-linkedin-performance` when recent exported metrics should shape the review

Use this pass to understand:

- the current PersonalBrand operating model
- the user's stable profile, recurring themes, and current lived context from diary memory
- the monthly and weekly LinkedIn commitments
- which LinkedIn tasks are likely to require planning, drafting, or analysis work
- whether the current queue needs a strategy reset before more proposal rows are added
- whether recent exported performance data suggests packaging or lane adjustments

## Diary Memory Gate

Treat diary memory as the default upstream grounding layer for LinkedIn work.

- Refresh it through `$pb-diary-memory-sync` before title generation or new draft creation when the files are missing, clearly stale, or the user has added meaningful diary entries since the last sync.
- Prefer `brandguide/memory_notion/profile.md` as the durable brand-and-reality anchor.
- Read `brandguide/memory_notion/recent.md` when selecting a timely angle, recent project thread, or concrete lived detail.
- Use `brandguide/memory_notion/diary.db` only as a retrieval backstop when `profile.md` or `recent.md` are not sufficient.
- If the sync fails, say so clearly and continue in degraded mode rather than pretending the memory layer is current.

## Live Control Tower

Use the Google Sheet referenced by `PB_CONTENT.gsheet` as the operational source of truth for due dates, production status, scheduling, manual publish tracking, and row-level coordination between the skills.

Active live tabs:

- `Content List`
- `Content Live`

Use Google Sheets tools to inspect and update those tabs directly.

Keep `contents/CONTENT.xlsx` only as a fallback backup or repair target.

Preferred sequence:

```powershell
Use Google Sheets tools to read spreadsheet metadata plus `Content List!A:P` and `Content Live!A:M`
Write a local snapshot JSON to <repo-root>\tmp\pb_linkedin_live_sheet_snapshot.json
python <skill-dir>\scripts\review_content_snapshot.py --snapshot <repo-root>\tmp\pb_linkedin_live_sheet_snapshot.json --days 7 --start-date <YYYY-MM-DD>
Fallback only:
python <skill-dir>\scripts\normalize_content_workbook.py --workbook <repo-root>\contents\CONTENT.xlsx
python <skill-dir>\scripts\review_content_workbook.py --workbook <repo-root>\contents\CONTENT.xlsx --days 7 --start-date <YYYY-MM-DD>
```

The live-sheet helper flow reads the Google Sheet first and uses a local snapshot file only as a transport format for downstream review logic.

The fallback helper script reads the local backup workbook and returns:

- upcoming due items inside the current review window
- generated rows that still need review approval
- rows that need refinement before title approval because control-tower fields are still missing
- track-split review queues for TurboBaba and learning-in-public rows
- user-entered manual seed rows
- rows in `Backlog` that are eligible for drafting
- rows currently in `Drafting`
- rows in `Ready`
- rows in `Done`

Base the weekly plan on actual live-sheet rows, dates, and status fields.

Expected `Content List` columns:

- `ID`
- `Title`
- `Review decision`
- `Content`
- `Category`
- `Channel`
- `Planner Source`
- `Production status`
- `Draft due`
- `Review due`
- `Scheduled date`
- `Draft doc`
- `Publish status`
- `Manager notes`
- `Published date`
- `Published URL`

Expected `Content Live` support columns:

- `ID`
- `Title`
- `When to post`
- `Angle`
- `Narrative spine`
- `Source fit`
- `Core tension`
- `Opening scene`
- `Notes`
- `Draft due`
- `Review due`
- `Scheduled date`
- `Production status`

## Row Hygiene Gate

Before GM treats a generated row as review-ready, it must contain:

- `Title`
- `Content`
- `Category`
- `Channel`
- `Planner Source`
- `Production status`

Rows missing any of those fields go into a refinement queue, not the normal title-approval queue.

## Track-Aware Review Queue

When the active queue mixes different content lanes, GM should split blank-review rows into separate review groups instead of treating them as one narrative sequence.

Use `Category` as the first signal for track ownership:

- `TurboBaba / ...` = TurboBaba narrative queue
- `Learning in public / ...` = learning-in-public or workflow-lessons queue

Use `Planner Source` as the fallback signal:

- `Block ...` = TurboBaba narrative queue
- `Bonus swap-in` = learning-in-public support queue

Interpret live-sheet rows through two dimensions:

- `Review decision`
  - blank = generated row awaiting approval
  - `Approved` = approved generated row
  - `Disapproved` = rejected generated row
  - `MANUAL` = user-seeded non-TurboBaba idea that can still go through title and draft work
- `Production status`
  - `Backlog`
  - `Drafting`
  - `Ready`
  - `Done`

Prioritize rows that are:

- due within the next 7 days
- missing an approval that blocks production
- in `Backlog` and eligible for drafting
- in `Drafting` and still waiting on draft completion
- in `Ready` and still waiting on manual review, scheduling, or manual publish tracking

If live-sheet access fails, say so clearly and fall back to the local workbook helper or the latest local planning artifacts.
Do not pretend the live-sheet review succeeded when it did not.

GM should never treat `MANUAL` rows as blocked review items.
Treat them as editable seed briefs that may still need title refinement, drafting, scheduling, and manual publish tracking.

## Approval Gates

Always make the approval requirements explicit before proposing execution.

Common approvals to call out:

- approval to use the proposed 7-day work window
- approval to refresh diary memory when the run should pull Notion and rewrite the local memory files
- approval of any strategy directions produced by `$pb-content-strategy` before they are converted into title rows
- approval to ingest a recent LinkedIn analytics export and use it for performance review through `$pb-linkedin-performance`
- approval of title candidates generated by `$pb-linkedin-title`
- approval of any draft selected for refinement or finalization by `$pb-linkedin-drafts`
- approval of scheduled publish dates or rescheduling changes recorded in the live sheet
- approval for database or metrics ingest actions that will change the tracking state through `$pb-linkedin-database`
- approval to proceed with the overall coordinated run

When summarizing approvals, separate:

- approvals needed now
- approvals that will be needed later in the run

## Weekly Priority Order

Use this execution order when the live sheet contains both scheduled-ready rows and review backlog rows:

1. Reconcile `Ready` rows with near-term scheduled dates before expanding the backlog
2. Refine any rows that fail the row-hygiene gate
3. Review learning-in-public support rows and TurboBaba continuation rows as separate approval groups
4. Only generate another title batch after the current review queue is internally consistent

## Plan Proposal

After the weekly review, ask the user whether to proceed with a plan.
The plan must describe:

- the 7-day window being covered
- the sheet basis used
- whether diary memory will be refreshed first and which memory outputs will be used
- whether `$pb-content-strategy` will be used before title generation
- which `pb-linkedin-*` skills will be used
- what each skill will do
- which outputs or state changes each step will produce
- which approval checkpoint follows each step

Keep the plan operational and short.
Do not execute the downstream skills until the user says to proceed.

## Execution Rules

After the user approves the plan:

- call the narrower `pb-linkedin-*` skills in the order required by the plan
- carry forward only the minimum context each downstream skill needs
- preserve human-in-the-loop review before anything that changes approved content state
- report progress in terms of completed steps, pending approvals, and blockers

Use these defaults:

- `$pb-content-strategy` first when the review queue is thin, the monthly arc needs recalibration, the content mix is drifting, or the user explicitly asks for topic strategy
- `$pb-diary-memory-sync` first when the memory outputs are missing, stale, or likely outdated relative to current diary work
- `$pb-linkedin-title` after approved strategy directions exist, or first when the task is direct row refinement and no strategy reset is needed
- `$pb-linkedin-drafts` after an `Approved` or `MANUAL` row is selected for draft creation or revision
- `$pb-linkedin-database` after planning or draft work when live-sheet state should be ingested or analyzed

Use these live-sheet state rules:

- generated proposal rows default to blank `Review decision` and `Production status = Backlog`
- approved generated rows keep `Review decision = Approved` and stay in `Backlog` until drafting starts
- manual seed rows keep `Review decision = MANUAL` and default to `Backlog`
- when GM routes a row to drafting, set `Production status = Drafting`
- when a draft is created and the `.docx` is written, set `Production status = Ready` and fill `Draft doc`
- when the user manually schedules a post, keep `Production status = Ready`, fill `Scheduled date`, and optionally set `Publish status = Scheduled manually`
- when the user manually publishes a post, set `Production status = Done`, fill `Published date` and `Published URL`, and optionally set `Publish status = Published manually`

## Final Response Shape

Before execution approval, return:

```markdown
Weekly window:
- <date range>

Upcoming work:
- <task>

Needs approval now:
- <approval>

Later approvals:
- <approval>

Proposed run:
1. <skill and action>
2. <skill and action>
3. <skill and action>
```

After execution starts, return:

- completed steps
- current blocker or pending approval
- next planned skill handoff
