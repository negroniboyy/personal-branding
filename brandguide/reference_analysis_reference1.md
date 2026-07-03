# Reference Reel Analysis — `reference1.MP4` (via OpenMontage)

**Source:** `frameworks/instagram_frameworks/references/reference1.MP4` · **Analyzed:** 2026-07-02
**Tool:** OpenMontage `video_analyzer` (+ manual vision pass on keyframes, per `skills/meta/video-reference-analyst.md`) + `openai-whisper` (base) for transcript, since OpenMontage's env doesn't have `faster-whisper` installed.

This is a test run answering: *what can OpenMontage's reference-analysis actually extract from one of our reels, and how much richer is it than the extractor we already have in `frameworks/instagram_frameworks/`?*

---

## 1. What OpenMontage extracted (raw capability)

Ran `video_analyzer.execute({"source": "reference1.MP4", "analysis_depth": "standard", "max_keyframes": 20})`.

| Layer | Result |
|---|---|
| Metadata | 720×1280, HEVC, 30fps, 58.0s, 108MB (confirmed via `ffprobe`) |
| Scene detection | 17 scenes, ffmpeg content-based cuts |
| Motion classification | Ran, but returned `motion_type: "unknown"` for every scene — **not reliable on this input**, see Limitations |
| Keyframes | 20 extracted, evenly spread across scenes |
| Audio energy | Ran (`has_energy_data: true`), no anomalies flagged |
| Transcript | **Not available** — OpenMontage's `transcriber` tool is `status: unavailable` in this environment (needs `faster-whisper`, not installed). Pulled a transcript manually via `openai-whisper` from `personal_brand`'s own venv instead (see §3). |
| Content/style auto-fill (`content_analysis`, `style_profile`) | **Empty by default.** The tool only produces the skeleton (scenes, timestamps, keyframe paths) — the actual content/style description is supposed to come from the agent's own vision pass over the keyframes, per the skill's protocol. I did that pass manually below. |
| Auto-suggested pipeline | `animated-explainer` / `flat-motion-graphics` — **wrong.** This is a straight talking-head selfie vlog; the correct OpenMontage pipeline is `talking-head` or `hybrid`. The heuristic misfires on short, cut-heavy, face-forward footage — don't trust this field blindly, treat it as a hint at most. |

**Limitation worth flagging back to OpenMontage:** `_analysis_meta.duration_seconds` reported `11.77`, while `ffprobe` and the `source` block both correctly say `58.0`. There's an internal duration-calc discrepancy in the standard-depth path — cosmetic here (didn't affect scene/keyframe extraction), but worth a bug note if you rely on that field elsewhere.

---

## 2. What our own extractor (`frameworks/instagram_frameworks/extract_reel.py`) would have given you

For comparison — this is the tool already in `personal_brand`:

| Capability | `extract_reel.py` (ours) | OpenMontage `video_analyzer` |
|---|---|---|
| Transcript (Whisper) + timestamped segments | ✅ Yes (via Ollama LLM structuring) | ❌ Needs a separate install; falls back to nothing |
| Hook type / CTA type / tone (LLM-classified) | ✅ Yes, structured YAML (`hook.type`, `cta.type`, `tone`) | ❌ Not classified — you have to read the transcript yourself |
| Scene cuts / pacing (cuts-per-second) | ✅ Yes (PySceneDetect) | ✅ Yes (ffmpeg content detection) — comparable |
| **Visual content** (what's actually on screen, location, wardrobe, framing) | ❌ None — `visual_notes` field exists but is explicitly "LLM never writes here; fill manually" | ✅ Keyframes + agent vision pass — this is the whole point of OpenMontage here |
| **Typography / on-screen text style** | ❌ Not captured | ✅ Captured via vision pass (see §3 — two distinct caption fonts found) |
| **Color grade / mood** | ❌ Not captured | ✅ Captured via vision pass |
| Output format | Structured YAML → SQLite (`reel_frameworks` table), fits directly into `script_writer.py`'s framework picker | Structured JSON blob (`VideoAnalysisBrief`), not wired into personal_brand's DB |

**Bottom line:** our extractor is the better *transcript/structure* tool — it's already LLM-classified and lands directly in the DB frameworks that `script_writer.py` picks from. OpenMontage is the better *visual* tool — it's the layer we're missing entirely today (location, wardrobe/continuity, color grade, caption typography, cut rhythm against picture not just audio). They're complementary, not competing. See §5 for how to combine them without duplicating work.

---

## 3. Full breakdown of `reference1.MP4`

**Creator:** @its.normss · **Runtime:** 58s · **Format:** vertical talking-head selfie/handheld, cut across 4 micro-locations in the same home (bedroom doorway hiding-in-closet cold open, desk with bookshelf, bedroom, hallway, living room).

### Content summary
A **meta reel about reel-writing technique** — not a story about his life, a direct-to-camera breakdown of one scriptwriting device ("the curiosity gap"), using a deliberately provocative example line as bait, then breaking the fourth wall to explain the mechanism, then a comment-to-unlock CTA.

### Structure (5-aspect + beat timeline)

| Beat | Time | What happens | On-screen text |
|---|---|---|---|
| Cold open / hook | 0.0–7.6s | Extreme close, half-hidden face peeking through hanging clothes in a closet (teal light, mysterious framing) → cuts to desk, bold claim: *"I stole one storytelling secret from secular creators, 200x'd my audience off ~30 posts"* | `called:` |
| Tension / stakes | 8.1–14.3s | *"Why would anyone care about my story? They don't, and they never will — one exception"* | (spoken only) |
| The reveal / bait line | 14.8–26.8s | Delivers a deliberately heavy, provocative example sentence (about sin/damnation) as the demonstration of the technique — cut to a 2s dark B-roll insert (screwdriver, glowing LED) as a tension beat between location changes | `None` (label, ties to a "fill-in-the-blank" gag) |
| Mechanism explained | 28.8–43.0s | Direct name-drop: *"the curiosity gap, see what I did there"* — explains that every line gives just enough context to know where the video is going but not enough to spoil the payoff | `Come` + `*applause*` (secondary sound-effect font) |
| CTA | 43.0–53.2s | *"If you want to see how I actually used it, comment 'leap' for the breakdown"* | — |
| Outro / sign-off | 54.0–58.0s | Frame dims, IG logo re-shown as a branding sting, casual sign-off | `God bless!` |

- **Subject:** single subject (creator), consistent across all locations, wardrobe changes signal it's the same take stitched from multiple short setups, not one continuous shot.
- **Spatial framing:** tight CU/MCU throughout, phone-arm's-length selfie distance, occasional profile/three-quarter turn for movement energy. No wide shots — intimacy is the point.
- **Camera:** static-handheld (slight natural shake, no gimbal), no zooms, no rack focus — all the "production value" comes from cutting + grade + captions, not camera work.
- **Cadence:** 17 scenes / 58s ≈ **1 cut every 3.4s** on average, but front-loaded — the first 20s carries 5 cuts (fast, hooky) vs. the back half settling into longer holds during the explanation beat. Classic "hook fast, explain slow" pacing.

### Visual style
- **Color grade:** cinematic teal-shadow / warm-highlight split-tone (teal in darks/skin-shadow, orange/amber in practical light sources) — consistent across every location, meaning it's a LUT or preset applied in post, not natural lighting.
- **Typography:** two distinct caption systems in play —
  1. **Primary dialogue captions** — serif italic, cream/off-white, word-by-word or short-phrase reveal, centered, no background box. Used for the spoken script.
  2. **Secondary SFX/aside captions** — a separate playful script/handwritten font (e.g. `*applause*`) — used to annotate a joke or a beat the audio doesn't literally say. This is a **second layer** most creators skip; it's doing comedic/meta work.
- **Branding:** persistent small IG logo + `@its.normss` handle, top-right, low-opacity — never distracting, always present (a repost/steal-proofing habit worth noting).
- **Outro treatment:** the final frame dims (not a hard cut to black) with the sign-off text overlaid on the darkened live frame — cheap to produce, reads as intentional.

### CTA
Type: **comment-to-unlock** ("comment 'leap' for the breakdown") — an engagement-bait mechanic, not a link/DM ask.

---

## 4. Suggestions, filtered through `brandguide/`

Running this against `voice_dna.md`'s decision filter and `brandbook.md`'s positioning (identity-first, reflective, not performative, not motivational) — here's what to steal, adapt, or reject.

### ✅ Structural technique worth stealing (adapt, don't copy)
The **curiosity-gap mechanism itself** ("give enough context to know where it's going, not enough to spoil the payoff") is not a gimmick — it's literally the same principle already encoded in `voice_dna.md`'s storytelling structure: *"Context without over-explaining"* + *"The real problem, named plainly."* This reel just makes that principle explicit and teaches it. That's a legitimate content angle for Max: **a builder-in-public reel about a technique he's using in his own system** — which is exactly `campaign_01_builder_in_public.md`'s anchor. Meta-commentary about *how the content itself is built* fits the campaign's "builder who builds in public" premise directly.

### ✅ Visual mechanic worth adopting
- **Two-tier caption typography** (spoken-word serif vs. an aside/SFX font) is cheap to replicate in Remotion/HyperFrames and gives a reel more texture without adding performance energy — it doesn't conflict with Max's "not performative" rule because it's a craft choice, not a persona.
- **Front-loaded cut pacing** (fast hook, settle into longer holds once you're explaining) matches `voice_dna.md`'s "slower opening hook, builds into conflict, clean pivot" instruction for Reels almost exactly — good evidence the pacing target we already wrote down is directionally right.

### ❌ Reject or rewrite before use
- **The bait line itself** (using a deliberately heavy/manipulative statement purely to shock) — this is "manufactured performance," fails filter question 1 (*"a real observation or a manufactured performance?"*) and question 3 (*"sounds like someone trying to sound smart"*). If Max does a curiosity-gap example, it needs to be a real thing he actually thought or noticed, not an engineered shock line.
- **"200x'd my audience"-style flex opener** — directly the kind of claim `voice_dna.md`'s "words he never uses" section rules out (adjacent to "Crushing it" / "Game-changer" energy). Any version of this angle should open with the honest-opening pattern instead: *"I built something I was actually proud of. Then I noticed everyone skips the same line."* — same structural beat, none of the flex.
- **Comment-to-unlock CTA** — `voice_dna.md` is explicit: Reels get **no on-screen CTA unless it's a natural question** ("Anyone else hit this wall?"). "Comment X for the breakdown" is an engagement-bait CTA type the brandguide already rules out — don't adopt the mechanic even though it's proven; it's the wrong tone for this brand.
- **Persistent handle watermark styling** — fine as an anti-repost habit, optional, not a voice issue either way.

### Suggested next content piece (if you want to run with this)
A short reel: *"I noticed my content pipeline uses the same trick every hook-writer uses — I just didn't know it had a name until I looked."* Structure: honest opening → what he noticed while building `personal_brand` (the curiosity-gap principle is already in `script_writer_idea.txt`'s voice rules) → self-aware pivot, no lecture → close on current honest state, no CTA (or, at most, a natural question). This turns the reference's *technique* into Max's *material*, without importing its tone.

---

## 5. How to actually combine the two tools (practical, not hypothetical)

Right now these live in two separate repos with no bridge. Given the gap table in §2, the useful integration is narrow and specific:

1. Keep `extract_reel.py` as the system of record for **hook/structure/pacing/tone/cta** — it already writes to `reel_frameworks` and `script_writer.py` reads from there. Don't duplicate that in OpenMontage.
2. Use OpenMontage's `video_analyzer` (this workflow) as a **manual, occasional supplement** when a reference reel's *visual* craft (color, typography, cut rhythm against picture, location/wardrobe use) is worth studying — write findings into `memory/reference_creators.md` or a one-off `brandguide/reference_analysis_<name>.md` like this one, not into the `reel_frameworks` DB schema (it has no columns for this today).
3. Don't build automated glue between the two pipelines yet — one test run took a handful of manual steps (whisper fallback, manual keyframe reading) that aren't worth scripting until this becomes a repeated weekly habit. If it does, that's a `handoff/blueprint_v[X.X]_openmontage_bridge.md` per the Blueprint Protocol — not an ad-hoc script.
