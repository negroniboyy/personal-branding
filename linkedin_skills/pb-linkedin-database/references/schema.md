# Schema

The SQLite schema is LinkedIn-first but channel-capable.

## `content_items`

Current tracked content rows from the live Google Sheet or fallback workbook review queues.

Key fields:

- `source_system`
- `source_tab`
- `source_row`
- `channel`
- `title`
- `brief`
- `category`
- `review_decision`
- `production_status`
- `proposal_id`
  - stores the queue `ID` from the live sheet when present
  - also accepts legacy `Proposal ID` values from older sheets
- `planner_source`
- `draft_due`
- `review_due`
- `scheduled_date`
- `draft_doc`
- `linkedin_post_urn`
- `linkedin_author_urn`
- `publish_status`
- `published_date`
- `published_url`
- `manager_notes`
- `created_at`
- `updated_at`
- `last_ingested_at`

Unique key:

- `(source_system, source_tab, source_row)`

## `planner_slots`

Narrative and slotting rows such as `Content Live`.

Key fields:

- `source_system`
- `source_tab`
- `source_row`
- `slot_label`
- `title`
- `angle`
- `narrative_spine`
- `source_fit`
- `core_tension`
- `opening_scene`
- `notes`
- `draft_due`
- `review_due`
- `scheduled_date`
- `production_status`
- `created_at`
- `updated_at`
- `last_ingested_at`

Unique key:

- `(source_system, source_tab, source_row)`

## `review_events`

Optional history of approval or disapproval changes and editorial adjustments.

Key fields:

- `content_item_id`
- `review_decision`
- `title_at_review`
- `brief_at_review`
- `reviewed_at`
- `source`
- `notes`

## `performance_snapshots`

Time-series performance data for published LinkedIn posts.

Key fields:

- `content_item_id`
- `snapshot_at`
- `source`
- `impressions`
- `views`
- `clicks`
- `reactions`
- `comments`
- `reposts`
- `engagement_rate`
- `raw_payload_json`

## `sync_runs`

Audit trail of ingest and import activity.

Key fields:

- `source`
- `action`
- `status`
- `started_at`
- `finished_at`
- `details_json`
