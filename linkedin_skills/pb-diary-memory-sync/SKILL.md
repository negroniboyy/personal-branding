---
name: pb-diary-memory-sync
description: Refresh the PersonalBrand diary memory from Notion and use the resulting local brand-memory files efficiently. Use when Codex needs up-to-date diary context for PersonalBrand, LinkedIn drafting, brand alignment, authenticity checks, or content planning based on `Diary 2026`. Also use when the user asks to sync, refresh, fetch, rebuild, or inspect the local Notion diary memory database or markdown memory outputs.
---

# PB Diary Memory Sync

## Overview

Refresh the local diary-memory store for the PersonalBrand repo, then use the compact markdown outputs as the default context surface for content work.

Prefer the repo's existing sync pipeline over ad hoc Notion fetching.

## Workflow

1. Confirm the repo root is `/Users/maxkiyuna/Library/CloudStorage/OneDrive-MCPAssetManagementCoLtd/Documents/Taishi Lab/VibeCode/PB`.
2. Run `scripts/sync_diary_memory.py` from this skill, or directly run `python3 -m personalbrand.cli diary-sync` in the repo root.
3. Treat these files as the primary outputs:
   - `brandguide/memory_notion/profile.md`
   - `brandguide/memory_notion/recent.md`
   - `brandguide/memory_notion/diary.db`
4. For normal content work, read `profile.md` first.
5. Read `recent.md` only when recent diary context matters.
6. Inspect the snapshot JSON or SQLite DB only when the user needs exact evidence, debugging, or a deeper profile rebuild.

## Token Discipline

- Do not load the full snapshot JSON into context unless debugging extraction or validating a specific entry.
- Do not summarize the full diary database by default.
- Prefer `profile.md` as the brand anchor.
- Prefer `recent.md` as the short-window update layer.
- Use the database or snapshot only as a retrieval backstop.

## What To Use For

- Refreshing the diary memory before LinkedIn or PersonalBrand work.
- Grounding content ideas in real work, real projects, and recent lived context.
- Rebuilding the brand anchor after multiple new diary entries.
- Checking whether extracted projects, people, or summaries look wrong.
- Validating that the Notion-to-local-memory pipeline is current.

## Output Paths

Read [references/paths.md](references/paths.md) for the canonical repo path, command, and output file locations.

## Scripts

- `scripts/sync_diary_memory.py`
  Use this wrapper when the task is simply to refresh the diary memory and report the resulting paths and counts.
