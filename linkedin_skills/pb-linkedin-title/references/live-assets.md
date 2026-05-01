# Live Assets

Use this file for the current PersonalBrand LinkedIn planning system.

## Operational Source Of Truth

This skill currently supports two operating modes:

- Live-sheet mode: the Google Sheet is the active source of truth
- Fallback local-workbook mode: the local workbook is used only when the live sheet is unavailable

The current system is now operating in live-sheet mode. Prefer the Google Sheet unless the user explicitly says to fall back to the local workbook.

### Planner doc

- Title: `TurboBaba Content Planning`
- URL: `https://docs.google.com/document/d/1wiqa0J_I0EHOQbIhKNOW7w8vRGa3tn6UvY8Pd5lWBQ4`
- Type: Google Doc
- Role: main planning narrative and story-block source

### Content sheet

- Repo pointer: `PB_CONTENT.gsheet`
- URL: `https://docs.google.com/spreadsheets/d/1-EUsJ_ITuadeaNcSWGoSbYDpCm6UsOFRGQF4iUVWLZk`
- Type: Google Sheet
- Role: main project manager and post manager for the live LinkedIn workflow

## Important Tabs

### `Content List`

- Active live review queue in Google Sheets
- Current source-of-truth tab for the planning system
- Existing columns currently start with:
  - `ID`
  - `Title`
  - `Content`
  - `Review decision`
  - `Category`
  - `Channel`
- Add support columns at the end when needed:
  - `Planner Source`

### `v2`

- Legacy append-only review queue for old LinkedIn proposals
- Existing columns start with:
  - `Title`
  - `Review decision`
  - `Content`
  - `Category`
  - `Channel`
- Legacy support columns may include:
  - `Proposal ID`
  - `Planner Source`

### `Sheet1`

- Historical or older review queue
- Read only when the user wants legacy approval and rejection patterns preserved
- Do not append new proposal rows here by default

### `Content Live`

- Narrative slotting and unused angle source
- Active live planning tab in Google Sheets
- Use blank title rows and the bonus row as planning inputs
- Do not write review-queue rows here by default

## Local Fallback

- Repo root: `/Users/maxkiyuna/Library/CloudStorage/OneDrive-MCPAssetManagementCoLtd/Documents/Taishi Lab/VibeCode/PB`
- Local workbook fallback: `contents/CONTENT.xlsx`
- Use only if the live Google Sheet is unavailable or the user explicitly asks for a local backup workflow

## Companion Skill

- Skill ID: `$pb-linkedin-drafts`
- Installed path: `/Users/maxkiyuna/.codex/skills/pb-linkedin-drafts`
- Role: turn an approved title + briefing into LinkedIn draft variants

## Current Working Assumptions

- The planner doc remains the strongest planning source.
- The live Google Sheet is now the active source of truth.
- The live Google Sheet is the main project manager and post manager across the `pb-linkedin-*` skills.
- Legacy tabs remain for reference, but the active live tabs are `Content List` and `Content Live`.
- `Approved` and `Disapproved` states are the only review signals that change planning behavior.
- In a fresh-start run, do not import old disapproval history unless the user asks for it.
- The current live queue already contains starter rows with `ID` values, so new proposals should continue from the highest existing live `ID`.
- The planner doc's next-priority blocks are `Block 4`, `Block 6`, and `Block 8`, but the skill may also use the open `Content Live` slots to complete a batch of five proposals.
