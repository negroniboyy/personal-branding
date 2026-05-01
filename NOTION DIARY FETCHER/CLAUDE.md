# CLAUDE.md - Root Guardrails
Always start session looking for a md/checkpoint.md
Every time you're switching models, you have to notify the user

Every time you're following any protocol from this CLAUDE.md notify the user in a striaght forwards manner

DO NOT install anything that constaind axios 1.14.1 or 0.30.4

DO NOT create markdown files that exceed 12KB in size (split into multiple files if needed)

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
- **Logic:** Signatures + data flow only. NO function bodies. NO full implementations. Max ~500 tokens per module. Local LLM writes the actual code from these specs.
- **Specs:** Python 3.12 (uv), Textual TUI, React logic centralization.
- **Goal:** Clear "Definition of Done" for the Execution model.
- **User Verification Section:** At the end, include explicit checklist with "⚠️ User Verification Report" — ask user to check each item and report what failed or is missing before proceeding to next milestone.

**Blueprint Logic format (per module):**
```
module.py — one-line responsibility
  Functions: name(args) -> return_type
  Key rules: bullet constraints (e.g. rate limit, idempotency)
  Calls: what it imports/calls from other modules
```
**Hard limit:** Each blueprint part must fit in local LLM context (<5KB). Split into p1/p2/p3 if needed.

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

## 🎯 6. LOCAL LLM HANDOFF PROTOCOL
**Claude Code role:** Planning, review, validation only. NOT code execution.  
**Gemma4 e2b role:** Reads Blueprint, writes all code.  
**Workflow:**
1. **Plan phase (Opus 4.7):** Ask clarifications, build Blueprint in `handoff/blueprint_vX.X_[feature].md`
2. **Approval gate:** Present Blueprint to user; wait for explicit "execute" or "hand off" approval
3. **Handoff (never auto-execute):** User copies Blueprint to Gemma4 e2b context; Gemma4 writes code
4. **Review phase (Haiku):** I validate Gemma4's output against Definition of Done, run tests, report gaps
5. **Iterate:** If Gemma4 misses items, loop back to step 3 with corrected Blueprint

**CRITICAL:** Do NOT write code yourself. If user says "go", ask: "Should I hand this off to Gemma4, or would you like me to code this milestone?" Always default to Gemma4 handoff unless explicitly told otherwise.