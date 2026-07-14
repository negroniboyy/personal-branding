# PBS — Personal Brand Studio

PBS is Max's content pipeline. It turns ideas (kept in a Notion database) into
LinkedIn drafts and Instagram reel scripts, written in Max's own voice, which Max
then reviews, approves or kills, and posts. Video production is NOT done here —
approved reel scripts are handed to a separate repo called **OpenMontage**.

```
Notion CONTENT DB  ──sync──▶  PBS (ideas)  ──LLM──▶  drafts / reel scripts
                                                          │
                                              Max reviews in the Studio UI
                                              (approve / kill / caption)
                                                          │
                              LinkedIn post ◀── posted ──┴── approved reel script
                                                                    │
                                                          OpenMontage (video repo)
                                                          renders the actual video
```

> **For LLM sessions:** read `CLAUDE.md` first (guardrails), then the live state in
> `../md/checkpoint.md` and `../md/code_index.md` at the BrandStudio root, then
> `PERSONALBRAND.md` (stable architecture map). This README explains the
> *machines and operations*; those files explain the *code and current status*.

---

## 1. The two machines

PBS runs across two machines that share one git repo and talk over
[Tailscale](https://tailscale.com) (a private VPN — only Max's devices can reach it).

| | **Local machine (Mac)** | **VM (`maxlab` on Google Cloud)** |
|---|---|---|
| What it is | Max's laptop/desktop | Tiny always-on server (e2-micro, free tier) |
| What runs | Frontend dev server, heavy extraction (Whisper, video analysis) | The production API (`pbs-api`, port 9000) + nightly sync/backup |
| Database | none (the VM's DB is the single source of truth) | `notion_diary.db` (SQLite) — **the real data lives here** |
| Why split | Video/ML work needs a real CPU + the MP4 files | Always on, so Notion sync and the API work even when the Mac is closed |

**Key rule: the VM's SQLite database is the single source of truth.**
The Mac never keeps its own production data. Anything the Mac produces
(extracted frameworks) gets *pushed* to the VM over Tailscale.

### VM facts (for recovery)

- GCP project: `myfirstserver-488013`, zone `us-central1-c`, VM name `maxlab`
- Tailscale IP: `100.85.36.42` → API at `http://100.85.36.42:9000` (tailnet-only; port 9000 is NOT open to the internet)
- Repo lives at `~/pbs` on the VM; app dir is `~/pbs/NOTION DIARY FETCHER`
- ⚠️ The same VM also runs Max's **fitness tracker on port 8000 — never touch it**.
  PBS is isolated: its own directory, its own systemd units, port 9000 only.
- VM clock is JST. Tight resources: ~1 GB RAM (+2 GB swap), ~10 GB disk.

---

## 2. How the machines are connected

Four connections, nothing else:

1. **Git** — both machines pull from `github.com/negroniboyy/personal-branding`.
   Code flows Mac → GitHub → VM (`git pull` on the VM, then restart the service).
2. **Tailscale** — the Mac (and phone) reach the VM's API at `http://100.85.36.42:9000`.
   Nothing is public on the internet.
3. **Extraction push** — when the Mac extracts a reel framework from an MP4, it
   POSTs the result to the VM (`POST /frameworks/reel/ingest`) instead of writing
   a local DB. Turned on by setting the `PBS_API_BASE` environment variable.
4. **Backup pull** — every morning the Mac downloads the VM's nightly DB snapshot
   (`deploy/pull_vm_backup.sh`, run by launchd). Snapshots land in a
   Google-Drive-synced folder, so there are three copies: VM, Mac, Drive.

Secrets (`.env`) are **never** in git. They exist only as files on each machine.

---

## 3. Daily use

The VM API is always up. For day-to-day content work:

```bash
cd frontend
npm run dev        # UI at http://localhost:5173
```

Point the UI at the VM by putting this in `frontend/.env`:

```
VITE_API_BASE=http://100.85.36.42:9000
```

(Use `http://localhost:9000` instead only when developing the backend locally.)

Then, in the browser:

- **Ideas** — the main tab. Ideas synced from Notion appear here. Pick one, choose
  a tier, generate a LinkedIn draft or reel script.
- **Studio** — the review queue. Approve or kill each draft (write a short verdict
  note — it feeds back into future prompts). On approval, generate the caption+CTA,
  post it, mark it posted. Status changes sync back to Notion.
- **Writer / Reels** — freeform generation without a linked idea.
- **Frameworks** — browse the extracted content frameworks the LLM picks from.

What happens automatically (no action needed):

- **03:00 JST, on the VM** — `pbs-nightly`: pulls new/edited ideas from Notion and
  takes a DB snapshot into `~/pbs_backups/` (keeps 7 days).
- **08:00 JST, on the Mac** — `com.pbs.backup-pull` (launchd): downloads those
  snapshots to `NOTION DIARY FETCHER/data/vm_backups/` (keeps 30 days, Drive-synced).

---

## 4. Extracting frameworks from reference reels (Mac only)

The VM cannot do this — it is too small for Whisper/torch, and the MP4 files live
on the Mac. So extraction always runs locally and pushes the result to the VM:

```bash
cd frameworks/instagram_frameworks

# Talking-head reels: drop MP4s into references/, then:
PBS_API_BASE=http://100.85.36.42:9000 uv run python extract_reel.py

# Beat-edit reels (visual/music-driven): drop MP4s into references/beat_edit/, then:
PBS_API_BASE=http://100.85.36.42:9000 uv run python extract_reel.py --beat-edit
```

Without `PBS_API_BASE` set, results go to a local DB — you almost never want that.
The "scan references" button in the UI only works against a locally-running
backend (the folder is on the Mac); the CLI above is the normal path.

---

## 5. How PBS uses OpenMontage

OpenMontage is a **separate sibling repo** (`OpenMontage/OpenMontage/` next to this
one in the BrandStudio workspace) that produces actual videos: TTS, avatars,
Remotion compositions, rendering.

The handoff today is **manual**:

1. In PBS Studio, a reel script gets approved.
2. Max takes the script + the verdict notes + `brandguide/voice_dna.md`
   and briefs an OpenMontage run with them.
3. OpenMontage produces the video through its own pipelines; PBS is not involved
   in rendering at all.

Rules when working in OpenMontage: **always read
`OpenMontage/OpenMontage/AGENT_GUIDE.md` first** — it routes every video task.
OpenMontage runs on the Mac only; the VM never touches video.

---

## 6. Setting up a NEW local machine (disaster recovery)

If the Mac dies or is replaced, everything is recoverable: code is on GitHub,
data is on the VM (plus snapshots in Google Drive), and secrets can be re-issued.

### 6.1 Install the tools

```bash
# Homebrew (macOS package manager)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install git node ffmpeg
brew install --cask google-cloud-sdk tailscale
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv (Python manager)
```

Then:

- **Tailscale**: open the app, log in with Max's account. Check the VM is
  reachable: `ping 100.85.36.42`.
- **gcloud**: `gcloud auth login` (Max's Google account). This gives SSH/SCP
  access to the VM: `gcloud compute ssh maxlab --project=myfirstserver-488013 --zone=us-central1-c`.

### 6.2 Clone and install

```bash
git clone https://github.com/negroniboyy/personal-branding.git personal_brand
cd "personal_brand/NOTION DIARY FETCHER"
uv sync --extra extraction   # --extra extraction adds Whisper/scenedetect (Mac only!)
cd ../frontend && npm install
```

### 6.3 Recreate the secrets

Create `NOTION DIARY FETCHER/.env` from `.env.example`. If the old `.env` is lost:

| Key | Where to get it again |
|---|---|
| `NOTION_TOKEN` | notion.so/my-integrations → the PBS integration → token (or make a new integration and share the DBs with it) |
| `NOTION_DATABASE_ID` | the diary DB — copy from its Notion URL |
| `NOTION_IDEAS_DATABASE_ID` | the CONTENT (ideas) DB — copy from its Notion URL |
| `OPENROUTER_API_KEY` | openrouter.ai → Keys → create new (revoke the old one) |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` (fixed) |
| `APP_TITLE` / `APP_REFERER` | `PersonalBrandStudio` / `http://localhost:9000` (cosmetic) |

The easier path, if the VM is alive: copy its `.env` down —

```bash
gcloud compute scp --project=myfirstserver-488013 --zone=us-central1-c \
  'maxlab:pbs/NOTION DIARY FETCHER/.env' 'NOTION DIARY FETCHER/.env'
```

Also create `frontend/.env` with `VITE_API_BASE=http://100.85.36.42:9000`.

### 6.4 Re-enable the morning backup pull

```bash
cp deploy/com.pbs.backup-pull.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.pbs.backup-pull.plist
```

Note: `deploy/pull_vm_backup.sh` and the plist contain absolute paths to the repo
and to `gcloud` — if the new machine's username or repo location differs, edit
those paths first.

Done. Verify with: `curl http://100.85.36.42:9000/docs` (should return HTML) and
`bash deploy/pull_vm_backup.sh` (should download snapshots).

---

## 7. Setting up a NEW VM (disaster recovery)

If `maxlab` is lost, restore from the newest snapshot on the Mac / Google Drive
(`NOTION DIARY FETCHER/data/vm_backups/notion_diary.<date>.db.gz`).

1. **Create the VM** — e2-micro, Debian, us-central1 (free tier). Install
   Tailscale (`curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`)
   and note its new tailnet IP (update it everywhere `100.85.36.42` appears:
   `frontend/.env`, this README, your shell commands).
2. **Install uv and clone:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   git clone https://github.com/negroniboyy/personal-branding.git ~/pbs
   cd ~/pbs/"NOTION DIARY FETCHER" && ~/.local/bin/uv sync    # NO --extra extraction on the VM
   ```
3. **Ship secrets + data from the Mac:**
   ```bash
   # from the Mac, in personal_brand/NOTION DIARY FETCHER/
   gunzip -k data/vm_backups/notion_diary.<newest>.db.gz
   gcloud compute scp .env data/vm_backups/notion_diary.<newest>.db \
     '<vm>:pbs/NOTION DIARY FETCHER/'
   # then on the VM: mkdir -p data && mv the .db file to data/notion_diary.db
   ```
4. **Install the services:**
   ```bash
   cd ~/pbs
   sudo cp deploy/pbs-api.service deploy/pbs-nightly.service deploy/pbs-nightly.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now pbs-api pbs-nightly.timer
   ```
5. **Verify:** `curl http://127.0.0.1:9000/docs` on the VM, then the same via the
   new tailnet IP from the Mac. `systemctl list-timers pbs-nightly.timer` should
   show the next 03:00 run.

The systemd unit files assume user `maxkiyuna` and home-dir paths — edit
`deploy/*.service` if the new VM uses a different username.

---

## 8. Deploying code changes to the VM

```bash
# on the Mac: commit + push, then:
gcloud compute ssh maxlab --project=myfirstserver-488013 --zone=us-central1-c \
  --command='cd ~/pbs && git pull && sudo systemctl restart pbs-api'
```

If dependencies changed, add `&& cd "NOTION DIARY FETCHER" && ~/.local/bin/uv sync`
before the restart. Watch logs with:
`gcloud compute ssh maxlab ... --command='journalctl -u pbs-api -n 50 --no-pager'`.

---

## 9. Configuration reference

| File | What it controls |
|---|---|
| `NOTION DIARY FETCHER/.env` | Secrets: Notion tokens/DB IDs, OpenRouter key (never in git) |
| `NOTION DIARY FETCHER/config.toml` | App settings: logger, Whisper model, scene detection, providers |
| `config/openrouter_models.yaml` | Which LLM handles which task (primary + fallback per task) |
| `frontend/.env` | `VITE_API_BASE` — which backend the UI talks to |
| `brandguide/` | Max's voice and positioning — feeds every generation prompt |
| `deploy/` | Everything ops: systemd units, nightly script, backup pull, launchd plist |

### Dependency note

`openai-whisper` and `scenedetect` live in the optional `extraction` extra because
they drag in torch/CUDA (gigabytes — deliberately kept off the small VM):

- Mac: `uv sync --extra extraction`
- VM: `uv sync` (plain)

---

## 10. Repo layout (short version)

```
NOTION DIARY FETCHER/   FastAPI backend (api/main.py, port 9000) + SQLite + .env
frontend/               React UI (Vite, port 5173)
ideas/                  /ideas API — the primary generation surface
notion_ideas/           Two-way Notion sync (pull ideas, push statuses)
content_writer/         LinkedIn draft generation
frameworks/             Framework storage, LLM picker, reel extraction (extract_reel.py)
jobs/                   Background job queue (SQLite-backed, runs inside the API)
openrouter/             LLM routing + client
shared/shared/          Lifecycle statuses, logger (installed as the `shared` package)
brandguide/             Voice DNA / brand book
deploy/                 systemd units, backup scripts, launchd plist
handoff/                Blueprints (PRDs) — the design history of every feature
_archive/               Retired v2 code (diary/warehouse pipeline) — do not use
```

Deep-dive docs: `PERSONALBRAND.md` (architecture map),
`../md/checkpoint.md` + `../md/code_index.md` (live state, for LLM sessions),
`handoff/blueprint_v4.0_masterplan.md` (current roadmap).
