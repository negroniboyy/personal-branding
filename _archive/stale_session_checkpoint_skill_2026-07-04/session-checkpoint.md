---
name: session-checkpoint
description: Create or refresh a single compact session checkpoint (md/checkpoint.md) for any Python repository. Use when a user asks to save session context, create a checkpoint, prepare handover notes, bootstrap the next session, or run /session-checkpoint. Also triggers on /checkpoint, /code-memory, /context-memory.
---

# Session Checkpoint

Produces a single `md/checkpoint.md` — the only file a new session needs to read to bootstrap.
Density is the goal: every line must earn its place. Target ≤ 80 lines total.

## Flags

| Flag | Behavior |
|------|----------|
| (default) | Scan repo + write/update `md/checkpoint.md` |
| `--checkpoint-only` | Skip scan; update checkpoint from current conversation context only |
| `--full` | Force full scan (not incremental) |
| `--freeze` | Also copy checkpoint to `checkpoint/checkpoint_XX.md` (frozen snapshot) |

---

## Phase 1 — Code Scan (skip with `--checkpoint-only`)

### 1.1 Run the scanner

```bash
python ~/.claude/skills/session-checkpoint/scripts/build_code_memory.py \
  --repo-root . --output md --mode <full|changed> --no-docs
```

Use `--mode full` if `md/manifest.json` does not yet exist or if the user passed `--full`.
Otherwise use `--mode changed` (incremental — faster).

The script writes `md/manifest.json` (for incremental tracking) and prints a JSON summary
to stdout. Capture that JSON — it contains the file→subsystem map you need.

If Python is unavailable, fall back to inline scan: read key source files, extract top-level
classes/functions, and build the file list manually. Announce the fallback.

### 1.2 Migration (first run only)

If `md/context_memory.md` or `md/code_memory/` exist, delete them now:
```bash
rm -f md/context_memory.md
rm -rf md/code_memory/
```
Report each deletion in your output summary.

---

## Phase 2 — Write `md/checkpoint.md`

Read `md/checkpoint.md` if it exists (update in place). Otherwise create from scratch.

Write the file using this exact structure — no extra sections, no reordering:

```markdown
# [Project Name] — [YYYY-MM-DD]

**Stack:** [lang · framework · key dep] · **Run:** `[startup command]` · **v[X.Y.Z]**

## Status
[2–3 sentences MAX. What it does + current phase/state. Hard limit: 300 characters.]

## File Map
| File | Role |
|------|------|
| path/file.py | [terse one-liner] |

## Edit Here When...
| Change | File |
|--------|------|
| [common task] | `path/file.py` |

## Active Context
- **Done:** [last shipped item]
- **Next:** [immediate next task]
- **Notes:** [blockers / caveats — write "none" if clear]
```

### Budget rules

| Section | Limit |
|---------|-------|
| Status | ≤ 300 characters |
| File Map | 8–12 rows — key files only; skip tests, vendor, migrations unless critical |
| Edit Here When... | 5–10 rows |
| Active Context | 3–5 bullets |
| **Total file** | **≤ 80 lines** |

### Writing rules

1. Durable facts only — no version history, no "I just added X" prose.
2. Exact paths, commands, version numbers. No relative dates.
3. Don't describe *how* functions work — just *where* behaviour lives.
4. Update only sections touched by this session's work.
5. If a section has nothing meaningful: write `none`, not blank.

---

## Frozen snapshot (only with `--freeze`)

1. Find the highest existing `checkpoint/checkpoint_XX.md`
2. Copy `md/checkpoint.md` → `checkpoint/checkpoint_XX+1.md`
3. Never overwrite older snapshots.

---

## Output summary

Always report:
- `created: md/checkpoint.md` or `updated: md/checkpoint.md`
- Any files deleted during migration
- If frozen: `frozen: checkpoint/checkpoint_XX.md`
- Line count of the final checkpoint file
