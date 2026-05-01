---
name: pb-linkedin-database
description: Create and manage a SQLite database for PersonalBrand LinkedIn content so Codex can track content inventory, review decisions, planner slots, publication state, and post-performance history for future analysis and improvement. Use when Codex needs to initialize the LinkedIn content database, ingest or sync tracked content from the live sheet referenced by `PB_CONTENT.gsheet` or its fallback workbook export, import LinkedIn performance metrics, or summarize patterns a digital marketing analyst would review for future content decisions.
---

# pb_linkedin_database

## Overview

Use this skill to keep a structured SQLite database for PersonalBrand LinkedIn content and performance.
Start with LinkedIn-only tracking, preserve room for more channels later, and treat LinkedIn API access as optional until credentials and product access are confirmed.
Use it through `$pb-linkedin-gm` for normal operations so database actions stay downstream from the live Google Sheet workflow instead of competing with it.

## Primary Workflow

Run this workflow in order unless the user asks for only one step.

1. Initialize the database schema.
2. Ingest the current tracked content inventory from the live Google Sheet or an exported fallback workbook copy.
3. Import LinkedIn performance snapshots when metrics are available.
4. Generate summary views for future planning and performance review.

Use these helper scripts:

```powershell
python scripts/init_linkedin_content_db.py --db <db-path>
python scripts/ingest_content_snapshot.py --db <db-path> --snapshot <repo-root>\tmp\pb_linkedin_live_sheet_snapshot.json
# Fallback workbook ingest only:
python scripts/ingest_content_workbook.py --db <db-path> --workbook <repo-root>\contents\CONTENT.xlsx
python scripts/import_linkedin_metrics.py --db <db-path> --payload-file <metrics.json>
python scripts/summarize_content_db.py --db <db-path>
```

Read `references/schema.md` for table intent and `references/linkedin-api.md` before promising live API sync behavior.

## Source Priority

Use source systems in this order.

1. Current live Google Sheet state for planning, review, production, scheduling, and manual publish fields
2. Local SQLite database for historical truth and analysis
3. LinkedIn metrics payloads for post-performance snapshots
4. Planner docs, brand docs, and review notes for interpretation

Do not overwrite analyst history or snapshot history when a newer ingest happens. Upsert the current item state and append performance snapshots.

## Database Rules

- Keep the schema LinkedIn-first but channel-capable.
- Preserve enough detail to answer analyst questions later without storing unnecessary noise.
- Track both current state and historical changes where it matters.
- Prefer explicit nullable fields over hidden assumptions.
- Store raw metrics payloads for auditability when importing external data.

The database must support at least:

- content inventory
- planner slots and unshipped ideas
- review decisions
- production status and due dates
- draft document tracking
- manual publish tracking
- performance snapshots over time
- sync history

## Ingest Rules

When importing the content manager:

- Prefer the live Google Sheet tabs `Content List` and `Content Live`
- For normal operations, read those tabs with Google Sheets tools and write a local snapshot JSON before running `ingest_content_snapshot.py`
- Use the fallback workbook only when the live sheet has been exported or the user explicitly asks for workbook ingest
- Include legacy `Sheet1` and `v2` only when they still exist in the exported workbook and the user wants historical carryover
- Use the explicit `ID` column when present and store it as the queue identifier; fall back to the legacy `Proposal ID` column or source row position plus tab name when needed
- Skip completely empty rows
- Preserve blank review decisions as blank, not `Approved` or `Disapproved`
- Preserve `Review decision = MANUAL` exactly as stored
- Capture management fields including `Production status`, `Draft due`, `Review due`, `Scheduled date`, `Draft doc`, `Publish status`, `Manager notes`, `Published date`, and `Published URL`
- Treat `MANUAL` rows as normal content inventory rows with a different source marker, not as errors
- Do not fabricate publish dates, draft URLs, or LinkedIn post URNs

If a row already exists in the database, update the current-state fields and refresh `last_ingested_at`.

## LinkedIn Metrics Rules

Start with payload-file imports even if the user eventually wants direct API sync.

- Accept JSON payloads exported or collected from LinkedIn stats endpoints
- Match snapshots to content items by `linkedin_post_urn`, `ID`, legacy `proposal_id`, or `title`
- Append a new snapshot row instead of overwriting older metrics
- Record the import in `sync_runs`

Only use live LinkedIn API requests after confirming:

- valid access token
- the required LinkedIn product access
- the correct versioned headers

If any of those are missing, fall back to manual payload import and state that clearly.
Do not add API publishing behavior here; publishing remains manual.

## Analyst Outputs

When summarizing the database, answer practical questions such as:

- which categories get approved more often
- which planner angles are still unused
- which published items perform best by impressions, engagement, or reactions
- where review friction is concentrated
- which titles or briefs are repeatedly revised

Keep recommendations simple and operational. Do not overfit to one post or one snapshot.

## Final Checks

Before finishing a database task, verify:

1. The SQLite file exists and the schema is present.
2. Live-sheet or fallback-workbook ingests populated both tracked content and planner slots.
3. Metrics imports created snapshot rows instead of mutating history.
4. Summary outputs identify real patterns rather than guessing.
5. Any LinkedIn API claim is consistent with the current official access limitations in `references/linkedin-api.md`.
