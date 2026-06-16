#!/bin/bash
# Starts frontend (5173) and unified API (9000) in separate Terminal tabs on macOS.

REPO="$(cd "$(dirname "$0")" && pwd)"

open_tab() {
  local title="$1"
  local cmd="$2"
  osascript \
    -e 'tell application "Terminal"' \
    -e "  do script \"printf '\\\\e]0;$title\\\\a'; $cmd\"" \
    -e 'end tell'
}

# Tab 1 — frontend
open_tab "Frontend" "cd '$REPO/frontend' && npm run dev"

# Tab 2 — unified API (NOTION DIARY FETCHER, port 9000)
open_tab "API :9000" "cd '$REPO/NOTION DIARY FETCHER' && uv run uvicorn api.main:app --reload --port 9000"

echo "Started 2 tabs: Frontend (5173)  ·  API (9000)"
