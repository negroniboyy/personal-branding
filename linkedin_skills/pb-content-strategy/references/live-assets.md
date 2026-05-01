# Live Assets

Use this file for the current PersonalBrand content-strategy workflow.

## Operational Role

This skill is strategy-first and read-first.
It should inspect current PersonalBrand context and recommend the next content directions.
It should not be the primary owner of queue writes, drafting, or database ingest.

## Primary Sources

### Core repo context

- `md/context_memory.md`
- `brandguide/brandbook.md`
- `brandguide/linkedin.md`
- `brandguide/memory_notion/profile.md`
- `brandguide/memory_notion/recent.md`

### Live control tower

- Repo pointer: `PB_CONTENT.gsheet`
- URL: `https://docs.google.com/spreadsheets/d/1-EUsJ_ITuadeaNcSWGoSbYDpCm6UsOFRGQF4iUVWLZk`
- Active tabs:
  - `Content List`
  - `Content Live`

Use the live sheet to judge:

- what is already approved, ready, or missing
- whether the queue is too thin or too repetitive
- whether the month arc needs recalibration
- whether there is drift between planned themes and current lived context

## Companion Skills

- `$pb-linkedin-gm`
  - owns weekly orchestration, approvals, and skill sequencing
- `$pb-linkedin-title`
  - turns approved strategy directions into live-sheet proposal rows
- `$pb-linkedin-drafts`
  - turns approved or manual rows into LinkedIn drafts
- `$pb-linkedin-database`
  - summarizes inventory and performance patterns when analysis is needed

## Working Assumptions

- LinkedIn is the first target channel for this skill.
- Instagram may be added later, but this skill should not optimize around Instagram execution yet.
- Diary memory and live-sheet state are more trustworthy than generic internet content strategy patterns.
- `knowledge_base/` can help with language or pattern support, but it should not override PersonalBrand reality.
