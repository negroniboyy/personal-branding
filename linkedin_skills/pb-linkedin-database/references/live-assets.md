# Live Assets

Use this file for the current LinkedIn-first PersonalBrand content data workflow.

## Live Sources

- Repo root: `/Users/maxkiyuna/Library/CloudStorage/OneDrive-MCPAssetManagementCoLtd/Documents/Taishi Lab/VibeCode/PB`
- Repo pointer: `PB_CONTENT.gsheet`
- Repo pointer: `PB_CONTENT.gsheet`
- Live Google Sheet: `https://docs.google.com/spreadsheets/d/1-EUsJ_ITuadeaNcSWGoSbYDpCm6UsOFRGQF4iUVWLZk`
- Active review queue: `Content List`
- Planning tab: `Content Live`
- Workbook fallback mirror: `contents/CONTENT.xlsx`
- Suggested snapshot path: `tmp/pb_linkedin_live_sheet_snapshot.json`
- Brand guide: `brandguide/brandbook.md`
- LinkedIn guide: `brandguide/linkedin.md`
- Planner doc mirror: `brandguide/TurboBaba Content Planning.docx`

## Current Related Skills

- `$pb-linkedin-title`
  - plans and updates the content review queue
- `$pb-linkedin-drafts`
  - writes draft copy for approved LinkedIn ideas

## Suggested Default Database Path

- `data/pb_linkedin_content.sqlite3` inside the repo when the user wants project-local storage
- or any user-specified SQLite path

## Current Repo Reality

- The repo does not yet contain a SQLite database module.
- The repo does not yet contain LinkedIn API credentials.
- The current `.env` only contains Plane settings.

That means this skill should default to database initialization, live-sheet-aware ingest planning, fallback workbook ingestion when needed, and manual metrics imports first.
