# Blueprint v2.7 — Voice-aware generation for the Ideas tab (freeform paths)

## State

**Problem.** The Ideas tab generates content, but through **voiceless** prompt builders:
- Reel → `script_writer.build_freeform_script_prompt` (generic "you are a scriptwriter").
- LinkedIn → `content_writer.prompt_builder.build_freeform_prompt` (framework mechanics only).

The creator's real voice logic (VOICE DNA, six CRAFT MOVES, transformation example, foil-hook /
meta-payoff / no-sell close) lives ONLY in the reel **story-node** template
`frameworks/instagram_frameworks/prompts/script_writer.txt`. The Ideas tab never touches it.

That template is also wrong as-is for ideas: its RULE 0 ("SELECT, DON'T SUMMARIZE… messy
brain-vomit… aggressively ignore everything else") assumes raw diary dumps. Ideas-tab input is the
opposite — an already-refined, single-thread insight written by the creator.

**Key leverage.** The two freeform builders are the **shared entry point for every free-text-idea
path**, so upgrading them in place fixes the Ideas tab AND both Writer tabs' freeform modes with no
route changes:
| Builder | Callers (all use free-text idea, story_node_id = None) |
|---|---|
| `build_freeform_script_prompt` | `ideas/routes.py:180`, `NOTION DIARY FETCHER/api/reel_routes.py:145,226` |
| `build_freeform_prompt` | `content_writer/service.py:74` (Ideas tab LinkedIn + LinkedIn Writer freeform) |

**Affected files**
- NEW `brandguide/voice_dna_block.txt` — single source of truth for the shared voice kit.
- EDIT `frameworks/instagram_frameworks/prompts/script_writer_idea.txt` — NEW reel idea template.
- EDIT `frameworks/instagram_frameworks/script_writer.py` — enrich `build_freeform_script_prompt`.
- EDIT `content_writer/prompt_builder.py` — enrich `build_freeform_prompt`.
- UNCHANGED (this round): `script_writer.txt` (verified story path), `ideas/routes.py`,
  `reel_routes.py`, `content_writer/service.py` — they call the builders, signatures stay identical.

## Decisions (locked with user)
1. Scope = **both channels** (reel + LinkedIn).
2. Structure = **shared voice block** (one file, injected into both idea paths).
3. Framing = **idea-tuned**, NOT diary-tuned: "this is already your one refined insight — sharpen
   it, stay strictly inside its facts," replacing the diary "select one thread from a mess" rule.

## Logic (model-agnostic)

### A. Shared voice block — `brandguide/voice_dna_block.txt`
Extract **verbatim** from `script_writer.txt`:
- VOICE DNA (who's speaking / rhythm / words he uses / NEVER-write list / self-awareness / close).
- The six CRAFT MOVES (moves 1 & 5 required).
- The RAW→POLISHED transformation example.
Channel-specific OUTPUT FORMAT and structural rules stay in each template (NOT in the shared block),
because voiceover lines ≠ LinkedIn paragraphs.

### B. Loader (robust, no cross-package import risk)
Each builder reads the file via a path derived from its own `__file__` → repo root →
`brandguide/voice_dna_block.txt`, cached at module level. (Two ~4-line readers; the FILE is the
single source, the reader is trivial. Avoids this repo's fragile sys.path wiring between
`frameworks/instagram_frameworks/` and root packages.)

### C. Reel idea template — `prompts/script_writer_idea.txt`
```
You are a short-form video scriptwriter writing in the creator's own VOICE.

The IDEA below is already a refined, single-thread insight the creator wrote himself.
Do NOT hunt for a thread or discard parts of it — it is already the one idea.
Your job: render it as a Reel script in his voice, using the craft moves.
Stay strictly inside the idea's facts — invent nothing beyond it.

{{VOICE_BLOCK}}                      # injected from brandguide/voice_dna_block.txt

**OUTPUT FORMAT — plain voiceover text only, no labels/headers.** (same as script_writer.txt 33-44)

**RULES (idea version):**
- The IDEA is the entire source of truth. Every concrete detail must trace to it.
- Hook = framework hook TYPE, content from the idea (never the framework's example subject).
- Duration / scene count / pacing / tone from FRAMEWORK, filtered through VOICE DNA.
- CTA = shape hint only; NEVER "DM me / link in bio / comment below"; default to honest current state.
- Apply craft moves 1 (foil hook) & 5 (meta-payoff) — required.

FRAMEWORK (shape only; its example topics are a different story):
{{FRAMEWORK}}

IDEA (the entire source material — write from it):
{{IDEA}}
```
`build_freeform_script_prompt(idea_prompt, framework)` → load template + voice block →
`llm_client.inject(template, VOICE_BLOCK=..., FRAMEWORK=_format_framework(fw), IDEA=idea_prompt)`.
Signature unchanged. `generate_script` still runs `clean_script_output` (strips any stray labels).

### D. LinkedIn idea path — `build_freeform_prompt(idea_prompt, framework)`
Build the string as today, but:
- Prepend the shared voice block (read from the same file).
- Add idea framing: "The source material IS the creator's refined insight — sharpen it in his voice,
  do not replace or pad it."
- Resolve the CTA tension the way the reel template does: framework CTA is a SHAPE hint, filtered
  through VOICE DNA → no "DM me / link in bio / comment below / follow"; prefer one honest question
  or his current state.
- Keep existing constraints: ≤1300 chars, whitespace between paragraphs, output the post only.
`service.generate_draft` already appends `get_feedback_block(conn, "content_drafts")` → verdict
feedback continues to apply on the LinkedIn idea path automatically.

## Specs
- Python 3.12 (uv). No new deps. Reuse `llm_client.inject`, `_format_framework`.
- Logic stays out of UI; routes/services untouched.
- Model routing unchanged — both paths keep their current `section`/router config.

## Out of scope (noted follow-ups)
- Migrating `script_writer.txt` (verified story path) to also inject `{{VOICE_BLOCK}}` for full
  de-dup. Deferred to avoid touching the verified path; the shared file is extracted verbatim from
  it, so they start identical.
- Verdict-feedback parity on the **reel** idea path (reel freeform builders take no `conn`; LinkedIn
  already has it). Would require a small route-level change.
- Note-rotation does not apply to ideas (user-authored, not mined) — N/A.

## Definition of Done
1. `brandguide/voice_dna_block.txt` exists; content matches the VOICE DNA + CRAFT MOVES +
   TRANSFORMATION sections of `script_writer.txt` verbatim.
2. Generating a Reel from an Idea (e.g. the OpenRouter insight) yields a script with: a foil hook,
   at least one antithesis, one personal admission, a meta-payoff near the end, a no-sell close, and
   ZERO invented facts beyond the idea. No "I'm excited to share / game-changer / DM me".
3. Generating a LinkedIn post from the same Idea shows the same voice markers and ≤1300 chars.
4. Reels tab freeform + LinkedIn Writer freeform produce the same voice (shared builders) — spot check.
5. Builder signatures unchanged; `clean_script_output` still applied to reel output.

## Handoff
Planning done on Opus. **Execution → Sonnet** (zero-verbosity, diffs only) per CLAUDE.md §1.
Generation itself must run on Max's machine (sandbox blocks OpenRouter SOCKS) — verify by generating
one reel + one LinkedIn from a real idea locally.
