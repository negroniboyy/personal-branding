---
name: pb-linkedin-title
description: Plan the next LinkedIn content candidates for the PersonalBrand system by reading the live TurboBaba planner document, the live sheet referenced by `PB_CONTENT.gsheet`, and the refreshed diary-memory outputs, then appending the next 5 title-and-brief rows to the live review tab and learning from Approved or Disapproved outcomes plus user title edits. Use when Codex needs to propose the next LinkedIn posts, keep the live planning sheet updated, or prepare approved rows for handoff to $pb-linkedin-drafts.
---

# pb_linkedin_title

## Overview

Use this skill to manage the LinkedIn planning layer for the PersonalBrand workflow.
Generate the next five LinkedIn proposals, write them into the active live review queue, optionally mirror them to a local backup workbook when needed, and update the skill's preference memory from user review behavior.
Use it through `$pb-linkedin-gm` for normal operations so the GM can keep Google Sheet state and approvals aligned across the pipeline.
For packaging help only, this skill may consult `$pb-linkedin-playbook` after the topic is already grounded in the planner, live sheet, brand docs, or diary memory.
Do not let `$pb-linkedin-playbook` choose the topic, own queue state, or replace this skill's planning responsibilities.

The default operating mode is now live Google Sheet mode.
Use the local `contents/CONTENT.xlsx` workbook only as a fallback backup or repair target when the live sheet is unavailable or the user explicitly asks for a local mirror.
Treat diary memory as the preferred personalization layer for choosing which grounded story, tension, or project thread to elevate.

## Read The Current System First

Read `references/live-assets.md` before doing any work.
Use it to understand which assets exist and which live tabs are active.

Use these tools when the live system is in scope:

- Google Docs tools to read the planner document
- Google Sheets tools to inspect and update the sheet referenced by `PB_CONTENT.gsheet`
- The local mirror script in this skill only when the user wants the same rows appended to `contents/CONTENT.xlsx` as a backup

Read these sources in order:

1. The live Google Doc `TurboBaba Content Planning`
2. The live Google Sheet referenced by `PB_CONTENT.gsheet`, especially tabs `Content List` and `Content Live`
3. `brandguide/memory_notion/profile.md`
4. `brandguide/memory_notion/recent.md` when recent diary context can sharpen the angle, timing, or anchor detail
5. Legacy tabs `v2` and `Sheet1` only when historical context is needed
6. The local fallback workbook `contents/CONTENT.xlsx` only when the live sheet is unavailable or the user explicitly wants a local backup checked
7. `brandguide/brandbook.md` and `brandguide/linkedin.md` when a title idea needs brand or channel confirmation
8. `references/learned-patterns.md` and `references/learning-state.json`
9. Optional `knowledge_base/` files only after the planner, live queue, and diary-memory outputs have already established a real topic or moment:
   - `knowledge_base/storyworth.md` for story-moment detection and brief shaping
   - `knowledge_base/title_patterns.json` for title packaging patterns
   - `knowledge_base/knowledge_registry.json` when you need the source-role metadata
   - `knowledge_base/*.summary.md` only when they help generate alternate packaging ideas without changing the brand voice

## Knowledge Base Role

Treat `knowledge_base/` as a packaging and story-shaping support layer, not as a truth layer.

- `brandguide/brandbook.md` and `brandguide/linkedin.md` remain the source of truth for voice, identity, guardrails, and what is off-limits.
- The planner doc, live sheet, and approved queue remain the source of truth for topic, timing, and lived experience.
- `brandguide/memory_notion/profile.md` is the preferred grounding layer for stable reality, recurring themes, and real project context.
- `brandguide/memory_notion/recent.md` is the preferred grounding layer for short-window recency and what has felt salient lately.
- `knowledge_base/` may suggest title shapes, story extraction techniques, or structural options only after the core idea is already grounded in repo material.
- `$pb-linkedin-playbook` may help compress an already-grounded idea into clearer angles or opening directions, but only as an optional support layer.
- Never let `knowledge_base/` decide the core topic, the emotional claim, or the professional framing by itself.
- Prefer abstract pattern transfer over copying wording from any external-style source.

## Default Goal

When the user asks for the next content ideas, do this by default:

1. Read the planner doc and extract the next strongest unused story blocks, tensions, and opening-scene angles.
2. Read the active live queue from `Content List` and the current planning tab from `Content Live`.
3. Read legacy review history only when it helps explain current user edits, approvals, or repeated disapprovals.
4. Generate exactly 5 new LinkedIn proposals.
5. Append them to the live `Content List` review queue.
6. Mirror them into the local workbook only when the user explicitly wants a backup.

This skill also supports a manual-seed refinement mode.
Use that mode when GM routes an existing live-sheet row whose `Review decision = MANUAL`.
In that case:

1. Read the existing row in `Content List`.
2. Treat its `Title` and `Content` as editable seed material, not final approved assets.
3. Refine the title and brief for that same row only.
4. Upgrade the row to review-ready by ensuring `Title`, `Content`, `Category`, `Channel`, `Planner Source`, and `Production status` are all populated.
5. Preserve the existing `ID`.
6. Do not generate a new five-row batch unless the user explicitly asks for it.

Each proposal row must contain:

- `Title`
- `Review decision` left blank
- `Content` as a short briefing, not a full draft
- `Category`
- `Channel` set to `LinkedIn`
- `ID`
- `Planner Source`
- `Production status` set to `Backlog`

## Proposal Rules

- Keep titles grounded, reflective, and specific.
- Prefer real tensions, workflow shifts, technical friction, or changes in thinking.
- Use the planner doc's narrative blocks and the current `Content Live` slots before inventing new directions.
- Use diary memory to check whether the proposed angle matches the user's actual projects, current concerns, and natural language.
- When a planner block is broad, look for the smallest concrete scene, misunderstanding, mistake, or shift inside it before naming the idea.
- Do not reuse a `Disapproved` title verbatim.
- Do not write the LinkedIn draft itself here unless the user explicitly asks.
- Do not overwrite existing review decisions or existing row text.
- Do not wipe due dates, draft doc paths, publish-tracking fields, or manager notes that already exist on live-sheet rows.

If you use `knowledge_base/` during proposal generation:

- Use `storyworth.md` to identify whether the idea contains a real turning point, a before/after shift, or a scene worth briefing.
- Use `title_patterns.json` only to generate alternate title shapes for an already-grounded idea.
- Rewrite any useful pattern back into calm, reflective LinkedIn language before returning it.
- Reject templates that sound like clickbait, challenge-bait, forced-choice engagement bait, direct-response marketing, or borrowed authority.
- If no real moment exists in the source material, do not manufacture one just to fit a title pattern.

For the `Content` briefing, write 2 to 4 sentences that cover:

- the core moment or tension
- the intended reflection angle
- any anchor detail that should show up in the later draft
- when diary memory offers a better real-world detail, the project, scene, or recent shift that makes the row feel lived-in rather than generic

When possible, make the briefing specific enough that the draft skill can identify:

- the scene or setting
- the tension or stakes
- the shift in thinking, behavior, or understanding

## Learning Loop

This skill improves by tracking what the user changes after proposals are written.

The learning loop should be based on the current live queue first.
Do not carry forward stale review outcomes from older legacy tabs unless the user explicitly asks to preserve them.

Count these as preference signals:

- a proposal marked `Approved`
- a proposal marked `Disapproved`
- a user-edited replacement title on a row with the same `ID`
- a user-edited briefing on a row with the same `ID`

Do not infer preferences from likes, views, or other publishing metrics here.

After each review cycle:

1. Export or read the reviewed rows from the active queue that include `ID`.
2. Run `scripts/reconcile_learning_state.py` to update `references/learning-state.json`.
3. Refresh `references/learned-patterns.md` from the script output.

Prefer repeated signals over one-off edits. Keep learned rules short and operational.

## Queue Write Protocol

Choose the queue based on the current active live tabs.

- Default active review queue: Google Sheet tab `Content List`
- Legacy history tabs: `v2` and `Sheet1`, read-only unless the user explicitly asks for cleanup

For either queue:

- Append new rows only.
- Preserve the existing live column order exactly as it appears now. The queue currently begins with `ID`, `Title`, `Content`, `Review decision`, `Category`, and `Channel`.
- If `ID` or `Planner Source` columns do not exist yet, add them without disturbing the live column order. Keep `ID` as the row identifier column.
- If the management columns exist, preserve them exactly and only fill the fields relevant to the new rows.
- In mixed-track runs, encode track ownership in `Category` using prefixes such as `TurboBaba / ...` or `Learning in public / ...`.
- Continue from the highest existing numeric `ID` when the sheet already uses numeric IDs. Use stable text IDs only if the active queue is already using them.
- Set `Planner Source` to a short planner anchor such as `Block 4`, `Content Live Week 3`, or `Bonus swap-in`. Never leave `Planner Source` blank on a generated or refined review row.
- Set `Production status` to `Backlog` for newly generated rows.

If the user wants a local backup after the Google Sheet write succeeds, run the local mirror script:

```powershell
python scripts/append_local_content_rows.py --workbook "<repo-root>\contents\CONTENT.xlsx" --sheet "Content List" --proposal-file "<json-file>"
```

Update `Content Live` only when the user wants the monthly sequence reflected there.

## Handoff To The Draft Skill

If the user asks to draft an approved idea, hand off to `$pb-linkedin-drafts` rather than drafting inside this skill by default.

Use only rows where:

- `Review decision` is `Approved`
- `Channel` is `LinkedIn`

GM may also route a `MANUAL` row back through this skill for title/brief refinement before the draft handoff.

Pass this minimum handoff context:

- id
- title
- content briefing
- category
- planner source
- diary-memory cues from `profile.md` or `recent.md` that clarify the user's reality, wording, or current priorities
- any edited title or briefing text from the sheet
- any story note that clarifies the concrete scene, turning point, or anchor detail
- manager notes when they clarify the direction of a `MANUAL` row

## Final Checks

Before finishing, verify:

1. Exactly 5 new proposal rows were generated unless the user asked for a different count.
2. No title duplicates an existing `Disapproved` title verbatim.
3. The rows were appended to the intended active live review queue, not written into historical tabs by mistake.
4. If a backup mirror was requested, the local workbook mirror was updated after the live sheet update.
5. The learning state was refreshed if reviewed rows with `ID` were available.
6. Any `knowledge_base/` pattern that survived was used only as packaging support and was rewritten back into PersonalBrand voice.
7. No proposal depends on invented scenes, exaggerated stakes, or imported creator-style phrasing.
8. Diary memory was used when available to make the title and briefing better aligned with real projects, recurring themes, or recent lived context.
9. New generated rows defaulted to `Production status = Backlog`.
10. No row handed back to GM for title approval is missing `Title`, `Content`, `Category`, `Channel`, `Planner Source`, or `Production status`.
11. Manual-seed refinement preserved the original live row `ID` and did not append unrelated new rows.
