# Blueprint v2.4 — Frontend UX Overhaul

## State
Reduce navigation friction across Narrative Warehouse, Content Writer, Reels.
Affected files:
- `NOTION DIARY FETCHER/config.toml` (thresholds)
- `frontend/src/lib/frameworkLabel.js`
- `frontend/src/components/ModelSelector.jsx`
- `frontend/src/components/StoryNodeList.jsx`
- `frontend/src/components/StoryNodeCard.jsx`
- `frontend/src/components/NarrativeDashboard.jsx`
- `frontend/src/components/ContentWriter.jsx`
- `frontend/src/components/ReelWriter.jsx`
- `frontend/src/App.jsx`

## Decisions (confirmed with user)
1. **Score:** global — config `min_worth_score 0.70 → 0.80`, `default_story_limit → 200`. Writers send `top_n: 200`.
2. **Synthesize week:** hide behind an "Advanced" disclosure with a one-line explanation.
3. **Framework label:** `source_file (db_id_tag) — Hook · Tone/Pacing · CTA`.
4. **Warehouse cards:** compact summary row, expand-to-edit.

## Logic
- DB facts: 110 story_nodes, 87 at worth ≥ 0.80. Framework `id` is the real tag; `source_file` is the friendly name.
- Warehouse: drop min-score slider + Normal/Low flag buttons; always `fetchAllStoryNodes(0.80)`; keep search/sort/count.
- StoryNodeCard: collapsed = conflict title + score badge + tags + [LinkedIn][Reel] buttons + expand/edit. Expanded = full fields + worth slider + tags; edit unchanged.
- Deep link: card `onCreate(channel, node)` → App sets tab (`writer`/`reels`) + `initialStory`. Writer preselects story on mount (inject into list if absent), shows preview.
- Writers: add selected-story preview panel; raise `top_n` to 200.
- ModelSelector: glass-panel light styling (on-surface text).

## Specs
React logic kept in components; no router (tab state in App). Python untouched except config.

## Definition of Done
- Warehouse shows only ≥0.80 stories as compact cards with working action buttons.
- Clicking a card action lands on the right writer with the story preselected + preview shown.
- Both writer dropdowns list all ≥0.80 stories; selecting shows a readable preview.
- Framework dropdowns show `name (tag)`; model selector legible.
- Synthesize-week tucked under Advanced. Verified in browser.
