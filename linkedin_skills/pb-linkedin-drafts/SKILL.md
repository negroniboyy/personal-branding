---
name: pb-linkedin-drafts
description: Generate grounded LinkedIn post drafts that match the PersonalBrand voice by reading the canonical brand guide, LinkedIn channel guidance, refreshed diary-memory outputs, and current planning materials. Use when Codex needs to turn markdown, DOCX, or spreadsheet planning inputs into LinkedIn draft variants, revise an existing LinkedIn draft to align with the brand, or check whether a LinkedIn draft stays honest, reflective, clear, and non-performative without inventing experience or authority.
---

# pb_linkedin_drafts

## Overview

Use this skill to draft or revise LinkedIn posts for the PersonalBrand project.
Build from repo source material first, then write copy that sounds lived-in, reflective, and clear rather than polished, motivational, or expert-posting.
For each newly created draft, also write a local `.docx` file so the user can edit it manually outside the chat.
Use this skill through `$pb-linkedin-gm` for normal operations so live Google Sheet status and approvals stay aligned across the pipeline.
Treat diary memory as the preferred bridge between abstract planning rows and the user's real voice, projects, and recent lived context.
For packaging help only, this skill may consult `$pb-linkedin-playbook` for opening-line or outline refinement after the source moment is already grounded.
Do not let `$pb-linkedin-playbook` override source precedence, lived-context checks, or voice authority.

## Current Style Signals

Use the user's reviewed draft edits as the strongest drafting preference signal.

- Prefer one grounded draft, not a bundle of alternate versions.
- Prefer direct work context early when it helps the post land: `one day at work`, `my personal app`, `my personal project`.
- Prefer simple reflective phrasing over polished contrast formulas.
- Let the post sound like a real note after work, not a packaged content asset.
- Keep reflections concrete and plain. Do not force a slogan-like ending.
- Short inserted observations are fine when they sound natural and personal.
- Avoid the pattern `feels less like ... more like ...`.
- Avoid `feels like ...` framing when a more direct sentence is available.

## Gather Sources

Read source material in this order.

1. Read `brandguide/brandbook.md` first for global voice, audience, and guardrails.
2. Read `brandguide/linkedin.md` second for LinkedIn-specific pillars, angles, and recurring formats.
3. Read `brandguide/memory_notion/profile.md` third for the stable reality, recurring themes, and language that should shape the draft.
4. Read `brandguide/memory_notion/recent.md` when recent diary context can sharpen the scene, timing, or reflection.
5. Read planning material next:
   - `brandguide/*.docx` for narrative or content-planning documents
   - the live Google Sheet referenced by `PB_CONTENT.gsheet`, especially `Content List` and `Content Live`, for content-plan status and approval decisions
   - `contents/*.xlsx` only when the local workbook fallback needs to be inspected
   - `contents/*.docx` and `Posts/*.docx` for prior draft examples
6. Read `templates/gpts/draft-writer.md` when you need the output pattern.
7. Read `templates/google/post-brief-template.md` or `templates/google/monthly-strategy-brief.md` when the user is shaping a brief rather than requesting a direct draft.
8. Read optional `knowledge_base/` files only after the brand docs, diary-memory outputs, and planning sources:
   - `knowledge_base/storyworth.md` for story extraction, scene clarity, and endings
   - `knowledge_base/knowledge_registry.json` when you need source-role metadata
   - `knowledge_base/script_templates.json` only for hidden structural scaffolding
   - `knowledge_base/title_patterns.json` only when checking hook shape, never as a direct copy source
   - selected `knowledge_base/*.summary.md` files only when you need alternate packaging ideas, not borrowed voice

If local DOCX or XLSX inputs are involved, prefer the helper script instead of manually unpacking files:

```powershell
python scripts/collect_linkedin_sources.py --root <repo-root>
```

When saving a generated draft into a local editable document, use:

```powershell
python scripts/write_linkedin_draft_doc.py --json-file "<json-file>" --output-dir "<repo-root>/Posts"
```

Read `references/source-materials.md` when you need the repo-specific file map and current working assumptions.

## Source Precedence

Treat the brand docs as stronger authority than planning docs or existing drafts.

- Use `brandguide/brandbook.md` as the canonical identity and guardrail source.
- Use `brandguide/linkedin.md` as the channel-specific drafting source.
- Use `brandguide/memory_notion/profile.md` as the default lived-context anchor.
- Use `brandguide/memory_notion/recent.md` as the short-window lived-context anchor when recency matters.
- Use planning docs to choose topic, source experience, and timing.
- Use existing drafts only as examples of prior direction, not as rules.
- Use `knowledge_base/` only as a downstream support layer for structure, pacing, and story shaping.
- Use `$pb-linkedin-playbook` only as an optional downstream support layer for opening-line and outline refinement.

If a planning row or draft conflicts with the brand docs, follow the brand docs.
If a `knowledge_base/` pattern conflicts with the brand docs or the lived experience in the source material, discard the pattern.

## Knowledge Base Role

Treat `knowledge_base/` as a storycraft and packaging support layer, not as a source of identity.

- `storyworth.md` is the preferred storytelling reference because it helps identify scenes, shifts, and endings without forcing a thought-leader voice.
- `script_templates.json` may help you test structure privately, but the final draft should read like a LinkedIn post, not a swipe-file template.
- Other summaries may help with hook compression, pacing, or framing experiments, but they must never define the final voice.
- `$pb-linkedin-playbook` may help refine packaging, but it must never replace the draft skill's judgment about voice, specificity, and source truth.
- Never import domain language, sales framing, CTA style, or creator persona from `knowledge_base/` just because the structure seems effective.
- Rewrite every borrowed pattern until it sounds like PersonalBrand again.

## Choose The Task

Classify the request before drafting.

- For a new draft, extract the topic, real source moment, and intended angle from the plan.
- Use diary memory to pressure-test whether the source moment sounds real, current, and natural for this user.
- For a revision, identify which parts of the current draft sound overstated, generic, preachy, or detached from lived experience.
- For a voice audit, review the draft against the checklist in this skill and explain the specific gaps before rewriting.

If the material does not contain a real observation, work moment, project milestone, mistake, or shift in thinking, stop and ask for that missing context instead of drafting generic advice.

If `storyworth.md` is in use, identify these before drafting:

- the concrete scene
- the tension or stakes
- the five-second moment or turning point
- the old assumption or default state
- the meaning that follows from the moment without turning it into a lecture

For new-draft requests, GM may route two row types into this skill:

- generated rows with `Review decision = Approved`
- user-seeded rows with `Review decision = MANUAL`

For `MANUAL` rows:

- use the live-sheet row title, content, category, planner source, and manager notes as the main brief
- skip the TurboBaba planner dependency unless the row explicitly points back to it
- treat the title as editable seed text unless GM has already fixed the direction upstream

## Drafting Rules

- Anchor every post in a real experience, observation, or project moment.
- Write with confidence in standards and humility in voice.
- Prefer process, friction, and partial understanding over polished conclusions.
- Keep the tone calm, honest, reflective, and non-performative.
- Keep the language simple and specific.
- Prefer diary-grounded details, phrasing, and project references over generic summary language when the memory outputs support them.
- Let progress appear inside the story rather than announcing growth as a headline.
- Use storytelling structure to reveal meaning more clearly, not to dramatize ordinary events.
- Prefer one concrete detail or scene over broad abstraction when a story moment is available.
- Use pacing that moves through cause and consequence rather than list-like recap.
- Let the ending land on meaning or an open reflection, not a neat motivational wrap-up.
- Default to one complete draft unless the user explicitly asks for options.
- Only generate alternate openings or CTA variants when the user explicitly asks for them.

Do not:

- invent expertise, achievements, certainty, or lessons that are not in the source material
- turn the post into motivational advice or coaching
- imitate thought-leader formatting, empty frameworks, or borrowed authority
- present TurboBaba as a polished startup story when the source material frames it as a personal systems project
- use disapproved content-plan items unless the user explicitly asks to salvage or rewrite them
- import a hook, CTA, or creator voice from `knowledge_base/` without rewriting it into PersonalBrand language
- exaggerate stakes, emotion, or conflict just to make the story feel more dramatic
- invent a scene because a template expects one
- use engagement bait, forced questions, or manipulative CTA wording just to farm comments
- use `feels less like ... more like ...` or similar packaged contrast phrasing
- add extra metadata or supporting sections to the draft doc unless the user explicitly asks for them

## Intro And CTA Options

When the user asks for packaging help, you may also produce:

- `Punchy intro options`
- `LinkedIn-native CTA options`

Treat these as optional add-ons, not mandatory output.

Punchy intro options should:

- be short, direct, and specific
- feel like a real observation, tension, or shift
- stay grounded in the actual post content
- avoid hype, startup theater, and empty “lesson” framing

LinkedIn-native CTA options should:

- feel natural at the end of a reflective post
- invite conversation, perspective, or connection without pressure
- match the post type:
  - reflective post -> soft question or no CTA
  - learning/building post -> perspective-seeking question
  - career-direction post -> connection or outreach line
- avoid low-signal closers like `thoughts?`, `agree?`, or `anyone else?`

Default to 2 to 4 options when the user asks for intros or CTAs.
Keep them short enough that they can be swapped into the draft quickly.

## Story Shaping With Storyworth

When the source material includes a real moment, you may use `knowledge_base/storyworth.md` to improve narrative shape.

- Find the smallest moment that actually changed something.
- Treat that shift as the center of the post.
- Build the opening from the earlier state, confusion, or assumption.
- Use only enough scene detail to let the reader picture what was happening.
- Translate the moment into professional meaning without turning it into generic advice.
- If the post works better as a quiet reflection than as a full story, keep it quiet.

Useful Storyworthy-derived checks:

1. What is the actual moment here?
2. What changed in that moment?
3. What was true before the change?
4. Which one detail makes the scene feel real?
5. Does the ending stay honest and slightly open rather than overly resolved?

## Draft Output

Default to returning only the main LinkedIn draft text unless the user explicitly asks for more structure.

- Do not include `Source basis`, metadata fields, alternate angles, or tradeoff notes by default.
- Do not preface the draft with labels when the user only wants the copy itself.
- When revising a draft, keep any explanation short and only include it when the user asked for feedback or comparison.
- If the user asks for intro options or CTA options, return them after the main draft in short clearly separated sections.

Default shape:

```markdown
<main LinkedIn post>
```

Optional expanded shape when requested:

```markdown
<main LinkedIn post>

Punchy intro options:
- <option>
- <option>

LinkedIn-native CTA options:
- <option>
- <option>
```

## Draft File Output

For each newly created LinkedIn draft, also create or update a local `.docx` file in `Posts/`.

- Build a JSON payload that includes:
  - `post_id`
  - `primary_draft`
-  `title` may be included for filename generation, but it should not be rendered into the document body by default.
- Only include extra metadata fields when the user explicitly wants them preserved in the document.
- Use `scripts/write_linkedin_draft_doc.py` to write the file.
- Default filename pattern:
  - `Posts/LinkedIn Draft - <post_id> - <slug>.docx`
- If a draft for the same `post_id` already exists, overwrite it unless the user explicitly asks for versioned copies.
- Return the created file path separately from the draft text so the user can open and edit it manually.
- By default the `.docx` body should contain only:
  - `ID: <post_id>`
  - the main draft text
- Do not include `Source basis`, category, planner source, created timestamp, alternate angle, or tradeoff note in the document unless the user explicitly asks.

After the draft file is written, GM should update the live Google Sheet row to:

- `Production status = Ready`
- `Draft doc = <created docx path>`

When GM first routes a row into drafting, it should set `Production status = Drafting`.
Draft creation should never set publish state automatically.

## Final Check

Before finishing, verify each draft against these questions.

1. Does this sound like a real observation instead of a manufactured performance?
2. Does this stay grounded in lived experience rather than generic advice?
3. Does this keep humility in voice without sounding weak or vague?
4. Would this still feel right if engagement were low?
5. Is the wording clear and reflective without sounding like a motivational post?
6. Did diary memory help improve specificity, tone, or project realism without forcing details that are not actually supported?
7. If `knowledge_base/` was used, did it improve structure without leaking foreign voice, hype, or sales framing into the draft?
8. If `storyworth.md` was used, is the story anchored in a real moment rather than a dramatized reconstruction?
9. Was the `.docx` draft file written to `Posts/`, or updated there, for manual editing?
10. If the source row came from `MANUAL`, did the draft stay independent from TurboBaba-specific framing unless the row explicitly asked for it?

If any answer is no, rewrite before returning the draft.
