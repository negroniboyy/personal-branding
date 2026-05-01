# pb-linkedin-gm orchestration map

## Managed scope

This skill coordinates installed skills whose names contain `pb-linkedin`.
Current known skills:

- `pb-content-strategy`
- `pb-diary-memory-sync`
- `pb-linkedin-performance`
- `pb-linkedin-title`
- `pb-linkedin-drafts`
- `pb-linkedin-database`

## Role split

- `pb-linkedin-gm`: mandatory gateway for normal LinkedIn work, inspect the live Google Sheet pipeline, identify approvals, sequence the run, and own live-sheet state transitions
- `pb-content-strategy`: decide the next PersonalBrand content directions when the system needs strategy recalibration before more title generation
- `pb-diary-memory-sync`: refresh the local diary-memory cache so LinkedIn planning and drafting can use current profile and recent lived context
- `pb-linkedin-performance`: parse LinkedIn analytics exports, import matched snapshots into the local DB, and produce brand-safe review feedback
- `pb-linkedin-title`: generate LinkedIn proposal rows or refine a `MANUAL` seed row while keeping the active Google Sheet current
- `pb-linkedin-drafts`: write or revise LinkedIn post drafts from `Approved` or GM-routed `MANUAL` rows
- `pb-linkedin-database`: update the SQLite tracking layer and summarize inventory or performance patterns

## Weekly orchestration default

Use a 7-day window by default.
Treat the current date in the user's timezone as day 0.
Refresh diary memory first when it is stale or missing, then inspect the live Google Sheet referenced by `PB_CONTENT.gsheet`, especially `Content List` and `Content Live`, and map live rows to the specialist skills.

Typical mapping:

- memory files are missing, stale, or likely outdated relative to recent diary work -> `pb-diary-memory-sync`
- review queue is thin, the monthly arc needs recalibration, the content mix is drifting, or the user explicitly asks for topic strategy -> `pb-content-strategy`
- a recent LinkedIn analytics export exists and the user wants a postmortem or batch review -> `pb-linkedin-performance`
- generated review queue is thin but strategy is already approved, a `MANUAL` seed row needs title refinement, or a row fails the hygiene gate -> `pb-linkedin-title`
- review-ready rows should be split into TurboBaba and learning-in-public queues before approval
- `Approved` or `MANUAL` row in `Backlog` or `Drafting` with no usable draft doc -> `pb-linkedin-drafts`
- review/inventory/performance sync needed -> `pb-linkedin-database`

## Approval checklist

Call out these approvals explicitly:

- execution window approval if the user did not set the horizon
- diary-memory refresh approval when the run will pull Notion and rewrite local memory files
- strategy-direction approval before converting new directions into queue rows
- analytics-import approval when the run will use a recent LinkedIn export for performance review
- title approval before drafting
- draft approval before final downstream use
- data sync approval when the run will mutate the tracking layer
- plan approval before coordinated execution

## Live-sheet usage

Prefer Google Sheets tools for normal operations.
Use this live-sheet helper flow first:

```powershell
Use Google Sheets tools to read `Content List!A:P` and `Content Live!A:M`
Write <repo-root>\tmp\pb_linkedin_live_sheet_snapshot.json
python <skill-dir>\scripts\review_content_snapshot.py --snapshot <repo-root>\tmp\pb_linkedin_live_sheet_snapshot.json --days 7 --start-date <YYYY-MM-DD>
```

Fallback only:

```powershell
python <skill-dir>\scripts\review_content_workbook.py --workbook <repo-root>\contents\CONTENT.xlsx --days 7 --start-date <YYYY-MM-DD>
```

This helper flow returns both all upcoming due items and the subsets for:

- generated review queue that passes the row-hygiene gate
- refinement-required rows missing control-tower fields
- TurboBaba narrative review queue
- learning-in-public review queue
- manual seed queue
- drafting queue
- in-progress drafting queue
- ready queue
- done queue

If deeper inspection is needed, use the live sheet directly and filter by:

- due date inside the current 7-day window
- review decision
- production status, draft doc, scheduled date, and published tracking fields

If live-sheet access fails, use the local workbook helper and say that the review is fallback-based.
