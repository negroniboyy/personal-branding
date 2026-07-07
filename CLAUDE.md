# CLAUDE.md - Root Guardrails

## 🚀 0. SESSION BOOTSTRAP (do this FIRST, every session)
Before any other work, read the workspace's SINGLE SOURCE OF TRUTH at the **BrandStudio root**
(one level up from this repo), if it exists (skip silently if absent):
1. `../md/checkpoint.md` — live session state (status, file map, next steps).
2. `../md/code_index.md` — live code index (file → role / key symbols).

`personal_brand/md/` is **retired** (pointer stubs only) — do not read or write it.
`/session-checkpoint` writes to the root `../md/` only, never here. These are **live documents**:
update them in place, never append. Notify the user briefly when you've loaded them.

Every time you're switching models, you have to notify the user.
Every time you're following any protocol from this CLAUDE.md, notify the user in a straightforward manner.

## 🤖 1. MODEL ROUTING
| Phase | Model | Primary Directive |
| :--- | :--- | :--- |
| **Planning** | Opus 4.7 | Build Blueprint; No code until alignment. |
| **Execution** | Sonnet | Zero verbosity; Code/Diffs only. |
| **Testing/Scout** | Haiku | Validate results & fetch data/files. |


## 📐 2. THE BLUEPRINT PROTOCOL
At the end of Planning, generate `handoff/blueprint_v[X.X]_[feature].md`.
**Must include:**
- **State:** Current repo summary + affected file list.
- **Logic:** Pseudo-code/Flow-logic (Model-agnostic for Gemma/Codex).
- **Specs:** Python 3.12 (uv), Textual TUI, React logic centralization.
- **Goal:** Clear "Definition of Done" for the Execution model.

## 🛰 3. SUB-AGENT PRE-FLIGHT (Haiku Default)
Before spawning sub-agents for parallel tasks:
1. **Estimate:** Provide a quick token/cost impact quote.
2. **Toggle:** User must choose **[💨 SPEED]** or **[🪙 COST]**.
3. **Approval:** Explicit permission required before deployment.
4. **Log:** Format as `[Action]: Using [Qty] sub-agents on [Model]`.

## 📜 4. OPERATIONAL GUARDRAILS
- **Scope:** Stay in the deployed env. No parallel directory hopping.
- **Access:** Use **Haiku** for reads. No full-repo scans unless requested.
- **Verbosity:** Execution is strictly minimalist. No "I have finished" prose.
- **Logic:** Business logic must remain decoupled from UI files.

## 📉 5. CONTEXT & TOKEN MANAGEMENT
- **Threshold:** At **50% context**, stop and trigger `/skill/session-checkpoint`.
- **Handoff:** Use the latest Blueprint to resume in a fresh session.
- **Exclusion:** Strictly follow `.claudeignore` (Builds, Node_Modules, `handoff/` history).