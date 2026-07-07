# Raw Content Used For This Bake-Off

**Purpose:** test whether OpenRouter models can find the *one* dominant story thread inside a messy, multi-topic diary dump and turn it into a voiceover script in Max's voice — without visual/production concerns.

**Selection rule:** picked from `story_nodes` where `worth_score > 0.80` (the existing Stage1 extractor's own quality floor), and cross-checked against `reel_scripts` to make sure it hasn't already been used. This is the **highest-scoring unused node in the DB** (`worth_score = 1.0`).

---

## Story node (`story_nodes` row — the *distilled* summary, for orientation only)

| Field | Value |
|---|---|
| `id` | `sn_4e7ec1ec794b` |
| `page_id` | `312bc1f7-37a0-80c8-84cc-e1f221cb383e` |
| `worth_score` | **1.0** |
| `thematic_tags` | career, relationship, self-improvement |
| `user_state` | Managing professional pivots and relationship frustrations |
| `conflict_node` | ambition-vs-relationship-imbalance |
| `desired_outcome` | Achieve personal growth and relational alignment |
| `the_bridge` | Direct communication and compounding self-improvement lead to results |
| `llm_model_used` | ollama:gemma4:e2b |

This is what Stage1 already extracted as *the* thread worth telling. The test below does **not** give the models this distillation as the answer key — it's shown here only so we can check afterward whether each model converged on the same thread independently (see the comparison doc's scoring notes).

---

## Source diary (verbatim raw notes — page `02262026 - 🧠 Brain Vomit`)

This is the actual raw material handed to every model. Untouched, unedited — a real messy brain-dump spanning team dynamics, a fitness-project pivot, a therapy session, a relationship conflict, food, and unrelated meetup links.

```
🧠 Brain Vomit
Date: Yesterday
Overall mood: Good
Work / Team observations
Realization: Many things "not work" — expected eventual occurrence
Noticing individual strengths and blocks in team members
Bruce
Strength: Knowledgeable about infrastructure
Weaknesses: Lacks development knowledge (databases, APIs)
Attitude: Skeptical of using APIs; encourages manual work
Fabian-san
Attitude: Supportive of user's approach
Preference: Favors using APIs and developing tools
Plan / Next steps (work-related)
Proceed with own approach (use APIs, develop tools)
For fitness program:
Start from scratch
Deprioritize frontend due to incorrect data
Focus on backend: obtain correct data and build workflow
Timeline: This week
Afterwards: Upload to server; learn about servers and Linux
Personal / Therapy
Therapy session: Pretty good
Topics discussed:
Desire to pursue big plans
Need to discuss plans with partner (concern about inability to afford activities because of her)
Personal effort:
Continual self-improvement: physical, mental, professional
Belief that efforts compound into results
Relationship concerns
Perception: Partner invests minimally compared to user
Specific issues:
Partner not pursuing personal investments (e.g., nutritionist, therapist)
Agreed-upon therapy arrangement not followed for over three months
Partner perceived as needy and attention-seeking (linked to upbringing)
Partner complains about minor issues
Emotional impact:
Frustration that partner's lack of growth may hinder user's progress
Intention: Need to have a conversation with partner about these issues
Personal notes
Food: Ate two sets of takoyaki for dinner; enjoyed it
Emotional resolution: Plan to address relationship concerns directly

Running Meetups
https://www.meetup.com/chillruncrew-tokyo/events/311065617/?eventOrigin=group_events_list
https://www.meetup.com/sogo-fitness/events/313235388/?recId=8e22d1a9-ca1d-46f8-9718-3e8f7c1ac291&recSource=event-search&searchId=ccece9fb-89b7-4ba2-b63e-e3e61fda21e3&eventOrigin=find_page%24all
https://www.meetup.com/kamarun-kamakura-running-social-club/events/313391516/?recId=25da63b9-38df-413d-99c4-272ab480b350&recSource=event-search&searchId=c93875a5-bfc8-4808-8d2a-0f29358d486f&eventOrigin=find_page%24all
https://www.meetup.com/tokyo-connections-and-explorations/events/312429958/?recId=25da63b9-38df-413d-99c4-272ab480b350&recSource=event-search&searchId=c93875a5-bfc8-4808-8d2a-0f29358d486f&eventOrigin=find_page%24all
```

**Threads actually present in the raw text (for scoring which model found "the" story vs. laundry-listed):**
1. Team dynamics / Bruce vs Fabian-san (work)
2. Fitness-program rebuild — backend-first pivot (work/project)
3. Therapy session — big plans, self-improvement compounding
4. **Relationship conflict — partner investing less than him, broken therapy commitment (this is the thread Stage1 scored 1.0 / `worth_score`)**
5. Food note (takoyaki) — noise, not a thread
6. Running meetup links — noise, not a thread

---

## Framework used (shape only — not the subject)

`frameworks/instagram_frameworks/frameworks/ref3-instagram-pain_point-v1.yaml` — vulnerability-first pain point → escalation → pivot → insight, 8 beats, ~67s, conversational tone, no CTA. Chosen because its shape (name a fear, escalate, land on tolerance not resolution) fits the ambition-vs-relationship conflict better than a bold-claim framework would.

## Prompt used

The unmodified production prompt: `frameworks/instagram_frameworks/prompts/script_writer.txt` — includes RULE 0 (select one thread, ignore the rest), the full Voice DNA block, the six craft moves, and the transformation example. Every model received the **identical** prompt, `{{STORY}}` (distilled fields above), `{{SOURCE}}` (raw diary above), and `{{FRAMEWORK}}` (yaml above) — `{{IDEA}}` left empty.
