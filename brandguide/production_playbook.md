# Production Playbook — Instagram Reels

> The repeatable loop for shipping reels through the existing frontend (ReelWriter tab).
> Pairs with `brandguide/content_strategy_log.md` (the verdict log / lessons).
> Generation is free (`gpt-oss-120b:free`) and runs against your local API.

Last updated: 2026-06-01

---

## Phase 0 — Ship what's already done (this week)

The n=3 batch drafts are already saved in the DB, so they appear in **Recent Scripts** in the UI.
Run `./start.sh`, open the **Reel** tab, scroll to Recent Scripts, and click these by number:

| Slot | Date | Script # | Theme | Status |
|---|---|---|---|---|
| I1 | Jun 3 | **#41** (ref2-bold_claim) | Fitness / injury reset | Post-ready (grade A). Copy → post. |
| I2 | Jun 10 | **#53** (ref1-contrarian) | Imposter syndrome | Post-ready (A-). Light edit pass, then post. |
| I3 | Jun 17 | _regen_ | Japanese learning | Enrich node first (see Phase 2), then post. |
| I4 | Jun 24 | _new_ | New node | Run the full loop fresh. |

For each: click the script → read it in the canvas → tweak if needed → **Save** → **Copy** → paste into Instagram.

---

## Phase 1 — The weekly loop (new content)

In the **Reel** tab:

1. **Surface the story.** Use the domain chip + IDEA HINT box to filter, then pick a story in the **STORY** dropdown. (Dropdown shows the top ~20 by worth, labelled by conflict.)
2. **Concreteness check (the #1 lever).** Glance at the story. If it's thin/abstract (no real names, numbers, or specifics), it WILL fabricate — see Phase 2 before generating.
3. **Generate the defaults.** Framework = **ref2-bold_claim** → Generate. Switch the framework dropdown to **ref1-contrarian** → Generate again. (Add **ref3-pain_point** only if it's a vulnerable/struggle story.) Keep model on `gpt-oss-120b:free`.
4. **Compare.** Both drafts land in Recent Scripts. Click each and read.
5. **Get a verdict.** Tell Claude the node + script numbers; Claude grades them against the voice DNA and logs the verdict in `content_strategy_log.md`.
6. **Ship.** Copy the winner, edit if needed, Save, post.

Skip the weak frameworks: **ref1-bold_claim** (70s, rambly, fabricates) and **ref6-bold_claim** unless the story is very concrete.

---

## Phase 2 — Enrichment (for thin stories)

If a story is too abstract (the Japanese node is the example), fabrication is guaranteed. Fix it upstream, two options:

- **Fast:** type 2-3 real specifics into the **IDEA HINT** box (what you actually did/studied, the real situation) before generating. The hint feeds the prompt.
- **Durable:** edit the `story_node` itself so every future generation has the detail.

Then generate as in Phase 1.

---

## Known limitations (current UI)

- **One framework per click** — no "generate all frameworks" button yet, so you switch the dropdown and re-generate. This is the friction the proposed UI button would remove (future build, not now).
- **No side-by-side compare** — drafts stack in Recent Scripts; compare by clicking between them.
- Generation runs locally only (sandbox can't reach OpenRouter).

---

## Definition of done (per post)

A reel is ready when: it sounds like you (no influencer CTAs, honest current-state close), invents nothing not in the source story, and you'd actually say it out loud. When in doubt, send it to Claude for a voice check before posting.
