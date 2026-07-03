# Blueprint v3.0 — PBS Reboot (PRD)
_2026-07-03 · Planning model: Fable/Sonnet 5 · Status: awaiting Max's approval · This document IS the new PRD._

## Why (the problem)

PBS got messy because the **input was bad**: the Notion diary → `narrative_warehouse` → `story_nodes` ingest fed unstructured "idea vomit" with no context into generation. Result: drafts that never felt natural to shoot — zero headshot videos filmed despite a working pipeline and 7+ approved scripts. The fix is upstream: **proper content ideas in, from a curated Notion database**, with the whole diary layer retired. The Notion API key has already been re-scoped to the "Personal Project" page.

## 1. STATE

**Current repo (v2.7):** FastAPI :9000 + React frontend; diary sync → story_nodes extraction → story-first generation (Warehouse/Writer/Reels tabs) + idea-path generation (Ideas tab) → Studio lifecycle (queued→approved→recorded→posted, verdict feedback) → Asana mirror via Cowork nightly routine. Ollama available as local fallback. `ideas-tab` branch (v2.7) still unmerged — **merge it before starting v3 work**.

**What v3 keeps:** Studio tab + lifecycle (`shared/shared/lifecycle.py`), Ideas tab as the primary surface, voice-aware idea-path builders (`content_writer/prompt_builder.py`, `frameworks/instagram_frameworks/prompts/script_writer_idea.txt`), OpenRouter router + `config/openrouter_models.yaml`, MD mirroring, brandguide layer (rebuilt 2026-07-03: `brandbook.md` + `voice_dna.md` v2 + `voice_dna_block.txt` v2).

**Affected files:** see §2 (archive list) and §3–§7 (new/modified).

## 2. REMOVE / ARCHIVE (nothing deleted)

Create `personal_brand/_archive/` and move:

| What | Paths |
|---|---|
| Diary→story ingest | `narrative_warehouse/` (whole dir incl. its tests) |
| Diary sync client | diary-sync parts of `NOTION DIARY FETCHER/src/notion_fetcher` (the generic Notion client code is REUSED by the new ideas sync — split before archiving) |
| Story-first generation | `frameworks/instagram_frameworks/prompts/script_writer.txt` (story path), story-first branches in `script_writer.py`, `batch_generate.py`, `gen_one_node.py`, `migrate_backfill_processed.py` |
| Story-first UI | `StoryNodeList.jsx`, `StoryNodeCard.jsx`, `StoryPreview.jsx`, `NarrativeDashboard.jsx`, Warehouse tab, story dropdowns in `ReelWriter.jsx`/`ContentWriter.jsx` |
| Ollama path | `ollama` leg of `openrouter/router.py` cascade, `provider = ollama` toggles in `config.toml`, Ollama entries in `ModelSelector.jsx` |

`notion_diary.db` stays in place **read-only** (110 story_nodes = idea mine). Brandguide archives already done (`brandguide/_archive/`).

## 3. NEW INGEST — Notion "Personal Project" ideas DB, two-way sync

- New module `notion_ideas/` (reuse the Notion client split from `notion_fetcher`): pulls rows from the content-ideas database on the "Personal Project" page into the existing `ideas` table.
- **Pull:** idea title, description/context, pillar, tier (if set in Notion), Notion page_id. Upsert by page_id; manual "Sync" button in Ideas tab + scheduled pull on the VM (§7).
- **Push:** lifecycle status changes (queued → drafted → approved → recorded → posted / killed) write back to a Status property on the Notion row. `shared/shared/lifecycle.py` remains the single status vocabulary — mapped 1:1 to Notion select options.
- Conflict rule: Notion wins for idea *content*; PBS wins for *status*. No merge logic beyond that.

## 4. IDEAS AS THE SPINE

Each idea carries: **pillar** (`it-ai-career` / `runner` / `systems-for-living`), **production tier** (`scripted-headshot` / `beat-edit` / `raw-talking-head`), **status**, **draft iterations**.

Tier selects the output format at generation time:
- `scripted-headshot` → full structured script (sharpened register)
- `raw-talking-head` → talking points + natural opening line, NOT word-for-word
- `beat-edit` → shot/beat list with on-screen text, minimal words

Implementation: tier-specific prompt templates alongside `script_writer_idea.txt` (e.g. `script_writer_raw.txt`, `script_writer_beat.txt`), all injecting `brandguide/voice_dna_block.txt` (v2 — it already defines the three registers). Business logic in builders, not UI (root CLAUDE.md rule).

## 5. SCRIPT DRAFTING LOOP (the core user story)

> Max drops a raw idea in Notion → PBS pulls it → he (or the VM automation) generates a tiered draft → he iterates a few times in Studio (each regeneration = new version, prior versions kept per idea) → approves → shoots. **Acceptance test: he feels natural shooting it.**

Draft versioning: add `version` + `parent_draft_id` (or an `idea_drafts` history table) so iterations are comparable; Studio shows version history per idea.

## 6. LLM SIMPLIFICATION — OpenRouter only

- Cascade becomes primary → secondary (both OpenRouter); failing selected model = surfaced error, never silent swap (existing rule).
- `config/openrouter_models.yaml` stays the single routing source of truth with the already-vetted models. Model re-testing deferred.
- Ollama fully retired (see §2) — this removes the last local-machine dependency.

## 7. GCP VM DEPLOYMENT + NOTIFICATIONS

- Backend runs headless on Max's GCP VM (uv + systemd service for FastAPI; frontend stays local-dev or static-served — decide at implementation).
- **Scheduled automation** (systemd timer or cron; replaces the Cowork nightly routine): pull new Notion ideas → generate a draft for each un-drafted idea per its tier → write drafts + set status `drafted`.
- **Notification on new drafts ready:** primary = **Notion-native** (status write-back + a "Ready for review" notification/reminder property on the row — nearly free given two-way sync). Optional second channel: email via SMTP (Gmail app password), config-gated.
- Secrets on VM: `.env` (Notion key, OpenRouter key), never committed; `config.toml` gains a `[deployment]` section (local vs. vm).

## 8. INSIGHT HELPER (agent workflow — zero app code in v3.0)

Documented procedure at `handoff/insight_helper_workflow.md` (write during implementation): when out of ideas, a Claude session uses **Firecrawl MCP** to scan X/blogs against the three pillars + `profile/brainstorm_seeds.md`, proposes candidate ideas in Max's framing, and on his OK writes accepted ones into the Notion ideas DB. Promotable to an in-app feature later if it becomes habit.

## 9. DEFERRED (explicitly out of v3.0)

Performance→prompt feedback loop · reference framework/style extraction (waiting on Max's uploads) · OpenMontage handoff automation (`OpenMontage/` untouched) · model re-testing/bake-offs · in-app insight helper.

## 10. SPECS

Python 3.12 / uv · FastAPI :9000 · React 18 + Vite + Tailwind, logic centralized outside UI files · SQLite (each repo its own DB) · must run headless on Linux VM (no local-machine dependencies) · archive-don't-delete · Blueprint Protocol for any scope growth.

## 11. DEFINITION OF DONE

1. Diary/warehouse/Ollama code archived; app boots and all surfaces work without them.
2. Ideas tab shows ideas pulled from the Notion "Personal Project" DB; status changes in Studio appear in Notion.
3. Generating from an idea respects its production tier (3 distinct output formats), voice-injected from `voice_dna_block.txt` v2.
4. Draft iterations are versioned and visible per idea.
5. Backend + scheduled draft automation run on the GCP VM; Max gets notified (Notion, optionally email) when drafts are ready.
6. **The real test:** Max takes one raw idea end-to-end and shoots the first headshot video because the draft finally feels like him.

## Implementation order (suggested)

Merge `ideas-tab` branch → §2 archive + Ollama removal → §3 Notion sync (pull first, push second) → §4 tiers + prompts → §5 versioning → §7 VM deploy + automation → §8 workflow doc.
