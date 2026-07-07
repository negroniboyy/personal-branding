# Why the drafts got so much better

_2026-07-03 · Written by Fable after cross-referencing `brandguide/voice_dna.md` v1 vs v2, the archived `content_strategy_log.md`, and the v3 reboot PRD. Every claim below is sourced from a real file in this repo, not general AI-prompting folklore._

## TL;DR

Three things changed, and they compound:

1. **The input got cleaner.** You went from "diary brain-vomit → auto-extracted story_node" to "you type one deliberate idea." This alone was the biggest single fix — it was already measured and logged (see below) *before* the reboot even happened.
2. **The voice model stopped being wrong.** v1's voice DNA wasn't just "less polished" than v2 — it was factually incorrect about your life. It assumed a struggle-and-lesson narrative arc you don't actually live, because it was statistically extracted from old writing instead of checked against you directly.
3. **The frameworks got a "shape, not content" rule + a rejection-feedback loop**, both of which existed before the reboot in embryonic form and are now load-bearing.

So: **yes, messy input was a real and measured cause — but it was not the only one.** A correct voice model fed messy input still degrades; a wrong voice model fed clean input still misses. You fixed both.

---

## 1. The input: diary vomit → curated idea

**Before:** `narrative_warehouse/stage1_extractor.py` scored raw Notion diary entries into `story_nodes` — a pipeline step that had no way to tell "this diary entry has enough real detail to write from" apart from "this is unstructured venting with no concrete anchors." Both got extracted as equally valid story material.

**The evidence this mattered, found in your own archived logs** (`brandguide/_archive/content_strategy_log.md`, an n=3 test across fitness / imposter-syndrome / Japanese-learning story nodes):

> "★ Fabrication is governed by SOURCE CONCRETENESS, not the framework. *(Confidence: high — clean signal across n=3.)* Rich source story (fitness: runner friends, plyometrics, named injury) → near-zero fabrication. Thin/abstract source (Japanese) → every draft invented routine specifics ('90 min/night', 'clients replied faster', 'coworkers noticed')."

That's a controlled, repeated observation, not a guess: the same prompt, the same frameworks, the same voice DNA — only the concreteness of the source material changed, and fabrication went from ~zero to "every draft invents details." A thin/abstract idea forces the model to fabricate because it has a length and specificity target to hit and nothing real to fill it with.

**Now:** you type the idea directly in the Ideas tab. It's short, but it's *yours* and *deliberate* — not a diary entry auto-scored for "narrative potential" by an extraction script that can't tell real specificity from rambling.

**The generalizable lesson:** *specificity in, specificity out* is not a platitude here — it was measured. If you want a clean draft, the idea prompt itself needs at least 2–3 concrete, real anchors (a name, a number, a place, an actual thing that happened). If the idea is abstract ("I've been thinking about ego lately"), the model has no honest way to reach a full-length structured output — it *will* invent the missing concreteness rather than write something honestly short.

---

## 2. The voice model: not just "better," previously *wrong*

This is the part worth sitting with, because it's not the story of "we polished v1." Read the actual disclaimer at the top of the current file (`brandguide/voice_dna.md`):

> "v1 (extracted from diary/story_nodes) was rejected wholesale as badly hard-coded... The single most important correction from v1: **do not manufacture crisis.** His life is going well and he says so. The tension in his content is not 'I failed and learned' — it is *pace*, *comparison*, and *fine lines*. Forced vulnerability reads instantly fake on him and is why the old drafts never got shot."

v1 was built by **extracting patterns from your raw writing** — vocabulary lists, sentence rhythms, a 6-step "storytelling structure" that assumed every piece needed a struggle → realization → resolution arc. That structure is a genuinely common narrative template, so the extraction *looked* reasonable. It was just wrong for you: your actual register right now is a "momentum season" — grateful, capable, impatient — not a struggle-story protagonist. A voice model built by pattern-mining old text will confidently reproduce whatever arc dominates the sample, correct or not, because nothing in that process asks "does this match reality" — it only asks "does this match the training text."

v2 was built **by interview** — you were asked directly, and the resulting file cites your actual sentences as evidence for each claim, not an inferred pattern. Compare the source-of-truth style:

- v1: *"Storytelling structure: All Max's pieces follow the same underlying arc..."* — a rule inferred from output.
- v2: *"I am very grateful for having taken the steps needed to get to where I am right now."* — a rule *quoted from you*, with the file explicitly noting it was built "from live interview + fresh writing samples Max provided himself."

**The generalizable lesson:** if you ask a model to imitate "your voice" by mining old content, it will find *a* pattern — but a pattern is not the same as truth, and nothing in that pipeline checks whether the pattern is still accurate to how you actually feel right now. **Voice/identity briefs should be interview-derived (you stating things directly) whenever a model will be asked to speak *as* you**, not reverse-engineered from a sample of your writing, however large. Extraction finds correlation; it can't tell you if the correlation is a life-arc you're actually living or an artifact of which old posts happened to survive.

---

## 3. Frameworks as shape, not content — and a real feedback loop

Two structural things were already true before the reboot and are worth keeping in any future project:

**a) Explicit "shape, not subject" instructions in the prompt itself.** Look at `frameworks/instagram_frameworks/script_writer.py`'s `_format_framework()` — every framework example is injected with an inline warning:

```
Hook verbal (EXAMPLE from an UNRELATED topic — copy the SHAPE, never the subject): ...
Structure (SHAPE template — its example topics/tools are from a DIFFERENT story;
never reuse them as content): ...
```

This one line stops a very specific, very common failure mode: a framework example about "a weather bot" bleeding its *content* (not just its structure) into an unrelated draft. Your own strategy log caught exactly this before: `ref1-bold_claim` (a long, 30+-scene framework) kept inventing "weather bot", "Raspberry Pi", `import requests` — not because the source story mentioned any of that, but because the framework's own example text leaked in as if it were real. **Longer, more detail-hungry templates are riskier for this** — a 40-second framework with 4 beats has less room to leak; a 70-second one with 30 scene-beats has to fill a lot of space and will reach for the nearest available words, which are the framework's own examples.

**The generalizable lesson:** when you give a model a structural template with worked examples, say explicitly — in the prompt, every time — "copy the shape, never the content of this example." Without that line, models default to pattern-completing the example's *content*, not just its structure, especially under length pressure.

**b) A live rejection loop, not a static prompt.** `shared/shared/lifecycle.py`'s `get_feedback_block()` pulls your own `verdict_note` from previously-killed drafts and injects it into the next generation call as an explicit "avoid this" signal. This means the system's idea of "good" isn't frozen at whatever the prompt said on day one — every reject you log with a reason becomes training signal for the next batch. This is a different (and cheaper) mechanism than fine-tuning, but it does the same job: closing the loop between your actual judgment and what gets generated next.

**The generalizable lesson:** if you're running any repeated generation loop, always capture *why* something was rejected in a structured, reusable place, and feed it back into the next prompt. A one-shot prompt that never learns from your verdicts will keep making the same category of mistake indefinitely.

---

## 4. What you were doing wrong before (direct answer)

Not "wrong" in the sense of a mistake you should feel bad about — this is exactly the kind of thing that's invisible until you've shipped enough drafts to see the pattern. Concretely, three separable things were happening at once:

1. **You let the model infer your voice from a writing sample instead of stating it.** Extraction-based voice models will always find *some* pattern; they can't tell you whether it's still true. If a model needs to sound like you, tell it who you are directly — don't hand it your archive and hope it reverse-engineers the right conclusion.
2. **The input pipeline didn't distinguish real specificity from raw volume.** More diary text isn't more useful material — a single concrete anecdote outperforms a page of unstructured reflection, because the model can't invent what it doesn't have, but it *will* invent what it's missing when the structure demands it.
3. **Long, detail-hungry framework templates were used on thin source material.** The fix your own log already proposed — "restrict thin nodes to the fabrication-resistant frameworks" — is a version of a broader rule: match the ambition of the output format to the richness of the input. Don't ask for a 70-second, 30-scene script from a one-line idea.

None of these are about "prompting harder" — they're about giving the model true, sufficient, and correctly-scoped material, which is the actual lever every time.

---

## 5. A checklist for future projects

When you start a new content/voice-driven project, in order:

1. **Get the identity/voice brief from the person directly** (interview, direct Q&A, or their own unedited writing samples quoted verbatim) — never from statistical extraction over a large corpus with no ground-truth check.
2. **Demand concreteness at the input stage**, not the output stage. A short idea with 2–3 real anchors (names, numbers, specific events) beats a long, vague brain-dump every time. If the input is thin, either enrich it before generating or explicitly request a shorter/less detail-hungry output — don't ask a verbose format to fabricate its way to length.
3. **If using structural templates/frameworks with worked examples, explicitly instruct "copy shape, not content"** in the prompt itself, every time an example is shown. Assume the model will otherwise leak the example's content.
4. **Build a real rejection-feedback loop** from day one: capture why something was killed, in a structured place, and feed it into the next generation call. Don't let "good" stay defined by the first prompt you wrote.
5. **Match format ambition to input richness.** Long-form, highly-structured outputs need rich, specific source material. Thin source material should produce short, conceptual output — not get padded to match a template's length requirement.
