# Blueprint v4.0 — Masterplan: The Shipping Flywheel
_2026-07-07 · Planning model: Fable 5 · Status: awaiting Max's approval · Supersedes nothing — v3 finishes first._

**Alignment locked with Max (2026-07-07):** north star = **shipping discipline** ·
deploy = **VM private on tailnet + Vercel public HQ** · metrics = **screenshot-drop ingestion** ·
idea input = **deliberate entry only** (no capture funnel — respects the locked no-diary decision).

---

## Operating thesis

PBS's risk was never capability — it's that **building substitutes for shipping**. Max named it
himself. So v4 is not a feature list; it is a **shipping contract**: every phase after the runway
is *gated on posted content*, so feature hunger becomes shipping fuel instead of its replacement.

The system's three jobs, in priority order:

1. **Make shooting cheaper** — kill every reason a draft doesn't become a video.
2. **Make reality flow back in** — a post's real performance and Max's own verdicts must
   change what gets generated next. Today the loop is open; nothing learns.
3. **Compound what ships** — every posted piece becomes a reusable asset (evidence, callbacks,
   portfolio, taste data) instead of evaporating into a feed.

Explicitly **excluded** (Max's list + locked decisions): auto video editing, transcription
features, automated posting, posting schedulers/calendars, diary resurrection, in-the-moment
capture surfaces, invented personas. The system augments a real person shipping raw work.

---

## 1. STATE

### Repo summary (as of commit `7fb01d3`, 2026-07-07)

`personal_brand/` — Python 3.12/uv · FastAPI :9000 · React 18/Vite/Tailwind :5173 · SQLite.
v3 §2–§5 + v3.4 committed: idea-first pipeline (Notion two-way sync), background job queue,
LLM framework picker, 3 production tiers, reel versioning, beat-edit reference extraction
(vision). MVP is functional; UAT (30 shipped pieces) has not started.

**v3 remainder (owned by v3 trail, absorbed here as Phase 0):** v3.3 in-browser QA →
§7 GCP VM deploy → §8 insight-helper doc. Plus: Max adds `Killed`/`Pillar`/`Tier` Notion props.

**Security debt (do before anything else):**
- **Rotate the OpenRouter key.** The real key sits in git history (`.env.example`, commit
  `1b96a04` and earlier) on a GitHub-hosted repo. Working tree is sanitized as of `7fb01d3`;
  history is not. Rotation > history rewrite (cheaper, sufficient once the old key is dead).
- Move VM secrets to `.env` on the VM only; never in repo. Optional later: GCP Secret Manager.

### Dead-code & staleness report (audited 2026-07-07, per Max's request)

**Verified ALIVE — do not remove** (each import-checked): `content_writer/recommender.py`
(used by `service.py` + `picker.py` keyword fallback) · `shared/shared/md_mirror.py` (used by
handlers, main, reel_routes) · `NOTION DIARY FETCHER/src/notion_fetcher/client.py` (reused by
`notion_ideas/`).

| # | Item | Evidence | Recommendation |
|---|------|----------|----------------|
| 1 | `dashboard.html` (repo root) | Orphan static "Productivity" page; zero references from any code/doc; loads Google Fonts | Archive to `_archive/` |
| 2 | `.vent/` (repo root) | Empty directory — typo sibling of `.venv` | Delete (nothing to archive) |
| 3 | `TASKS.md` | Frozen 2026-05-27; pre-v3 June calendar; superseded by checkpoint + Notion/Asana | Archive |
| 4 | `frameworks/linkedin_frameworks/extract_linkedin.py` + `llm_client.py` | No imports from any live route/module; one-time CLI extraction utilities from the reference era | Dormant utility — either document as CLI in README or archive until LinkedIn reference extraction is next needed |
| 5 | `knowledge_base/` | Zero code references (`*.py`/`*.js*`) | Not code — keep as reference material, but move under `brandguide/_reference/` or archive; stop listing it as an active subsystem |
| 6 | `brandguide/content_workflow.md`, `brandguide/production_playbook.md` | Self-marked SUPERSEDED; describe retired story-first loop | Extract the still-valid **time-caps rule** into `brandbook.md`, then archive both |
| 7 | `handoff/routine_nightly_content.md` + Cowork nightly task | §7 VM timers replace the Cowork routine by design (PRD §7) | Retire both at §7 cutover — add to §7's Definition of Done |
| 8 | Stale `yaml_path` on every `reel_frameworks` row | Points at pre-move legacy paths (known from checkpoint) | One-time migration: repoint or drop the column if nothing reads it |
| 9 | `PERSONALBRAND.md` | Banner says "rewritten after v3 lands"; Ingest/Extract/story-first sections describe retired code | Rewrite post-§7 (small task, big confusion-saver) |
| 10 | `memory/` (glossary, reference_creators, projects/) | Docs-only; partially describes the retired system | Review pass; fold still-true content into brandguide/profile, archive rest |
| 11 | `.gitignore` gap | `references/*.MP4` doesn't cover `references/beat_edit/` subfolder | Add `frameworks/instagram_frameworks/references/**/*.MP4` (+ lowercase) — one line, prevents a 60 MB accident |
| 12 | Root strays `NOTION/`, `DIARY/` | Gitignored empty leftovers | Delete locally |

**Alive but overlapping (consolidation candidates, NOT dead):** `ReelWriter.jsx`,
`ContentWriter.jsx`, `ModelSelector.jsx` — standalone generation tabs from the pre-Ideas era.
The Ideas→Studio path is the primary surface; these duplicate it with manual controls. Decide
at Phase A whether to fold them into IdeaDetail or keep as power-user panels. Also `main.py:62`
does `import script_writer as _sw` via `sys.path` mutation — works, but a packaging smell to fix
whenever the API root gets touched.

### Assets nobody is using yet

- `MobileNav.jsx` already exists — the frontend is mobile-aware. One PWA manifest away from
  Studio-on-your-phone over Tailscale (Phase 0 exploits this).
- `frameworks/api_routes.py::_get_stats` already computes used/approved/killed per framework —
  the seed of the evidence-weighted picker (Phase B exploits this).
- `notion_diary.db` (read-only) holds 110 story_nodes — a one-time idea mine (Phase C).
- OpenMontage's free/local tools (Piper TTS, Remotion transparent overlays) — used below
  strictly for **pre-production**, never auto-editing.

---

## 2. LOGIC — the phase map

Each phase ships as its own thin blueprint (`v4.1`, `v4.2`, …) per the Blueprint Protocol.
Phases B–D are **gated on posted-piece count** (posts marked `posted` in Studio — no
scheduling involved, just counting reality). Gates are enforced socially, not cryptographically:
Studio shows a "flywheel meter" (posts shipped / next unlock); the checkpoint doc tracks it;
Max can override consciously, never accidentally.

```
Phase 0  (now)        RUNWAY      — rotate key · v3.3 QA · §7 deploy · §8 doc · hygiene sweep
Phase A  (no gate)    PRE-CAMERA  — table-read TTS · fabrication linter · enrichment interview ·
                                    production brief compiler (OpenMontage bridge)
Phase B  (5 posted)   REALITY IN  — screenshot-drop metrics · hypothesis cards ·
                                    evidence-weighted picker
Phase C  (15 posted)  COMPOUND    — verdict RAG (taste model) · callback engine ·
                                    pillar balance ledger · story-node idea mine
Phase D  (30 posted)  PUBLIC HQ   — Vercel proof-of-work site · job-flywheel tagging
Cross    (continuous) OPS         — backups · cost ledger · observability · tests · dead-code sweep
```

### Phase 0 — Runway (v3 scope, finish it)

1. **Rotate OpenRouter key** (Max, 5 min, today).
2. **v3.3 in-browser QA** (Max): generate all 3 tiers, regenerate, kill/fallback.
3. **§7 GCP VM deploy** — the topology locked with Max:

```
Phone/Laptop ──tailscale──> GCP VM
                             ├─ FastAPI :9000  (systemd unit `pbs-api`)
                             ├─ jobs worker    (same process; queue survives restarts already)
                             ├─ systemd timer  `pbs-nightly`: pull Notion ideas → tiered drafts
                             │                 → status `drafted` → Notion write-back notification
                             └─ frontend       static build served by FastAPI (StaticFiles) or
                                               Caddy, over Tailscale Serve (HTTPS on tailnet)
Public internet ──> Vercel: brand HQ (Phase D only — nothing public before that)
```

   - **PWA manifest + icon** for the frontend so Studio installs to Max's home screen —
     review/approve/kill from the phone after a run. `MobileNav.jsx` makes this nearly free.
   - **Beat-edit detection caveat** (from checkpoint): Scan Folder assumes local file access —
     on the VM, `references/` lives on the VM disk; scanning stays a laptop-side or
     scp-then-scan operation. Document, don't over-build.
   - **Backups from day one:** SQLite → nightly `sqlite3 .backup` snapshot + `gsutil cp` to a
     GCS bucket (or Litestream if appetite allows). The DB is becoming the brand's memory;
     losing it loses the moat.
4. **§8 insight-helper doc** (`handoff/insight_helper_workflow.md`) — as PRD'd, zero app code.
5. **Hygiene sweep** — execute the dead-code table above (archive-don't-delete).

**DoD:** Studio reachable from phone via tailnet · nightly timer produces drafts headlessly ·
key rotated · first headshot video shot and posted (v3 PRD DoD #6 — this starts the UAT count).

### Phase A — Pre-camera layer (no gate; runs during UAT)

Everything here attacks the single historical failure: *drafts that never became videos*.

1. **Table-read (TTS shoot test).** On demand per approved script: pipe script text through
   OpenMontage's local Piper TTS → MP3 in the script's detail view. Max *hears* it before
   setting up a camera — "would I actually say this?" caught at zero cost. Pre-production,
   not editing; local, free, no new keys.
   - Logic: `POST /reels/scripts/{id}/table-read` → job `table_read` → subprocess call into
     OpenMontage's Piper wrapper (or plain `piper` binary) → store MP3 path on the script row.
2. **Fabrication linter.** His #1 durable finding: thin input → invented specifics, and
   fabrication is an instant kill. New LLM task `lint_fabrication`: extract every concrete
   claim (names, numbers, events, quotes) from a draft → check each against the idea's source
   text → badge unsupported claims in Studio *before* Max reads the draft. Verdict button
   "kill: fabricated" feeds the taste dataset (Phase C).
3. **Enrichment interview (deliberate-time, not capture).** When an idea's concreteness score
   is low (no names/numbers/specifics — cheap heuristic + LLM assist), the generate button
   offers "Enrich first": 2–3 interview questions in Max's preferred style; answers append to
   the idea's context (and push back to Notion, which already wins on content). Turns the
   "concreteness drives quality" law into a workflow instead of a memory.
4. **Production brief compiler (OpenMontage bridge v1 — still human-triggered).** On approve:
   compile `handoff/briefs/<idea-slug>_v<n>.md` — script, tier, register, verdict notes,
   `voice_dna_block.txt`, beat/shot checklist (beat-edit tier), teleprompter-formatted text,
   suggested reference frameworks. An OpenMontage session (or DaVinci prep) consumes the file;
   the copy/paste era ends without automating production itself. This is the
   `blueprint_openmontage_bridge` PERSONALBRAND.md anticipated.

**DoD:** for one real script: table-read heard, linter caught ≥0 fabrications honestly,
one brief file consumed in an OpenMontage session without manual re-briefing.

### Phase B — Reality intake (gate: 5 posted)

1. **Screenshot-drop metrics.** Studio "Add results" on any posted piece → drop 1–n
   screenshots of IG/LinkedIn insights (from the phone over tailnet) → vision task
   `extract_post_metrics` (new task in `openrouter_models.yaml`, reuses the proven
   `complete_vision` path from beat-edit extraction) → parsed into new `post_metrics` table
   (`script_id/draft_id, platform, captured_at, views, reach, likes, comments, saves, shares,
   follows, watch_pct?, raw_json, screenshot_path`). Manual, ~1 min/post, no Meta API, no
   scraping. Re-drop later screenshots → new snapshot rows (time-series for free).
2. **Hypothesis cards.** Every piece marked posted gets one falsifiable bet — auto-suggested,
   Max-editable ("beat-edit + fine-line theme will out-save talking-head"). When metrics land,
   the card resolves (supported / refuted / unclear + note). This is the marketing-analysis
   muscle *made visible* — and the resolved cards are themselves content fuel: "I tested X on
   my own account, here's what happened" is pillar-1×3 cross-bleed, in his exact voice.
3. **Evidence-weighted picker.** Extend `_get_stats` with performance quantiles from
   `post_metrics`; picker prompt gains an EVIDENCE block ("this framework: 3 posts, top-quartile
   saves"). LLM still chooses; evidence informs. No auto-optimization theater.

**DoD:** ≥5 posts have metrics snapshots · ≥3 resolved hypothesis cards · picker prompt
demonstrably cites evidence for one real generation.

### Phase C — Compounding memory (gate: 15 posted)

1. **Verdict RAG (the taste model, no fine-tuning).** Every approve/kill already carries a
   verdict note. Index them (SQLite FTS5 is enough at this scale — no vector DB) and retrieve
   the 3–5 most relevant past verdicts into every generation prompt: "past-Max on a similar
   draft: 'felt performative, killed'." The system starts inheriting his judgment — the one
   asset that grows every single week he ships.
2. **Callback engine.** Index shipped content (hooks, phrases, recurring bits, numbers).
   Generation gets: (a) callback suggestions — audiences bond over recurring bits ("the
   fine-line thing again"); (b) self-repetition warnings — same hook twice in 3 weeks gets
   flagged. Both advisory, never blocking.
3. **Pillar & register balance ledger.** Rolling 30-day view: posted mix vs brandbook intent
   across pillars and tiers. Drift surfaced as one honest line in Studio ("3 weeks, zero
   pillar-2"). No dashboard-ism — one meter, one sentence.
4. **Story-node idea mine (one-time).** Deliberate distillation pass over the 110 read-only
   story_nodes → candidate ideas written to the Notion ideas DB for Max to triage *in Notion*
   (keeps "deliberate entry" as the only doorway into the system).

**DoD:** generation prompts contain retrieved verdicts · one callback suggestion shipped in a
real post · balance meter live · idea mine emptied into Notion and triaged.

### Phase D — Public HQ on Vercel (gate: 30 posted = UAT passed)

The reward phase — only exists because 30 real pieces exist.

1. **Brand HQ static site.** Built *from the DB*: every `posted` piece becomes a page (script/
   caption + Max's post-hoc note + link to the platform post), grouped by the three pillars;
   plus a "systems I built" portfolio section (PBS, TurboBaba, the OpenMontage workflow — the
   proof-by-action story). Static generation (Astro or Vite SSG — decide at v4.x blueprint;
   stays in his React lane), built by a VM timer, deployed via Vercel deploy hook. No Studio
   access, no secrets, nothing dynamic public-facing.
   - This is not auto-posting: it mirrors only what Max already chose to publish, on a
     property he owns. It compounds (SEO, recruiter link, owned audience) while feeds decay.
2. **Job-flywheel tagging.** Each HQ item optionally tagged to Solutions-Engineer competencies
   (mirrors his experience-to-story practice) → "show me evidence for X" query when tailoring
   applications. Content becomes career capital with zero extra production work.

**DoD:** HQ live on Vercel with ≥30 pieces + portfolio section · one job application sent that
links to an HQ evidence page.

### Cross-cutting — Ops & unit economics (continuous, no gate)

- **Cost ledger:** log OpenRouter usage (tokens/cost from response metadata) per job →
  `$ per shipped post` on the Studio meter. Marketing-brain unit economics; also validates
  model routing choices with data instead of vibes.
- **Observability:** `/healthz` (DB + worker heartbeat) · job dead-letter view in the existing
  jobs UI · optional tailnet-only uptime ping (ntfy) — no external monitoring SaaS.
- **Tests where they pay:** `notion_ideas/mapper.py` field mapping, version-family resolution,
  picker fallback, lifecycle transitions. Not coverage theater — these four break silently.
- **Error message quality:** the known "wrong folder" scan confusion (checkpoint note) —
  distinguish "no speech found" from "file in wrong folder" in scan errors.

---

## 3. SPECS

- Python 3.12 / uv · FastAPI :9000 · SQLite (migrations via existing `_run_migrations` in
  `NOTION DIARY FETCHER/api/main.py`) · React 18 + Vite + Tailwind, **all business logic
  outside UI files** (root rule) · headless-Linux-safe (no macOS/local deps in any Phase ≥0
  feature) · archive-don't-delete.
- New LLM tasks route through `config/openrouter_models.yaml` only (`extract_post_metrics`,
  `lint_fabrication`, `enrich_interview`, `suggest_hypothesis`, `suggest_callbacks`) —
  primary+secondary, paid-only, no silent fallback (existing rule).
- New job kinds registered via `jobs/queue.py::register` + handler in `jobs/handlers.py`
  (existing pattern; queue already survives crashes).
- New tables: `post_metrics`, `hypotheses`; FTS5 virtual table over verdicts/shipped content.
  **No vector DB, no Redis, no new services** — SQLite until it visibly hurts.
- VM: systemd units (`pbs-api.service`, `pbs-nightly.timer`, `pbs-backup.timer`), Tailscale
  Serve for tailnet HTTPS, `.env` on VM only. Vercel: static output + deploy hook, Phase D only.
- OpenMontage stays untouched as a repo; PBS consumes it as a toolbox (Piper TTS subprocess,
  brief files it can read). Any actual video production still routes through OpenMontage's
  own AGENT_GUIDE/pipelines per its Rule Zero.
- Voice: all new prompts inject `brandguide/voice_dna_block.txt`; nothing duplicates voice text
  (existing rule). Fabrication linter enforces voice_dna's no-fabrication law, not style.

## 4. GOAL — Definition of Done for v4.0 as a whole

1. The flywheel meter exists and gates B/C/D on real posted counts (5/15/30).
2. Phase 0 complete: key rotated, VM deploy live, Studio on the phone, backups running,
   dead-code table executed, first video posted.
3. By 30 posts: metrics + hypothesis history exists, generation prompts cite Max's own verdict
   history and evidence, and the public HQ is live on Vercel.
4. **The real test (inherited from v3 and still the only one that matters):** shooting feels
   cheaper every month, and the system can show — with Max's own data — *why* the content is
   getting better.

## Immediate next actions

1. **Max (today, 5 min):** rotate the OpenRouter key; add `Killed`/`Pillar`/`Tier` Notion props.
2. **Max:** v3.3 in-browser QA (3 tiers, regenerate, kill/fallback).
3. **Execution model (Sonnet, zero verbosity):** `blueprint_v4.1_runway.md` — §7 deploy +
   hygiene sweep + PWA, exactly as scoped in Phase 0 above. No code before that blueprint
   is approved.
4. Then A → B → C → D as gates open. One thin blueprint per phase, always.
