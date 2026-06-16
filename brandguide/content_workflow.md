# Content Creation Workflow
_Updated: 2026-05-27 | Target: 4 LinkedIn + 4 Instagram/month_

---

## The rule above all rules

**Time caps are non-negotiable.** The system exists to lower the cost of creating. If you go over time, you ship what you have. You are not trying to produce your best work — you are trying to build the habit of producing.

| Step | Max time |
|---|---|
| Monthly planning session | 30 min |
| Draft generation (OpenRouter) | 5 min |
| Human review + edit | 20 min |
| Image generation | 5 min |
| **Total per post** | **~30 min** |

---

## Tools in the stack

| Job | Tool | Cost |
|---|---|---|
| Story selection | Local system `./start.sh` → Content Writer tab | Free |
| Draft generation | OpenRouter → see model picks below | ~$0.01–0.05/draft |
| Image generation | OpenRouter → `black-forest-labs/flux-schnell` | ~$0.003/image |
| Content home | Notion CONTENT database | Free |
| Deadline tracking | Asana "June Posts" project | Free |
| Brand check | `brandguide/voice_dna.md` decision filter | Free |

### OpenRouter model picks

| Use | Model | Why |
|---|---|---|
| First draft (cheap) | `meta-llama/llama-3.1-8b-instruct` | ~$0.04/M tokens, fast, follows system prompts well |
| Better quality | `google/gemini-2.0-flash-lite` | Better tone matching, ~$0.075/M tokens |
| Image thumbnails | `black-forest-labs/flux-schnell` | $0.003/image, 500ms, good for warm atmospheric stills |

**System prompt = voice_dna.md** (full file). Context = story_node fields + framework structure.

---

## Monthly planning session (once, ~30 min)

Run this at the end of each month for the next.

1. Open local system: `./start.sh`
2. Go to Content Writer tab → filter by domain
3. Pick **4 story_nodes for LinkedIn** (career/tech/building/learning tags)
4. Pick **4 story_nodes for Instagram** (fitness/philosophy/life tags)
5. For each: create a Notion page in CONTENT database using the brief template below
6. Assign a scheduled posting date (aim for Mon/Wed LinkedIn, Tue/Fri Instagram)
7. Create 8 Asana tasks in "Monthly Content" project, each with due date + Notion link

---

## Per-post creation workflow

### Step 1 — Open the brief (2 min)
Open the Notion page. Read the story_node fields. Know what the story is before touching any tool.

### Step 2 — Generate draft (5 min)
Call OpenRouter with:
- **System prompt**: full contents of `brandguide/voice_dna.md`
- **User prompt**: See template below

```
Story node:
- User state: [paste user_state field]
- Conflict: [paste conflict_node field]
- Desired outcome: [paste desired_outcome field]
- Tags: [paste thematic_tags]

Platform: [LinkedIn / Instagram Reel / Instagram static]
Framework: [paste framework structure from YAML]
Domain: [Building / Career / AI / Fitness / Philosophy]

Write a draft in Max's voice. Follow the voice DNA exactly.
Use the framework structure as the skeleton.
Do not add CTAs, hashtag blocks, or motivational sign-offs.
```

### Step 3 — Human review (20 min MAX)
Open `brandguide/voice_dna.md`, go to the decision filter. Ask each question once.
**Cut lines that fail, don't rewrite them.** Cutting is faster and produces better results.
If you spend more than 20 min, ship what you have.

### Step 4 — Image (5 min, Instagram only)
For Reels: you need real B-roll footage. Phone camera, natural light, whatever's around you.
For static posts (albasnotes style): clean text card in Figma or Canva — no AI needed.
For LinkedIn header (optional): FLUX Schnell with prompt:

```
Warm cinematic still, [topic-related subject], film grain, natural light,
muted earth tones, no text, no people, close detail shot
```

### Step 5 — Schedule and post
- Update Notion status → "Done"
- Mark Asana task complete
- Post manually (or schedule via Later/Buffer if you set it up)

---

## Notion page template (paste into each new page)

```markdown
## Brief
- Story node ID: [id]
- User state: [paste]
- Conflict: [paste]
- Tags: [paste]
- Platform: LinkedIn / IG Reel / IG Static
- Framework: [name + YAML path]
- Domain: Building / Career / AI / Fitness / Philosophy
- Scheduled: [date]

## Raw angle
[1-2 sentences on the specific angle you're taking]

## Generated draft
[paste OpenRouter output here]

## Reviewed draft
[paste your edited version here]

## Visual notes
[B-roll ideas, image prompt, or card copy]
```

---

## June 2026 content calendar

| # | Platform | Story node | Conflict angle | Week |
|---|---|---|---|---|
| L1 | LinkedIn | Early morning projects (existing draft) | Built it, broke it, stepped back | W1 (Jun 2) |
| L2 | LinkedIn | `sn_be9d61978326` | Too much inspiration = building nothing | W2 (Jun 9) |
| L3 | LinkedIn | `sn_19d639de61df` | Career pivot uncertainty, excited but lost | W3 (Jun 16) |
| L4 | LinkedIn | `sn_3fe9a0ad2290` | Scope management: stacking complexity until it breaks | W4 (Jun 23) |
| I1 | IG Reel | No perfectionism (existing draft) | Trading cinematic for actually shipping | W1 (Jun 3) |
| I2 | IG Reel | `seed-fitness-004` | Speed loss as necessary phase, trust the process | W2 (Jun 10) |
| I3 | IG Reel | `sn_be9d61978326` / "Slow down" | Slowing down to actually feel things | W3 (Jun 17) |
| I4 | IG Reel | `seed-fitness-001` | Injury forced a reset. What I built instead. | W4 (Jun 24) |

**Week 1 is already done.** L1 and I1 have existing drafts ready to review and ship.

---

## OpenRouter scaffolding (for Gemma4 to build)

See `handoff/blueprint_v1.0_openrouter.md` for the technical spec.

The scaffolding needs:
- A Python module that loads `voice_dna.md` as system prompt
- Accepts story_node fields + framework YAML as context
- Calls OpenRouter with configurable model (env var)
- Returns draft text + saves to DB `content_drafts` or `reel_scripts` table
- Optional: image generation call to FLUX Schnell, saves URL to draft record
