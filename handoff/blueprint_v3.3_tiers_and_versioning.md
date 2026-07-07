# Blueprint v3.3 — §4 Production Tiers + §5 Reel Draft Versioning

_2026-07-04 · Planning: Opus 4.8 · Execution: Sonnet 5._

## Context

PRD v3.0 §4 + §5 are the next two unstarted steps, bundled here because together they
complete the core drafting loop: **drop idea → generate in the right format for how you'll
actually shoot it → iterate a few takes → approve the one that feels natural.** §3 (Notion
sync) landed the `tier` column as groundwork but nothing reads it yet — every idea still
generates the same full script. §5 adds versioned iteration so regenerating keeps prior takes.

Scope is **reels only** for both features (tiers are video output formats; LinkedIn is a
separate channel and stays single-shot). §7 (GCP VM deploy) comes after Max tests this.

**Decisions locked with Max this session:**
- **Tier source:** default + PBS override. No-tier ideas default to `scripted-headshot`
  (today's behavior). A tier picker in `IdeaDetail` writes `ideas.tier`. Notion's `Tier`
  select still wins on pull when Max adds it — no blocking on his manual Notion work.
- **Templates:** `raw-talking-head` drafted from the PRD description + `voice_dna_block.txt`.
  `beat-edit` grounded in the real reference `frameworks/instagram_frameworks/references/beatedit.MP4`
  (frame-sampled during the build — see Part A3).
- **Versioning scope:** reels only. `reel_scripts` gets `version` + `parent_script_id`;
  `content_drafts` untouched.
- **Iterate UX:** replace + keep history. New version is the live card in Studio; older
  versions collapse into an expandable history per idea. Live = highest `version` per
  `idea_id` among non-killed rows.

## Definition of Done

1. Generating a reel for an idea respects its tier — three distinct output shapes:
   - `scripted-headshot` → full word-for-word structured script (current `script_writer_idea.txt`).
   - `raw-talking-head` → talking points + one natural opening line, NOT word-for-word.
   - `beat-edit` → ordered `shot | on-screen-text | pacing` beat list, minimal/no VO,
     matching the `beatedit.MP4` grammar.
   All three inject `brandguide/voice_dna_block.txt` v2. Tier resolves as
   `idea.tier or "scripted-headshot"`.
2. Tier is settable in `IdeaDetail` (dropdown, writes `ideas.tier`); Notion pull still
   overwrites it when the property exists. Badge shows current tier on idea rows.
3. Regenerating a reel for an idea creates a new `version` (prior versions kept, linked via
   `parent_script_id`). Studio shows the live version as the card; prior versions expand as
   history. Idea status derives from the **live** version only.
4. LinkedIn generation, one-off reels (no `idea_id`), and existing single-version ideas keep
   working unchanged. Migration is additive/backfilled (`version=1`).
5. `python -c "import api.main"` clean (migration registered) · `npm run build` clean.
   Max shoots one idea as `raw-talking-head` or `beat-edit` and it feels natural (the real test).

---

## Part A — §4 Production Tiers

### A1. Tier plumbing (backend, no new module)

Tier is already a column on `ideas` (`notion_page_id`/`pillar`/`tier`/`channels` landed in §3).
Thread it into reel generation:

- `ideas/routes.py::generate_reel` — load the idea (already does), pass `tier = idea.tier or "scripted-headshot"` into the enqueued payload:
  ```python
  job_id = jobs_queue.enqueue("generate_reel_script", {
      "idea_id": idea_id,
      "idea_prompt": idea_prompt,
      "tier": idea.tier or "scripted-headshot",   # NEW
      ...
  })
  ```
- `jobs/handlers.py::_handle_generate_reel` — read `payload.get("tier", "scripted-headshot")`
  and pass to `script_writer.build_freeform_script_prompt(idea_prompt, framework, tier=tier)`.
  One-off reels (Reels tab, no idea) pass no tier → default.

### A2. Prompt template selection (`script_writer.py`)

`build_freeform_script_prompt(idea_prompt, framework)` currently hardcodes
`IDEA_PROMPT_PATH = prompts/script_writer_idea.txt`. Add a tier→template map and a `tier` arg:

```python
TIER_TEMPLATES = {
    "scripted-headshot": PROMPTS_DIR / "script_writer_idea.txt",   # existing, unchanged
    "raw-talking-head":  PROMPTS_DIR / "script_writer_raw.txt",    # new
    "beat-edit":         PROMPTS_DIR / "script_writer_beat.txt",   # new
}

def build_freeform_script_prompt(idea_prompt, framework, tier="scripted-headshot"):
    template_path = TIER_TEMPLATES.get(tier, TIER_TEMPLATES["scripted-headshot"])
    template = template_path.read_text(encoding="utf-8")
    voice_block = VOICE_BLOCK_PATH.read_text(encoding="utf-8")
    ...  # rest unchanged — same voice injection + framework fill
```

All three templates inject `voice_dna_block.txt` v2 exactly as the existing path does.
Store the resolved tier on the row (see A4) so Studio can badge it and so re-generation reuses it.

### A3. The two new templates

**`script_writer_raw.txt`** — from the PRD description. Output contract:
- A natural spoken **opening line** (one sentence, in Max's register — the hook he actually says).
- **3–6 talking points** as bullets, NOT sentences to read verbatim — cues he riffs off.
- A one-line **closer/CTA** cue.
- Explicitly instruct: this is NOT a word-for-word script; keep it loose enough to feel unscripted.

**`script_writer_beat.txt`** — grounded in `beatedit.MP4`. **Before writing this template,
re-extract reference frames** (scratchpad frames are session-scoped and won't survive):
```bash
SRC="frameworks/instagram_frameworks/references/beatedit.MP4"
ffmpeg -v error -i "$SRC" -vf "fps=1/2,scale=360:-1" /tmp/beat_%02d.jpg   # ~16 frames
# view them with the Read tool (native vision) — read the on-screen text + shot types directly
```
Reference grammar observed (32s vertical 720×1280, 25fps, music-only, no VO, `@NKIRKNZ`):
- **Hook beat:** wide performance shot + giant red/white kinetic headline ("Running's a lot like Dance").
- **Content beats:** alternate wide-performance and tight macro cutaways (legs/shoes on wet pavement),
  one short coaching cue per beat ("Don't lift up & down"), consistent red/white type system.
- Cinematic grade, music-driven pacing, ~1 text beat per shot.

Output contract for the template — an **ordered beat list**, each beat:
- `shot:` (wide / macro / detail — what's on screen)
- `text:` (the short on-screen overlay, punchy, ≤5 words)
- `beat:` (pacing note — cut on beat / hold / transition)
Minimal or zero spoken words. Inject `voice_dna_block.txt` for the text-overlay voice.
Keep it a shootable shot list, not prose.

### A4. Store tier on the reel row

Add `tier TEXT` to `reel_scripts` (via `script_writer.init_db` try/except ALTER pattern,
mirroring `framework_pick_reason`). `save_script(...)` gains a `tier` param, persists it.
Lets Studio badge the tier and lets regenerate default to the same tier. Backfill NULL → treat
as `scripted-headshot` at read time.

### A5. Frontend — tier picker + badge

- `IdeaDetail.jsx`: tier `<select>` (`scripted-headshot` / `raw-talking-head` / `beat-edit`),
  writes via a small `PATCH /ideas/{id}` extension or a dedicated `PATCH /ideas/{id}/tier`.
  Show current tier; default display `scripted-headshot` when null. **Editable even for
  Notion-linked ideas** (tier is a PBS-side production decision; content stays read-only).
- `IdeasTab.jsx`: tier badge on idea rows (alongside the existing pillar/channel badges).
- `lib/ideasApi.js`: `setIdeaTier(ideaId, tier)`.

Business logic stays server-side; UI only sends the chosen tier + renders badges.

---

## Part B — §5 Reel Draft Versioning

### B1. Schema (`script_writer.init_db`, additive)

```sql
ALTER TABLE reel_scripts ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE reel_scripts ADD COLUMN parent_script_id INTEGER;   -- root of the version chain
```
Backfill: existing rows keep `version=1`, `parent_script_id=NULL`. **Version family = all
`reel_scripts` sharing an `idea_id`.** One-off reels (`idea_id IS NULL`) are always their own
family of one — never versioned/grouped.

### B2. Version assignment on generate (`_handle_generate_reel`)

When `idea_id` is set, before `save_script`:
```python
row = conn.execute(
    "SELECT id, MAX(version) AS v FROM reel_scripts WHERE idea_id = ?", (idea_id,)
).fetchone()
if row and row["v"]:
    version = row["v"] + 1
    parent_script_id = row["id"]      # immediate prior live row
else:
    version, parent_script_id = 1, None
```
Pass `version` + `parent_script_id` into `save_script`. No prior row is mutated — history is
implicit in the `version` ordering (no `superseded` flag needed).

### B3. Live-version resolution + status derivation

- **Live version** per idea = the row with `MAX(version)` among non-killed rows for that
  `idea_id`. If the live version is killed, the next-highest non-killed becomes live
  ("kill this take, fall back to the previous").
- `ideas/repository.py::derive_idea_status` — the `reel_scripts` leg of the UNION must count
  **only the live version's status**, not every version. Otherwise a superseded `approved` v1
  keeps the idea `approved` after regenerating a fresh `queued` v2. Replace the flat
  `SELECT status FROM reel_scripts WHERE idea_id = ?` with a live-version subquery:
  ```sql
  SELECT status FROM reel_scripts
  WHERE idea_id = ? AND status != 'killed'
  ORDER BY version DESC LIMIT 1
  ```
  (If all reel versions are killed, contribute `killed`, consistent with the existing all-killed rule.)

### B4. Studio board — live card + history expander

- `NOTION DIARY FETCHER/api/reel_routes.py::list_scripts` — return **only live versions** for
  idea-linked scripts (one card per idea), plus all one-off scripts. Include `version`,
  `idea_id`, `tier` in the payload. Keep `ORDER BY created_at DESC`.
- New endpoint `GET /reels/scripts/{id}/versions` → all rows sharing that script's `idea_id`,
  ordered `version DESC`, each with `id/version/status/created_at/model_used/generated_text`.
  For the history expander.
- `frontend/src/components/StudioTab.jsx` — `PipelineCard` for a versioned reel shows
  `v{n}` + tier badge and an expandable "history" list (older versions, read-only view) fetched
  from the versions endpoint. Approve/kill still act on the **live** row's `id` via the existing
  `PATCH /reels/{id}/meta` path (unchanged). Killing the live version re-derives live to the
  prior one on next fetch.
- `IdeaDetail.jsx` — a "Regenerate" action enqueues `generate_reel_script` with the idea's
  tier (same path as first generation); the new version appears as live on next poll. Prior
  versions listed read-only under the live draft (uses `get_idea_drafts`, which already returns
  all reel rows — add `version` to `IdeaDraft` so they render in order).

### B5. Models

- `ideas/models.py::IdeaDraft` — add `version: int = 1` (and surface `tier` if useful for badges).
- `get_idea_drafts` SELECTs — add `version` to the reel query; sort reels by `version DESC`
  within the idea (keep the cross-channel `created_at` sort for the merged list, or group by
  channel — reels grouped by version, LinkedIn as-is).

---

## Logic summary (model-agnostic flow)

```
generate reel for idea:
  tier   = idea.tier or "scripted-headshot"
  tmpl   = TIER_TEMPLATES[tier]
  prompt = fill(tmpl, idea_prompt, framework) + voice_dna_block + feedback_block
  v      = (max version for idea_id) + 1   |  1 if none
  parent = prior live row id               |  None
  save_script(..., tier, version=v, parent_script_id=parent)
  push_notion_status(idea_id)              # unchanged §3 trigger

idea status:
  live reel status = status of MAX(version) non-killed row per idea
  derive_idea_status unions content_drafts + live-reel-status  (all-killed -> killed)

studio board:
  cards   = live reel versions (one per idea) + one-off reels
  history = GET /reels/scripts/{id}/versions  (expand)
  approve/kill -> live row id (existing meta path)
```

## Affected files

| File | Change |
|------|--------|
| `frameworks/instagram_frameworks/script_writer.py` | `TIER_TEMPLATES` map, `tier` arg on `build_freeform_script_prompt`; `init_db` ALTERs (`tier`, `version`, `parent_script_id`); `save_script` gains `tier`/`version`/`parent_script_id` |
| `frameworks/instagram_frameworks/prompts/script_writer_raw.txt` | **NEW** — talking-points template |
| `frameworks/instagram_frameworks/prompts/script_writer_beat.txt` | **NEW** — beat-list template, grounded in `beatedit.MP4` |
| `jobs/handlers.py::_handle_generate_reel` | read `tier`, compute `version`/`parent_script_id`, pass through |
| `ideas/routes.py::generate_reel` (+ tier PATCH) | pass tier into payload; `PATCH /ideas/{id}/tier` |
| `ideas/repository.py` | `derive_idea_status` live-version subquery; `get_idea_drafts` returns `version`; `set_idea_tier` |
| `ideas/models.py::IdeaDraft` | `version` field |
| `NOTION DIARY FETCHER/api/reel_routes.py` | `list_scripts` returns live versions + `version`/`tier`/`idea_id`; new `GET /reels/scripts/{id}/versions` |
| `frontend/src/components/IdeaDetail.jsx` | tier picker, regenerate, version history read-only |
| `frontend/src/components/IdeasTab.jsx` | tier badge |
| `frontend/src/components/StudioTab.jsx` | `v{n}` + tier badge, history expander |
| `frontend/src/lib/ideasApi.js` | `setIdeaTier`, versions fetch |

## Out of scope (unchanged from PRD)

LinkedIn versioning · §7 VM deploy + scheduled automation (next after Max tests this) ·
§8 insight-helper doc · pushing local ideas to Notion · tier-specific OpenMontage handoff ·
stale `yaml_path` pass · rotating the leaked OpenRouter key (Max's follow-up).

## Verification (Sonnet, before handoff)

1. `python -c "import api.main"` clean (migration + new route registered).
2. Generate a reel for an idea at each tier → 3 visibly different output shapes; confirm
   `tier`/`version` persisted on the row.
3. Regenerate the same idea → `version=2`, `parent_script_id` set, live card updates, v1 in
   history, idea status follows the live version (not the stale v1).
4. Kill the live version → prior version becomes live on next fetch; idea status re-derives.
5. One-off reel (Reels tab, no idea) + a LinkedIn draft → unchanged.
6. `npm run build` clean.

## Handoff note (model routing)

Execution → Sonnet 5 per CLAUDE.md routing. Suggested sequence: A1–A2 plumbing → A3 write the
two templates (extract `beatedit.MP4` frames first, view them, then author `script_writer_beat.txt`)
→ A4–A5 tier storage + UI → B1–B3 versioning schema/logic → B4–B5 Studio + IdeaDetail history →
verification. No sub-agents needed. Update root `md/checkpoint.md` + `md/code_index.md` when done.
