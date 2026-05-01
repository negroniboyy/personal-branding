---
name: pb-linkedin-performance
description: Review PersonalBrand LinkedIn post performance from exported LinkedIn analytics files, normalize and ingest those exports into the local SQLite tracking database, and produce brand-safe feedback that helps `pb-linkedin-gm`, `pb-content-strategy`, `pb-linkedin-title`, and `pb-linkedin-drafts` improve the next batch without overfitting noise or chasing vanity metrics.
---

# pb_linkedin_performance

## Overview

Use this skill as the LinkedIn performance-review layer for the PersonalBrand system.
Its job is to turn LinkedIn analytics exports into usable editorial feedback, not to chase virality or override the brand.

This skill should:

- request or locate a recent LinkedIn analytics export
- normalize the XLSX export into local JSON
- import matched post metrics into the local SQLite database
- classify findings as signal, weak signal, or noise
- produce a short report with 2 to 3 experiments and explicit guardrails

This skill should not:

- publish or schedule posts
- rewrite the brand voice around engagement
- declare strong conclusions from tiny samples
- write raw analytics clutter back into the control tower

Read `references/review-contract.md` before acting.

## When To Use

Use this skill when:

- the user asks to review LinkedIn performance
- the user provides a LinkedIn analytics export file
- `pb-linkedin-gm` needs a postmortem or recent-window review
- the system should compare the last 14 or 30 days against prior snapshots
- the user wants suggestions for improving reach or engagement without compromising voice

Do not use this skill for:

- title generation
- full drafting
- scheduling or publishing
- raw database maintenance without performance review intent

## Read Order

Read these sources in order:

1. `brandguide/brandbook.md`
2. `brandguide/linkedin.md`
3. `md/context_memory.md`
4. The live Google Sheet referenced by `PB_CONTENT.gsheet`, especially `Content List`
5. Local analytics artifacts when present:
   - `tmp/*.json` normalized LinkedIn analytics exports
   - `data/pb_linkedin_content.sqlite3`
6. The supplied LinkedIn analytics export `.xlsx` file when a fresh review is requested
7. `$pb-linkedin-database` only when you need the current ingest and schema behavior

Use this pass to understand:

- what was actually posted
- how the posts are categorized in the PB system
- what metrics are available versus missing
- whether the current sample is large enough for any strong recommendation

## Export Intake Workflow

Default review windows:

- `14` days for tactical review
- `30` days for pattern review

Run this workflow in order:

1. Confirm the review window from the export file or user request.
2. Parse the LinkedIn analytics `.xlsx` export into normalized JSON.
3. Match exported posts back to `Content List` using `Published URL`, `Published date`, `ID`, and title as fallbacks.
4. Import matched snapshots into the local SQLite DB.
5. Generate a short performance review.

Use these commands:

```powershell
python3 -m personalbrand.cli linkedin-analytics-parse --xlsx "<path-to-export.xlsx>"
python3 <skill-dir>\scripts\init_linkedin_content_db.py --db <repo-root>\data\pb_linkedin_content.sqlite3
python3 <skill-dir>\scripts\ingest_content_snapshot.py --db <repo-root>\data\pb_linkedin_content.sqlite3 --snapshot <repo-root>\tmp\pb_linkedin_live_sheet_snapshot.json
python3 <skill-dir>\scripts\import_linkedin_metrics.py --db <repo-root>\data\pb_linkedin_content.sqlite3 --payload-file <repo-root>\tmp\linkedin_week1_metrics_payload.json
python3 <skill-dir>\scripts\summarize_content_db.py --db <repo-root>\data\pb_linkedin_content.sqlite3
```

If the current repo helper flow already produced the normalized JSON or import payload, reuse those files instead of re-deriving them.

## Data Rules

- Treat the export file as the source of truth for the metrics it actually contains.
- Do not invent reactions, comments, reposts, views, or click counts when the export does not provide them.
- Use impressions and aggregate engagements when available.
- Compute engagement rate only when both engagements and impressions are available.
- Keep the SQLite DB as the long-lived history layer.
- Treat `PB_CONTENT` as the operating layer, not the analytics warehouse.

Write back to `PB_CONTENT` only when the user explicitly asks, and only with compact summary fields or notes.
Never dump full demographics tables, daily time series, or raw export structure into `Content List`.

## Interpretation Rules

Classify each claim you make:

- `Signal`
  - repeated pattern, enough matching data, or clear relative difference
- `Weak signal`
  - plausible pattern with low sample size or partial metric coverage
- `Noise`
  - one-off fluctuation, incomplete export coverage, or tiny sample

Default assumption:

- four posts is enough for a baseline, not enough for aggressive optimization

Prefer explanations about:

- opening clarity
- immediate reader payoff
- topic/lane mix
- post packaging versus core idea
- whether distribution is simply too early or too cold to interpret strongly

Avoid shallow recommendations about:

- hashtags
- posting hacks
- thought-leader formatting
- fake contrarian hooks
- gimmick CTAs

## Output Contract

Return a short review in this shape:

```markdown
Window reviewed:
- <date range>

What the data actually says:
- <high-confidence observation>

Signals:
- <signal finding>

Weak signals:
- <weak-signal finding>

Noise:
- <what should not be overinterpreted>

Recommendations:
1. <experiment>
2. <experiment>
3. <experiment if justified>

Do not change:
- <brand or system guardrail>
```

Recommendations must be:

- specific
- low-drama
- directly connected to observed data
- limited to 2 or 3 changes per batch

## Handoff Rules

Use this skill as a reviewer and advisor.
Do not take over downstream work.

When a recommendation is approved:

- route lane or topic adjustments to `$pb-content-strategy`
- route packaging or queue shifts to `$pb-linkedin-title`
- route post-level draft adjustments to `$pb-linkedin-drafts`
- keep historical storage and import work aligned with `$pb-linkedin-database`
- let `$pb-linkedin-gm` own sequencing and approval gates in normal operation

## Final Checks

Before finishing, confirm:

1. The export was actually parsed, not just discussed abstractly.
2. The DB import used matched posts only.
3. Missing metrics were called out explicitly.
4. Recommendations stayed inside brand and voice constraints.
5. No conclusion overclaimed certainty from a small sample.
