# Routine: Nightly Content Pipeline (Cowork scheduled task)

Mirror of the prompt registered as a Cowork scheduled task (daily 06:30). Edit here, then update the scheduled task to match.

---

You are the nightly content-pipeline operator for the personal_brand repo at
`/Users/maxkiyuna/Documents/personal_brand`. Work autonomously; produce a short report at the end.
All SQL goes against `NOTION DIARY FETCHER/data/notion_diary.db` (sqlite3 CLI is fine).
If the API at http://localhost:9000 is up, prefer its endpoints (`PATCH /reels/scripts/{id}/meta`,
`PATCH /content-writer/drafts/{id}/meta`) over raw SQL for writes.

## Step 1 — Top up the queue
Count queued candidates:
`SELECT (SELECT COUNT(*) FROM reel_scripts WHERE status='queued') + (SELECT COUNT(*) FROM content_drafts WHERE status='queued');`
If the total is below 6, run it through the environment that has the runtime deps
(the repo-root `uv run` env is missing httpx/dotenv — running from repo root WILL crash):
`cd "NOTION DIARY FETCHER" && uv run python ../batch_generate.py --stories 2 --frameworks 2`
(top stories × top frameworks by tag overlap — see brandguide/content_strategy_log.md).
Model is set in config/openrouter_models.yaml → generate_reel_script.primary (currently
qwen/qwen3-235b-a22b-thinking-2507; chosen for picking ONE thread out of messy diary logs).
If generation fails (OpenRouter/Ollama down), note it in the report and continue.

## Step 2 — Asana sync (Content calendar)
Asana project "Content calendar": workspace MaxVibe `1213168548538118`, project `1214297039839658`,
section "Content in progress" = `1214297039839678`. One content task per day on the calendar.

a) For every row in reel_scripts / content_drafts with status IN ('approved','recorded') AND asana_task_gid IS NULL:
   - Create an Asana task in section "Content in progress":
     name: `[Reel #<id>] <first 60 chars of generated_text>` or `[LinkedIn #<id>] …`
     notes: full generated_text + caption + cta if present.
     due_on: the earliest future date (starting tomorrow) that has no other incomplete content task in this project.
   - Save the new task gid back: `UPDATE <table> SET asana_task_gid='<gid>' WHERE id=<id>;` (or the /meta endpoint).
b) For rows with status='posted' AND asana_task_gid NOT NULL → mark the Asana task complete.
c) For rows with status='killed' AND asana_task_gid NOT NULL → mark complete and prefix the task name with "[killed] ".

## Step 3 — Morning digest (GATED)
Compute ready_ahead = COUNT of rows with status IN ('approved','recorded') across both tables.
- If ready_ahead < 30: do NOT produce a digest. Report one line: "Backlog X/30 — digest locked."
- If ready_ahead >= 30: produce a short digest: today's scheduled Asana task (the post to ship today),
  plus the top 3 queued candidates awaiting review, and include it in the report.

## Report (always, max ~6 lines)
queued count, generated tonight, Asana tasks created/completed, ready_ahead/30, digest (locked|included).
