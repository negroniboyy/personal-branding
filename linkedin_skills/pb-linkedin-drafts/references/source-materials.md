# Source Materials

Use this file when you need the current repo-specific file map for the PersonalBrand LinkedIn drafting workflow.

## Expected Repo Layout

Look for a repo root that contains these folders:

- `brandguide/`
- `contents/`
- `Posts/`
- `templates/`

Current known repo root:

`/Users/maxkiyuna/Library/CloudStorage/OneDrive-MCPAssetManagementCoLtd/Documents/Taishi Lab/VibeCode/PB`

## Primary Files

Read these first when they exist:

- `brandguide/brandbook.md`
- `brandguide/linkedin.md`
- `brandguide/TurboBaba Content Planning.docx`
- Repo pointer: `PB_CONTENT.gsheet`
- Google Sheet: `https://docs.google.com/spreadsheets/d/1-EUsJ_ITuadeaNcSWGoSbYDpCm6UsOFRGQF4iUVWLZk`
- `contents/CONTENT.xlsx`
- `contents/TurboBaba LinkedIn Drafts - Posts 1 to 3.docx`
- `Posts/LinkedIn Draft Progress 01.docx`
- `templates/gpts/draft-writer.md`
- `templates/google/post-brief-template.md`
- `templates/google/monthly-strategy-brief.md`

## Working Assumptions

- `brandguide/brandbook.md` is the canonical brand source.
- `brandguide/linkedin.md` is the LinkedIn channel source.
- The sheet referenced by `PB_CONTENT.gsheet` is the main project manager and post manager.
- `contents/CONTENT.xlsx` is a local fallback copy, not the primary control tower.
- Treat rows marked `Disapproved` as off-limits unless the user explicitly asks to rework them.
- Existing `.docx` drafts are useful examples but do not override the brand docs.
- Newly generated LinkedIn drafts should be written to individual `.docx` files under `Posts/`.

## Repo-Specific Notes

### TurboBaba framing

The TurboBaba planning document frames the project as:

- a personal systems project
- a learning-in-public storyline
- proof of thinking through trial, error, and restructuring

Do not reframe it as a polished startup success story.

### Draft pattern

The GPT draft template expects:

- one primary draft
- one alternate angle
- one short tradeoff note
- one local `.docx` output file for manual editing

### Spreadsheet preview

The live Google Sheet currently uses these active tabs:

- `Content List`
- `Content Live`

Legacy tabs may still exist for reference:

- `Sheet1`
- `v2`
- older exported monthly-arc tabs

The active review tab includes columns such as:

- `ID`
- `Title`
- `Review decision`
- `Content`
- `Category`
- `Channel`

Prefer rows where:

- `Channel` is `LinkedIn`
- `Review decision` is `Approved`
