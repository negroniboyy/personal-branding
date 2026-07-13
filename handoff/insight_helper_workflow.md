# Insight Helper — "I'm out of ideas" runbook

_Masterplan v4.0 §8 / v3.0 PRD §8. A **procedure**, not app code. Run it as a Claude session
from your laptop whenever the Studio idea queue runs dry. Promotable to an in-app feature later
if it becomes a habit — until then, it lives here._

> **Packaged as a global skill.** Invoke with **`/insight-helper`** (or just say "I'm out of
> ideas") from a session in this workspace. The skill lives at
> `~/.claude/skills/insight-helper/SKILL.md` and defers to **this doc as the canonical spec** —
> if they ever differ, this repo copy wins. Edit here first, then mirror into the skill.

---

## When to run this

Run it when the **Ideas queue is empty or stale** — nothing `queued` worth drafting, and you
don't have a fresh angle top-of-mind. This is the top of the funnel: it manufactures *candidate
ideas*, never finished posts. Everything it produces still passes through Studio review before it
becomes anything.

## Where this runs (important)

This is a **laptop-side Claude session** — the same kind you're reading this in. It touches only
two things over the network:

- **Firecrawl MCP** — to scan X / blogs.
- **Notion MCP** — to write accepted ideas into the CONTENT database.

**The GCP VM is not in this loop at all.** You put ideas *into* Notion from your laptop; the VM's
nightly timer independently *pulls* them out to draft. Notion is the hand-off point between the
two. So this workflow needs **no VM access and not even the running PBS app** — just the two MCPs
and the framing files in your local repo clone.

```
YOUR LAPTOP                        CLOUD                    VM (headless, decoupled)
Claude session
  ├─ Firecrawl MCP ──scan──────>  X / blogs
  ├─ reads framing files (local)
  └─ [YOUR OK] ──create pages──>  Notion CONTENT db
                                       │  nightly pull (independent)
                                       └──────────────────> drafts tiers → "Script ready"
```

---

## The framing files (context this session must load first)

All paths are relative to the **BrandStudio root**. These are the single source of truth for
"in Max's framing" — the session reads them, it does not guess:

| File | What it supplies |
|------|------------------|
| `personal_brand/brandguide/brandbook.md` | The **three pillars**, audience, guardrails, and the canonical decision filter. |
| `personal_brand/brandguide/voice_dna.md` | The voice — how a candidate should *sound* when rewritten in your framing. |
| `profile/brainstorm_seeds.md` | Recurring themes and underserved niches you keep circling back to — the scan's seed list. |

### The three pillars (from `brandbook.md` — scan targets)

1. **IT/AI early career, learning in public** — Japanese IT (hakken contracts, recruiters,
   negotiation), AI implementation from the trench, presentation skills, honest inner thoughts.
2. **Runner / athlete** — marathon training, run clubs + solo focus, knee-protective strength,
   software-for-running crossover.
3. **Systems for living** — habits, routines, finance discipline, iteration applied to life,
   ego/attachment as noise, clarity over effort.

The cross-bleed between pillars *is* the brand — prefer candidates that connect two.

---

## The kickoff prompt (paste to start a session)

> I'm out of ideas for content. Run the **Insight Helper** workflow from
> `personal_brand/handoff/insight_helper_workflow.md`.
>
> 1. Load `personal_brand/brandguide/brandbook.md`, `personal_brand/brandguide/voice_dna.md`,
>    and `profile/brainstorm_seeds.md`.
> 2. Use **Firecrawl** to scan X and blogs for recent, concrete material in my three pillars and
>    the brainstorm seeds. Favor firsthand, specific, underserved angles — not thought-leader takes.
> 3. Propose **6–8 candidate ideas** in my framing, as candidate cards (format below). For each,
>    show which pillar(s) it hits, a suggested Tier and channel, and the source link.
> 4. Run every candidate through the brandbook decision filter before showing it to me. Drop
>    anything that fabricates, preaches, or fails the filter — don't show me filler.
> 5. **Stop and wait for my OK.** Write nothing to Notion until I name the ones I accept.
> 6. On my OK, create the accepted ideas in the Notion CONTENT database via **Notion MCP**, using
>    the field mapping below, with `status = Not started`.

---

## Phase 1 — Scan (Firecrawl)

Use Firecrawl to pull *recent, concrete* material across the three pillars and the brainstorm
seeds. Good raw material has real names, numbers, or firsthand specifics — the same concreteness
bar that keeps generation from fabricating. Prefer:

- Firsthand accounts over commentary (a real hakken contract clause > a "career tips" listicle).
- Underserved niches you're actually living (Japan IT dispatch reality, early-career AI from the
  support trench, engineering-your-own-tools).
- Anything that lets two pillars cross-bleed.

Skip: generic advice, motivational threads, ragebait, anything you couldn't speak to firsthand.

## Phase 2 — Propose (candidate cards, in your framing)

Rewrite each raw find as a candidate **in your framing** — not the source's words. One card each:

```
### Candidate N — <short working title>
- Pillar(s): <1 / 2 / 3, name them>
- Angle: <1–2 sentences — the specific observation, in Max's voice, zero invented detail>
- Suggested channel: LinkedIn | Instagram   (same material can split: IG gets the moment,
                                             LinkedIn gets what you noticed in it)
- Suggested Tier: Scripted headshot | Music-beat edit | Raw talking head
- Source: <url>
- Filter check: <one line — why it passes: capable-not-lecturing, real, would-say-out-loud>
```

Every card must pass the **brandbook decision filter** before you see it:
1. Real observation, not manufactured performance?
2. Still feels right if engagement were zero?
3. Would Max feel natural saying this to camera?
4. Leaves the viewer feeling capable, not behind?
5. Reflects actual life/work/training/learning, zero invented details?

If any answer is no → the candidate is cut, not shown.

## Phase 3 — Gated write (only after your OK)

**Nothing enters Notion without your explicit approval.** You reply with the candidates you accept
(e.g. "add 1, 3, 5"). Only then does the session create those pages in the Notion CONTENT database
via Notion MCP.

### Field mapping (accepted candidate → Notion CONTENT db)

| Notion property | Type | Value written |
|-----------------|------|---------------|
| `Name` | title | The working title |
| `Description` | rich text | The angle, in your framing (Phase 2 card body) |
| `Select` | multi-select | Channel(s): `LinkedIn` and/or `Instagram` |
| `Pillar` | select | The pillar (add the option in Notion first if it doesn't exist yet) |
| `Tier` | select | `Scripted headshot` / `Music-beat edit` / `Raw talking head` |
| `status` | status | **`Not started`** — always, for a fresh idea |

New ideas land as `Not started`. On its next sync, PBS pulls them as `queued` and they appear in
Studio, ready to draft. From there it's the normal loop — the insight helper's job is done.

_(Field names verified against `personal_brand/notion_ideas/mapper.py`. `Pillar` and `Tier` are
optional selects; if Notion doesn't have the option value yet, add it in Notion before the write.)_

---

## Guardrails

- **Human gate is absolute** — no Notion write before an explicit OK. The scan and proposal are
  free; the commit is yours alone.
- **Dedupe** — before proposing, have the session check existing Notion ideas (and Studio's queue
  if reachable) so it doesn't re-suggest something already there.
- **Framing, not fabrication** — candidates are rewritten in your voice from *real* sources; the
  session never invents specifics to make an angle land.
- **Quality over volume** — 6–8 strong candidates that pass the filter beat a long filler list.
  A short list is a success, not a shortfall.
- **Stays a doc** — this is deliberately not app code. Only promote it into PBS if it becomes a
  genuine habit (PRD §8).
