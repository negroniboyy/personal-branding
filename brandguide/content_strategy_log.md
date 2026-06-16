# Content Strategy Log — Control Centre

> Living document. Claude (strategist mode) updates this after every generation/review pass.
> This is the **judgment layer**: what we're learning about Max's voice, which frameworks fit
> which stories, and what makes his storytelling land. The prompt (`prompts/script_writer.txt`)
> is the *engine*; this doc is the *taste*.
>
> Source of voice truth: `brandguide/voice_dna.md`. Per-node review docs live in `drafts/`.

Last updated: 2026-06-01 (after n=3 pass: fitness, imposter, Japanese)

---

## 1. How this loop works

1. Claude picks candidate `story_nodes` (diverse themes) and hands Max CLI commands.
2. Max runs `gen_one_node.py` locally (sandbox can't reach OpenRouter — **generation is always local**).
3. Claude reads the `--out` JSON, grades every framework draft against the voice DNA, and recommends the strongest one to actually post.
4. Verdicts get logged in §5 below. Patterns that repeat across nodes get promoted to §2–§4.

**Active framework set (5):** ref1-bold_claim, ref1-contrarian, ref2-bold_claim, ref3-pain_point, ref6-bold_claim.
**Deleted (fabrication risk):** ref4 story_open, ref5 — anecdote-hook frameworks invented biography ("my entire 20s", fake parties). Removed to kill friction.

---

## 2. Voice patterns — CONFIRMED (do these)

These survived the n=1 review and are now load-bearing rules. Confidence rises as more nodes confirm them.

- **Voice overrides framework, always.** Inlining the distilled voice DNA into the prompt was the single biggest quality lever — it fixed CTAs across the board and stopped frameworks from hijacking the story. *(Confidence: high — this was the unlock.)*
- **Close on honest current state, never a CTA.** "Still building. Just with something real under it now." beats any "follow for more." No selling, ever.
- **Self-awareness marker lands.** Narrator catching himself in a pattern without judgment ("I over-complicated it, as I always do") is a signature move — use it where the story supports it.
- **Short declarative rhythm + single-sentence pivots.** "It worked. Then I kept going." Sentences end on personal ownership, not universal claims.
- **★ Fabrication is governed by SOURCE CONCRETENESS, not the framework.** *(Confidence: high — clean signal across n=3.)* Rich source story (fitness: runner friends, plyometrics, named injury) → near-zero fabrication. Thin/abstract source (Japanese) → every draft invented routine specifics ("90 min/night", "clients replied faster", "coworkers noticed"). The fix lives upstream: add 2-3 real specifics to the story node *before* generating, or restrict thin nodes to the fabrication-resistant frameworks (ref2, contrarian). This is now the #1 storytelling lever after voice injection.
- **Short + contrarian frameworks resist fabrication; long bold-claim invites it.** ref2 (40s) and ref1-contrarian stay conceptual and stay honest. ref1-bold_claim (70s, 30+ scenes) pads length by inventing specifics ("weather bot", "Raspberry Pi", "import requests") and reads rambly. Prefer short/contrarian for thin stories; reserve long bold-claim for concrete ones.

## 3. Voice patterns — BANNED (kill on sight)

- Influencer CTAs: "DM me", "link in bio", "comment below", "follow for more", "drop a comment".
- Hype vocab: "game-changer", "level up", "crushing it", "thought leader", "I'm excited to share", "grateful for this journey".
- Advice/preaching tone: "you should…", "here's what you need to do…", "here's the framework I wish I had".
- **Fabrication** — the persistent failure mode. No invented backstory, stats, named tools, events, or anecdotes not in the source story. This is why anecdote-hook frameworks were cut. *(n=3 update: fabrication now reappears whenever the source story is thin — see §2 ★. Mitigate upstream, not by deleting more frameworks.)*
- **Template artifact leak (ref3-pain_point):** invents a filming setup ("shot on my phone, pressed record") not present in the story. Appeared on both imposter + Japanese drafts. Candidate prompt fix.

## 4. Framework fit map

What kind of story each framework is good/bad at. Built from grades; updated as evidence accumulates.

| Framework | Best for | Grade (n=1, node sn_3fe9a0ad2290) | Notes |
|---|---|---|---|
| ref2-bold_claim | Build/process stories; **any thin/abstract story** | A (fitness), A- (imposter), B+ (jp) | **Most reliable.** Tight 40s, stays conceptual, fabrication-resistant. Default pick. |
| ref1-contrarian | "Everyone thinks X, actually Y" turns; **thin stories** | A- (fitness), A- (imposter), B+ (jp) | Stays conceptual → resists fabrication. Strong all-rounder. |
| ref3-pain_point | Vulnerable/struggle stories | A- (fitness), B+ (imposter), B (jp) | Good on vulnerable themes, but leaks "shot on my phone" filming artifact. |
| ref6-bold_claim | Concrete stories only | B+ (fitness), B (imposter), B- (jp) | Long; invents specifics on thin stories ("weather bot"). |
| ref1-bold_claim | Concrete stories only | B+ (fitness), C+ (imposter), B- (jp) | **Weakest.** 70s/30+ scenes, rambly, top fabrication risk. Candidate to retire/shorten. |

> n=3 confirmed: the voice map generalizes. ref2 + contrarian are the safe defaults; ref1-bold_claim is the weak link. The real quality driver is source concreteness (§2 ★), not framework choice.

## 5. Per-node verdict log

| Date | Node | Theme | Best framework | Verdict / notes |
|---|---|---|---|---|
| 2026-05-31 | sn_3fe9a0ad2290 | Over-complicating (build/career) | ref2-bold_claim (A) | v2 (voice-injected) fixed CTAs + drift across all frameworks. See `drafts/2026-05-31_*`. |
| 2026-06-01 | seed-fitness-001 | Fitness / injury / reset | **ref2-bold_claim (A)** | Strongest batch. Concrete source → near-zero fabrication. Post ref2 (id 41); ref3 (A-) is longer/vulnerable alt. `drafts_fitness.json`. |
| 2026-06-01 | sn_7f27d28f2148 | Imposter syndrome | **ref1-contrarian (A-)** | ref6/ref1-bold invented projects (weather bot, Raspberry Pi). Contrarian + ref2 stayed clean. `drafts_imposter.json`. |
| 2026-06-01 | sn_0726698b6935 | Japanese learning | **ref1-contrarian (B+)** | Weakest batch — thin source → all drafts invented routine specifics. Recommend adding real detail to the node + regen. `drafts_japanese.json`. |

## 6. Open questions / hypotheses to test

- ~~Does the voice map generalize past build stories?~~ **RESOLVED (n=3): yes.** Voice fidelity held across fitness/imposter/Japanese. CTAs clean, honest closes, signature lines landing everywhere.
- ~~Does fabrication reappear when the source story is thin?~~ **RESOLVED: yes, strongly** — and it's the dominant quality driver. See §2 ★.
- **Does ref3-pain_point win on vulnerable themes?** Partial: solid (A-/B+) but not the top pick; the filming-artifact leak holds it back. Re-test after fixing that prompt note.
- **New: should we add a "source concreteness" check before generating?** A thin node (few real specifics) predictably yields fabrication. Worth a pre-gen gate or an enrichment step that adds real detail to the story node first.
- **New: retire or shorten ref1-bold_claim?** Consistently weakest + highest fabrication risk. Decide after 1-2 more nodes.
- **Is 5 frameworks too many per node?** Leaning no — the spread is what surfaced the concreteness pattern. Keep for now; could default to ref2 + contrarian for thin nodes to save generation cost.
