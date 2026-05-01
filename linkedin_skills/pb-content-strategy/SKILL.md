---
name: pb-content-strategy
description: Decide what PersonalBrand content themes, angles, and post directions to pursue next. Use when Codex needs to figure out what to post next on LinkedIn, recalibrate the next 2-4 weeks of PersonalBrand content, identify gaps in the live PB content sheet, or prepare a strategy brief that upstreams into `pb-linkedin-gm` and `pb-linkedin-title` without writing final queue rows or full drafts.
---

# pb_content_strategy

## Overview

Use this skill as the upstream strategy layer for the PersonalBrand content system.
Its job is to decide what the next content directions should be, not to write the final LinkedIn draft and not to append final proposal rows directly into the live sheet.

This skill is LinkedIn-first for now.
Keep the structure reusable for future Instagram strategy work, but do not optimize this first version around Instagram execution.

Read `references/live-assets.md` before acting.

## Role In The PB Stack

This skill sits before execution-focused content skills.

- `pb-content-strategy`: choose the next themes, angles, and post directions
- `pb-linkedin-gm`: coordinate approvals, weekly review, and skill sequencing
- `pb-linkedin-title`: convert approved strategy directions into row-ready LinkedIn proposals
- `pb-linkedin-drafts`: turn approved rows into draft posts
- `pb-linkedin-database`: analyze tracking and performance patterns when needed

Do not duplicate the downstream work of `pb-linkedin-title` or `pb-linkedin-drafts`.
If the user asks for rows or drafts, hand off to the appropriate skill after strategy is approved.

## When To Use

Use this skill when:

- the user asks what they should post next on LinkedIn
- the next 2-4 weeks of PB content need recalibration
- the live `Content List` feels repetitive, thin, or misaligned
- the current `Content Live` tab needs better narrative direction
- `pb-linkedin-gm` needs a strategy brief before routing work to `pb-linkedin-title`

Do not use this skill for:

- writing the final LinkedIn post text
- updating row state in the live sheet as the primary task
- SEO-first blog planning
- generic company content marketing advice

## Read Order

Read these sources in order before proposing strategy:

1. `md/context_memory.md`
2. `brandguide/brandbook.md`
3. `brandguide/linkedin.md`
4. `brandguide/memory_notion/profile.md`
5. `brandguide/memory_notion/recent.md` when recent lived context matters
6. The live Google Sheet referenced by `PB_CONTENT.gsheet`, tabs `Content List` and `Content Live`
7. `knowledge_base/` only when you need optional pattern support or language checks

Use this pass to understand:

- the current PersonalBrand operating model
- the audience and credibility boundaries for LinkedIn
- what is actually happening in the user's work and life right now
- what is already planned, approved, ready, or missing in the live system

## Grounding Questions

If the context is still unclear after reading the sources, ground strategy around these questions:

- What current role, career direction, or transition is the user living through?
- What recent work, project, or learning experience is available to write from?
- Who should the current LinkedIn season attract or resonate with?
- What should the next 2-4 weeks of content accomplish?
- What claims, lessons, or advice would overstate the user's real experience?

Prefer repo and live-sheet evidence over asking the user unless the answer is truly missing.

## Strategy Frame

Replace generic content-marketing thinking with these PB-native buckets:

- `Evergreen authority-building`
  - grounded explanations, systems thinking, durable lessons, clear points of view
- `Timely learning-in-public`
  - recent confusion, course-correction, project friction, evolving understanding
- `Bridge posts`
  - connect real work, building, and reflection into a coherent narrative direction

Every proposed direction should fit one of these buckets.
Do not frame the work around searchable vs shareable, funnel keywords, or buyer-stage SEO modifiers.

## PB LinkedIn Lanes

Use the current channel guidance in `brandguide/linkedin.md` as the default lane set:

- learning in public
- real work experience
- career direction and standards
- building and projects
- systems thinking
- reflection posts

Treat these as the current strategy pillars.
Do not invent a new pillar system unless the existing lanes are clearly insufficient.

## Ideation Sources

Default source order for ideas:

1. recent lived context from diary memory
2. gaps, repetition, and backlog state in `Content List`
3. open or underused direction in `Content Live`
4. approved or disapproved title history in the live sheet
5. current building or work threads visible in repo context
6. optional `knowledge_base/` patterns only as support, never as the main source

External market research is optional validation at most.
Do not let Reddit, Quora, or competitor posts override lived context and brand truth.

## Scoring Model

Score candidate directions using a PB-specific lens:

- `Reality strength`
  - can the user write this from direct experience right now?
- `Audience resonance`
  - is this likely to matter to the people the user wants to attract on LinkedIn?
- `Strategic fit`
  - does it strengthen the current narrative direction instead of fragmenting it?
- `Freshness`
  - is this timely enough to feel alive rather than backfilled?
- `Draftability`
  - can `pb-linkedin-title` turn this into a credible row-ready proposal without inventing missing context?

Prefer honest, grounded, strategically coherent ideas over broad or impressive-sounding ones.

## Decision Rules

When proposing the next directions:

- start from what the user is actually living, learning, building, or rethinking
- prefer a tight set of directions that reinforce each other
- avoid repetitive variations of the same post unless the live queue needs continuity on purpose
- keep claims modest and first-person
- reject directions that depend on authority the user has not earned yet

If the live queue is already healthy and aligned, say so and recommend only minimal course correction.

## Output Contract

Return a short strategy brief in this shape:

```markdown
Current narrative state:
- <what the current PB season seems to be about>

Recommended focus lanes:
- <lane and why now>

Priority directions:
1. <direction title>
   Grounding: <recent reality or live-sheet basis>
   Lane: <linkedin lane>
   Frame: <evergreen authority-building | timely learning-in-public | bridge post>
   Handoff to pb-linkedin-title: <what the title skill should preserve>

2. <direction title>
...

Gaps or drift:
- <what is missing or overrepresented in the current live plan>

Next handoff:
- Route approved directions to `pb-linkedin-title` for row-ready proposals.
```

Default to exactly 5 priority directions unless the user asks for a different number.

## Handoff Rules

After strategy is approved:

- send only the approved directions and their grounding notes to `pb-linkedin-title`
- let `pb-linkedin-title` decide the exact row wording and sheet write mechanics
- let `pb-linkedin-gm` own approvals and sequencing when the task is part of a weekly run

Do not mutate the live sheet unless the user explicitly asks for a strategy artifact to be written somewhere.

## Final Checks

Before responding, confirm:

1. The strategy is LinkedIn-first and PB-specific.
2. Every direction is grounded in repo context, diary memory, or live-sheet state.
3. No section relies on SEO funnels, ICP language, support-ticket logic, or company-blog framing.
4. The advice does not overstate authority or experience.
5. The handoff notes are specific enough for `pb-linkedin-title` to continue without inventing new strategy.
