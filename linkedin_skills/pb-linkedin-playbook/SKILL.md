---
name: pb-linkedin-playbook
description: Shape grounded PersonalBrand LinkedIn ideas into stronger angles, opening lines, briefs, and draft-ready outlines. Use when Codex needs packaging help for one real source moment, diary note, work incident, planner block, or approved brief without taking over workflow orchestration, scheduling, approvals, or analytics.
---

# pb_linkedin_playbook

## Overview

Use this skill as a LinkedIn-first packaging and shaping playbook for the PersonalBrand project.
It helps turn real source material into clearer LinkedIn angles, opening lines, short briefs, and draft-ready structure.
It is not a workflow owner.

Keep these responsibilities where they already belong:

- `$pb-linkedin-gm` owns orchestration, approvals, and production-state coordination.
- `$pb-linkedin-title` owns live planning rows, title generation, and queue updates.
- `$pb-linkedin-drafts` owns full draft writing and local `.docx` output.
- `$pb-linkedin-database` owns analytics, ingest, and performance review.

If the user asks for scheduling, analytics, content calendars, or broad social-media strategy, do not pretend this skill handles that.
Redirect to the PB skill that owns that layer, or state that the request is out of scope.

## Source Check First

Before asking the user for more context, read the project sources that already define the brand and channel.

Read in this order:

1. `brandguide/brandbook.md`
2. `brandguide/linkedin.md`
3. `brandguide/memory_notion/profile.md`
4. `brandguide/memory_notion/recent.md` when recency matters
5. Live planning artifacts only when needed to identify the active topic or row:
   - `Content List`
   - `Content Live`
   - approved brief rows or planner blocks routed in by the user or GM

Use those sources to ground:

- what is actually true about the user
- which LinkedIn pillars are already canonical
- whether the idea sounds lived-in or generic
- whether the task is packaging help versus planning or drafting work

If the source material still does not contain a real moment, tension, work situation, mistake, or shift in thinking, stop and ask for that missing context instead of manufacturing content.

## Scope And Non-Goals

This skill is for:

- angle generation from one grounded source moment
- opening-line shaping
- short brief creation
- draft-ready outline creation
- repackaging a diary note, work incident, planner block, or approved brief into LinkedIn-ready form

This skill is not for:

- managing the live Google Sheet or workbook
- asking for execution approvals on behalf of GM
- scheduling posts
- publishing posts
- analyzing performance metrics
- daily engagement routines
- broad multi-platform strategy
- viral-content reverse engineering

## Canonical LinkedIn Pillars

Use the existing PB LinkedIn pillars from `brandguide/linkedin.md`.
Do not invent a new pillar system unless the user explicitly asks to revise the brand strategy.

Default pillar set:

- Learning in public
- Real work experience
- Career direction and standards
- Building and projects
- Systems thinking
- Reflection posts

Use these pillars as classification and shaping aids only.
They help choose the right angle for a real source moment; they do not replace the source moment itself.

## Task Classifier

Classify the request before producing output.

- `Angle generation`
  Turn one grounded source moment into 3 to 5 possible LinkedIn directions.
- `Hook shaping`
  Produce 2 to 4 opening-line options for an already-grounded angle or draft.
- `Brief creation`
  Turn a real source moment into a short post brief that title or draft work can build from.
- `Source repackaging`
  Transform one input into LinkedIn-ready material:
  - diary note -> LinkedIn angle
  - work incident -> reflection post
  - planner block -> title/brief direction
  - approved brief -> draft-ready outline

If the task actually belongs to planning, workflow coordination, or full draft creation, hand off conceptually to the PB skill that owns that layer instead of stretching this skill beyond scope.

## Opening-Line Patterns

When shaping openings, stay reflective, specific, and PB-native.
Do not use contrarian theater, engagement bait, or creator-style hot takes.

Preferred opening-line patterns:

- `Observation`
  Start from something the user noticed after real work, friction, or reflection.
- `Story`
  Start from a concrete small moment, not an inflated narrative.
- `Value`
  Start from a practical realization without sounding like a guru.
- `Shift`
  Start from what changed in how the user thinks, works, or learns.

Good openings should:

- sound like a real thought after real experience
- make the reader curious without sounding engineered
- stay compatible with the final draft's actual content
- avoid hype, certainty theater, or borrowed authority

Bad openings include:

- bold contrarian claims for their own sake
- challenge bait
- forced-comment prompts
- viral-style formulas that sound imported from another creator

## Source-To-Post Transforms

Use these PB-native transforms instead of generic multi-platform repurposing systems:

- `Diary note -> LinkedIn angle`
  Find the work-facing observation, tension, or change in thinking.
- `Work incident -> reflection post`
  Isolate the smallest real scene, the friction, and what changed afterward.
- `Planner block -> title/brief`
  Extract the most concrete scene or misunderstanding from the broader theme.
- `Approved brief -> draft-ready outline`
  Clarify opening, core movement, and ending direction without writing the full post unless asked.

Each transform should preserve:

- the real source event
- the user's actual level of certainty
- the calm, reflective PB tone

## Grounded Recovery Checklist

When the user is stuck, look for these sources before inventing new topics:

- a recent confusion that became partial understanding
- a small troubleshooting moment
- project friction or a blocked workflow
- a career-direction question that is still unresolved
- a recent change in standards, process, or mindset

Do not solve creative blockage by introducing trend-driven formats, other platforms, or empty topic buckets.

## Output Shapes

Default outputs should stay short and operational.

### Angle generation

Return:

- 3 to 5 angle options
- 1 sentence each on what makes the angle real

### Hook shaping

Return:

- 2 to 4 opening-line options

### Brief creation

Return:

- one short brief covering:
  - source moment
  - reflection angle
  - one anchor detail
  - ending direction

### Draft-ready outline

Return:

- opening direction
- middle movement
- ending direction

Do not add content-calendar advice, scheduling advice, performance advice, or multi-platform adaptation unless the user explicitly asks to expand scope.

## Guardrails

- Ground every output in repo material or user-provided lived context.
- Keep the tone honest, reflective, calm, and specific.
- Prefer partial understanding over borrowed certainty.
- Ask for missing lived context when the source is too abstract.
- Reject packaging that sounds like thought-leader performance.
- Reject prompts to optimize for virality, follower growth, or engagement bait when that would distort the brand.
- Do not treat LinkedIn as a generic business-content channel; treat it as the PB work-and-learning channel defined in the brand docs.

## Optional Use By Other PB Skills

This skill may be consulted by other PB LinkedIn skills only as a narrow support layer.

- `$pb-linkedin-title` may consult it for packaging help after the topic is already grounded.
- `$pb-linkedin-drafts` may consult it for opening-line or structure refinement after the source moment is already grounded.
- `$pb-linkedin-gm` may include it as an optional packaging support handoff when the user explicitly wants help shaping grounded ideas before or during title or draft work.

## Final Check

Before finishing, verify:

1. The output stayed LinkedIn-first.
2. The output stayed grounded in real PB source material.
3. No multi-platform, engagement, scheduling, or analytics advice leaked back in.
4. No opening line sounds like clickbait, hot-take theater, or forced interaction bait.
5. The response improved packaging without stealing workflow ownership from the existing PB skills.
