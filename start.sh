#!/bin/bash
# Starts frontend (5173), main API (8000), and Ideas Draft API (8001)
# in separate Terminal tabs on macOS.

REPO="$(cd "$(dirname "$0")" && pwd)"

open_tab() {
  local title="$1"
  local cmd="$2"
  osascript \
    -e 'tell application "Terminal"' \
    -e "  tell application \"System Events\" to keystroke \"t\" using {command down}" \
    -e "  delay 0.3" \
    -e "  do script \"printf '\\\\e]0;$title\\\\a'; $cmd\" in front window" \
    -e 'end tell'
}

# Tab 1 — frontend
open_tab "Frontend" "cd '$REPO/frontend' && npm run dev"

# Tab 2 — main API (NOTION DIARY FETCHER, port 8000)
open_tab "API :8000" "cd '$REPO/NOTION DIARY FETCHER' && uv run uvicorn api.main:app --reload --port 8000"

# Tab 3 — Ideas Draft API (port 8001)
open_tab "Ideas :8001" "cd '$REPO/Ideas Draft' && uv run uvicorn main:app --reload --port 8001"

echo "Started 3 tabs: Frontend (5173)  ·  API (8000)  ·  Ideas Draft (8001)"
