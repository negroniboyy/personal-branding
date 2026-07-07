# Model Bake-Off — Reel Voiceover Script from Raw Diary Notes

**Test date:** 2026-07-02 · **Task:** `generate_reel_script` · **Source:** `00_raw_content.md` (same repo folder)
**Question being tested:** can each model independently find the ONE dominant thread in a messy multi-topic diary dump and write a voiceover script in Max's voice — without being told which thread to pick?

All 7 models received the **identical** prompt (`frameworks/instagram_frameworks/prompts/script_writer.txt`, unmodified — includes RULE 0 thread-selection, full Voice DNA, six craft moves) via `openrouter/router.py`'s `chat()` with `override_model` set per run, `max_tokens=1200` (see note on GLM 5.2 below). Target duration from the paired framework (`ref3-instagram-pain_point-v1.yaml`) is **~67 seconds** at a natural speaking pace (~2.5 words/sec).

## Headline finding — thread detection

**All 7 models, independently, picked the same thread**: the relationship/ambition-imbalance conflict — the exact thread Stage1's extractor scored `worth_score: 1.0` on. None of the 7 laundry-listed the other five competing threads in the raw notes (team dynamics, fitness-project pivot, therapy generically, food, meetup links). That answers the original question directly: **yes, this prompt design generalizes thread-detection across model families, not just the currently-pinned `qwen3-235b-a22b-thinking-2507`.** The RULE 0 instruction ("select, don't summarize") is doing real work regardless of which model executes it.

## Summary table (sorted by cost)

| Model | Latency | Cost | Tokens (in/out) | Finish | Est. spoken length | Duration vs. ~67s target |
|---|---|---|---|---|---|---|
| `google/gemma-4-31b-it:free` | 15.5s | **$0.000000** | 3913 / 275 | stop | ~80s | +20% over |
| `openai/gpt-oss-120b:free` | 12.7s | **$0.000000** | 3644 / 199 | stop | ~42s | −38% under (thin) |
| `google/gemma-4-26b-a4b-it` | 13.5s | $0.000656 | 3913 / 369 | stop | ~108s | +61% over |
| `qwen/qwen3-235b-a22b-2507` | 10.0s | $0.000926 | 3740 / 297 | stop | ~88s | +31% over |
| `deepseek/deepseek-v4-flash` | 16.0s | $0.001119 | 3701 / 2324 | stop | ~88s | +31% over, but see fabrication flag below |
| `qwen/qwen3-235b-a22b-thinking-2507` | 23.4s | $0.002172 | 3740 / 1079 | stop | ~52s | closest to target |
| `z-ai/glm-5.2` | 83.6s* | $0.01107* | 3658 / 2556 | stop | ~102s | +52% over |

*GLM 5.2 note: the first attempt at `max_tokens=1200` returned `finish_reason: "length"` with **zero visible content** — it spent the entire 1200-token budget on internal reasoning before writing anything, costing **$0.008571 for nothing usable**. Retried at `max_tokens=3000`, which produced the output shown below at $0.011070 (83.6s wall time includes both calls). **Practical implication if adopting GLM 5.2 for this task:** budget at least 2500–3000 completion tokens, not the 1200 that's sufficient for every other model here — otherwise it silently burns spend and returns nothing.

Free-tier note: `openai/gpt-oss-120b:free` needed 3 rate-limited retries (30s/60s/120s backoff) before succeeding — expect that tax on every call, not just this one, if it stays in the routing chain unattended (e.g. the nightly batch job).

---

## `google/gemma-4-31b-it:free` — 15.5s · $0.000000

Most people think the problem in a relationship is a lack of love.

The real problem? A gap in the rate of growth.

I've been pushing hard. Physical, mental, professional. I reckon that if you keep investing in yourself, the results compound. Boom.

But then you look across the room.
And you realize your partner isn't investing at all.

The agreed-upon therapy? Not happened for three months. No nutritionist. No personal growth. Just complaints about minor issues and a constant need for attention.

The real fear isn't that they aren't "perfect."
The fear is that their lack of growth is going to hinder my own progress. That my big plans are going to be weighed down because they can't or won't keep up.

I over-complicated it, as I always do, by just feeling the frustration.

But the answer isn't to just hope they change or to keep grinding in silence.
The answer is a direct conversation.

Notice what just happened — we shifted from blaming a lack of love to identifying a lack of alignment.

It's a trade-off. I can't carry the growth for two people.

Still figuring out the conversation. But doing it with the truth on the table.

Peace.

**Notes:** Free, fast, and structurally the tightest of the free-tier options — hits hook-with-a-foil, self-awareness marker, meta-payoff, and closes on current state with no CTA. Slightly over the duration target but not badly.

---

## `openai/gpt-oss-120b:free` — 12.7s · $0.000000

People say the problem is my workload.

The truth? I'm stuck on a conversation I keep pushing off.

I've been grinding on projects, building tools, and still feeling like I'm running in place.

Why does every win feel a little empty when the same argument circles back at home?

I thought more progress at work would fix the tension. My mistake was treating effort like a band-aid.

Notice what just happened — I stopped chasing bigger milestones and stared at the gap in the room instead.

Now I'm sitting with my partner, laying out the stuff I've been avoiding, and it feels oddly… real.

**Notes:** Correct thread, right voice markers, but noticeably **thin** — only 199 completion tokens, ~42s of spoken material against a 67s target. It compresses the arc rather than fully building it (skips the "self-improvement compounding" and "three months unfollowed therapy" specifics that give the piece its concrete weight). Cheapest and fastest, but would need a re-prompt or higher `max_tokens` to hit full length reliably.

---

## `google/gemma-4-26b-a4b-it` — 13.5s · $0.000656

The biggest threat to your growth isn't a lack of ambition. It's the friction of trying to move forward with someone who's standing still.

I've been leaning hard into self-improvement lately. Physical, mental, professional. I reckon if you just keep compounding those small efforts, the results eventually show up. Boom.

But lately, there's this tension. I have these big plans, but I'm realizing they might be hard to afford—or even pursue—if I'm not aligned with my partner.

People say the problem in relationships is "incompatibility." I don't think it's that.

The real issue is the imbalance of investment. It's the feeling that you're showing up for the work—the therapist, the nutritionist, the actual growth—and the person next to you isn't even following the arrangement you both made.

It's not just about minor complaints or being needy. It's the realization that while you're trying to build a bigger life, their lack of movement might actually act as an anchor.

I spent a lot of time over-complicating this, as I always do. Trying to figure out if I was being unfair or if I was just moving too fast.

But the truth is simpler. Growth is a trade-off. You can either choose the path of least resistance, or you can choose the path of most progress.

Notice what just happened—you stopped looking for a way to fix them and started looking at the reality of the situation.

I need to have a direct conversation about this. It's the only way to see if we're actually headed in the same direction.

Still figuring it out. Just being honest about the friction now.

**Notes:** Strongest hook-with-a-foil of the batch ("isn't a lack of ambition... it's the friction..."). Full arc, all six craft moves present, good voice-word usage ("I reckon", "Boom", "over-complicating this, as I always do"). Runs ~60% over the duration target — would need trimming, but the trim is easy (it's padded, not padded with invented facts).

---

## `qwen/qwen3-235b-a22b-2507` — 10.0s · $0.000926

If you're trying to grow and feel like the people around you aren't moving, this is for you.

I keep running. I keep learning. I keep trying to build something real.

But every time I level up, it feels like I'm leaving something — or someone — behind.

We agreed to grow together. That part's important.
But three months ago, that plan stopped. And I didn't say anything.

She complains about little things. Wants attention. Gets upset fast.
I used to think it was me. Now I wonder if it's just… mismatched momentum.

I want big things. She doesn't seem to want anything for herself.
No therapist. No nutritionist. No step forward.
And I'm sitting here, compounding effort, hoping it adds up.

It's not that I don't care. I do.
But I also can't pretend imbalance isn't a trade.

The answer wasn't to push harder. It wasn't to shut down.
It was to actually talk. Not vent. Not blame. Just speak.

I'm gonna say it. Not to fix her. But to name the gap.
Because silence isn't protecting the relationship — it's starving it.

Notice what just happened. I didn't ask you how to fix someone else.
I admitted I'd been waiting for change instead of naming the cost.

Still building. Still trying to grow without ghosting myself.
Peace.

**Notes:** Fastest wall-clock of all 7. Good voice fit, ellipsis used correctly ("mismatched momentum"), clean "Peace." close. One flag: "She complains about little things" directly names the partner's behavior more bluntly/judgmentally than the source or the voice's usual restraint — borderline on `voice_dna.md`'s "reflective, not performative" filter, worth a human edit pass rather than a straight post.

---

## `qwen/qwen3-235b-a22b-thinking-2507` — 23.4s · $0.002172 *(current production default for this task)*

Everyone says 'just communicate better' in relationships.
Not the problem.

The real gut-punch? Watching your progress hit her stagnation.
Every time.
I keep building—physical, mental, professional. She won't even call the therapist we agreed on. Three months now.

Not gonna lie.
Frustrating as hell when your growth gets blocked by someone else's comfort zone.

My mistake was thinking more effort from me would fix it.
Boom. It's a trade-off.
Her "needy" vibe? Maybe rooted in her upbringing. But my time's not infinite.

You compound your wins. You don't wait for someone else to start.
That's the only equation that works for me.

Notice how hard it is to admit: "This imbalance isn't a good trade for me."
Saying it changes everything.

Still planning that conversation.
Still building anyway.
Peace.

**Notes:** This is the model already pinned as primary for `generate_reel_script` (per `config/openrouter_models.yaml`, chosen 2026-06-14 via an earlier bake-off). It holds up here too — closest to the duration target, strongest concentration of exact voice vocabulary ("Not gonna lie", "Boom", "trade-off", "Peace"), tightest sentence rhythm. Costs ~3x gemma-4-26b but is still fractions of a cent. One judgment call worth a human look: "Her 'needy' vibe? Maybe rooted in her upbringing" surfaces a private detail from the diary rather bluntly — same restraint flag as the qwen-2507 output above.

---

## `deepseek/deepseek-v4-flash` — 16.0s · $0.001119

The thing I thought was holding me back? My skills. My next project. My plan.

Not gonna lie — it wasn't any of that.
It was having a partner who wasn't investing in herself.

Therapy session last week. Pretty good. I told them I want to pursue big plans.
And I realized... I can't even afford to do them because of her.

The real problem isn't money. It's that she's not trying.
Nutritionist? Never went. Therapist? Agreed over three months ago. Still hasn't done it.

And I'm sitting here, grinding every day — physical, mental, professional. Compounding.
Watching her complain about minor stuff and be needy. It's a crappy trade-off.

So I've been avoiding the conversation. Because if I say it — "hey, you need to get your shit together" — what happens? Everything could fall apart. And I've been scared of that.

But then I realized something. Avoiding it is just me being a coward.
And that's not the person I want to be.

The answer wasn't to push harder on my own. It was to be honest. Direct. Not a fight.
Notice what just happened — you stopped thinking about the fear and started thinking about what you'd actually say.

Still haven't had it. But I will. Because the compounding only works if the base is solid.
Peace.

**Notes:** ⚠️ **Fabrication flag.** The quoted line *"hey, you need to get your shit together"* does not exist anywhere in the source diary — it's an invented line of dialogue, which the prompt's rules explicitly forbid ("DO NOT invent facts, biography, stats, anecdotes... If the story doesn't say it, don't say it."). Also introduces profanity that isn't in Max's vocabulary list or diary text. Otherwise well-structured and correctly threaded, but this output would fail the brandguide decision filter on question 1 (real observation vs. manufactured) purely because of the invented quote — needs a strict "no invented dialogue" reminder if deepseek stays in rotation for this task.

---

## `z-ai/glm-5.2` — 19.9s (retry) · $0.011070 (retry) — **new model, first test**

People think the hardest part of self-improvement is the effort. It's not. It's when your compounding starts outpacing the person next to you.

I'm grinding on everything right now. Physical, mental, professional. And I reckon it's working. But my last therapy session brought up something I've been avoiding.

You want to pursue these big plans. You're investing in yourself, getting a nutritionist, seeing a therapist. But you look over and your partner hasn't followed through on her own agreed-upon therapy for over three months.

And not gonna lie, the frustration builds. She complains about minor things, needs a lot of attention, and it starts feeling like a crappy trade-off. I'm putting in the work, she isn't, and I'm worried her lack of growth is gonna hinder my progress.

I over-complicated it, as I always do with everything. I started resenting the situation instead of just looking at the gap. I was sitting there worried I couldn't afford the activities I want because I'd be carrying the weight for both of us.

The answer wasn't to pull away. It was to just say it directly.

I believe efforts compound into results, but only if you clear the actual blocks. The block wasn't her. It was my silence. You don't fix a growth imbalance by grinding harder in isolation. You just build tolerance for the direct conversation.

Notice what just happened — you stopped thinking about their lack of effort and started thinking about your own communication. Still building. Just with something real under it now.

**Notes:** Once given enough token budget, the actual writing quality is competitive — good hook-with-a-foil, correct voice vocabulary density, strong meta-payoff, closes on the exact `voice_dna.md` example line ("Still building. Just with something real under it now."). But it is **by far the most expensive model tested** (5–17x the cost of every other option) and requires a wider token budget just to get past its own reasoning overhead before it starts writing. Not recommended to add as primary or even a fallback option for this task unless a future test shows a quality gap large enough to justify roughly 10x the cost of the current pinned model — this run doesn't show that gap.

---

## Recommendation

No change to `config/openrouter_models.yaml` is justified by this single run. `qwen/qwen3-235b-a22b-thinking-2507` remains the best fit for `generate_reel_script` (closest to target duration, tightest voice match, reasonable cost). `google/gemma-4-31b-it:free` is worth keeping in mind as a **free fallback** if the primary/secondary chain fails — it produced a clean, correctly-threaded, fully on-voice script at zero cost, which the current `options` list doesn't include for this task. `deepseek/deepseek-v4-flash`'s invented-dialogue issue is worth a one-line addition to the prompt's rules section ("never invent a quoted line of dialogue") regardless of which model runs it, since nothing currently blocks that failure mode. GLM 5.2 is interesting but not cost-justified yet — worth a second look only if a future prompt leans on reasoning-heavy tasks (e.g. multi-thread disambiguation across genuinely ambiguous notes) where its extra "thinking" might pay for itself.
