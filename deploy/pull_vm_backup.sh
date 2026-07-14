#!/bin/bash
# Mac-side: pull nightly SQLite snapshots from maxlab into local (Google-Drive-synced) folder.
# Run by launchd (com.pbs.backup-pull) daily; safe to run manually.
set -uo pipefail

GCLOUD=/opt/homebrew/bin/gcloud
DEST="/Users/maxkiyuna/Library/CloudStorage/GoogleDrive-max.taishi@gmail.com/My Drive/VIBECODE/BrandStudio/personal_brand/NOTION DIARY FETCHER/data/vm_backups"

mkdir -p "$DEST"
"$GCLOUD" compute scp --project=myfirstserver-488013 --zone=us-central1-c \
  'maxlab:pbs_backups/*.db.gz' "$DEST/" --scp-flag=-p \
  || { echo "$(date -Iseconds) pull FAILED" >> "$DEST/pull.log"; exit 1; }

# keep 30 days locally
ls -1t "$DEST"/notion_diary.*.db.gz 2>/dev/null | tail -n +31 | xargs -I{} rm -f "{}"
echo "$(date -Iseconds) pull OK ($(ls "$DEST" | grep -c db.gz) snapshots)" >> "$DEST/pull.log"
