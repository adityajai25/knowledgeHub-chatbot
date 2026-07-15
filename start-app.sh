#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_LOG="$ROOT_DIR/.backend.log"
FRONTEND_LOG="$ROOT_DIR/.frontend.log"

if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:8000 | xargs -r kill -9 || true
  lsof -ti tcp:5173 | xargs -r kill -9 || true
else
  echo "lsof not found; skipping port cleanup"
fi

cd "$BACKEND_DIR"
source .venv/bin/activate
export PYTHONPATH="$BACKEND_DIR"
nohup python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 > "$BACKEND_LOG" 2>&1 &

cd "$FRONTEND_DIR"
nohup npm run dev -- --host 127.0.0.1 --port 5173 > "$FRONTEND_LOG" 2>&1 &

sleep 2

printf '\nBackend: http://127.0.0.1:8000\n'
printf 'Frontend: http://127.0.0.1:5173\n'
printf 'Backend log: %s\n' "$BACKEND_LOG"
printf 'Frontend log: %s\n' "$FRONTEND_LOG"
