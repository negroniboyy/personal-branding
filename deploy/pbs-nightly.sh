#!/bin/bash
# PBS nightly: trigger Notion ideas sync, then back up SQLite (local rotation + GCS if creds present).
set -uo pipefail

APP_DIR="/home/maxkiyuna/pbs/NOTION DIARY FETCHER"
DB="$APP_DIR/data/notion_diary.db"
BACKUP_DIR="/home/maxkiyuna/pbs_backups"
BUCKET="gs://pbs-backups-myfirstserver-488013"
GCS_KEY="/home/maxkiyuna/.gcp/pbs-backup.json"
STAMP="$(date +%Y-%m-%d)"
OUT="$BACKUP_DIR/notion_diary.$STAMP.db"

mkdir -p "$BACKUP_DIR"

# 1. Notion ideas sync (enqueues job; pbs-api worker executes it)
curl -sf -X POST http://127.0.0.1:9000/notion/sync -o /dev/null \
  || echo "WARN: sync trigger failed (pbs-api down?)"

# 2. Consistent SQLite snapshot via online backup API
cd "$APP_DIR"
/home/maxkiyuna/.local/bin/uv run python - "$DB" "$OUT" <<'EOF'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close(); src.close()
EOF
gzip -f "$OUT"

# 3. Local rotation: keep 7 days
ls -1t "$BACKUP_DIR"/notion_diary.*.db.gz 2>/dev/null | tail -n +8 | xargs -r rm -f

# 4. GCS upload (skipped until service-account key is provisioned)
if [ -f "$GCS_KEY" ]; then
  CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE="$GCS_KEY" \
    gcloud storage cp "$OUT.gz" "$BUCKET/" --quiet \
    || echo "WARN: GCS upload failed"
else
  echo "INFO: $GCS_KEY absent — local backup only"
fi
