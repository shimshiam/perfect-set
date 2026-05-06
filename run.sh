#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT_DIR/health-form-tracker"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
VENV_DIR="$ROOT_DIR/.venv"

if [[ ! -f "$VENV_DIR/bin/activate" && -f "$APP_DIR/.venv/bin/activate" ]]; then
  VENV_DIR="$APP_DIR/.venv"
fi

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_RELOAD="${BACKEND_RELOAD:-0}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ -n "$FRONTEND_PID" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}

require_path() {
  local path="$1"
  local message="$2"

  if [[ ! -e "$path" ]]; then
    echo "$message"
    exit 1
  fi
}

is_port_in_use() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

find_available_port() {
  local port="$1"

  while is_port_in_use "$port"; do
    port=$((port + 1))
  done

  echo "$port"
}

is_backend_healthy() {
  local port="$1"
  curl -fsS "http://$BACKEND_HOST:$port/health" >/dev/null 2>&1
}

wait_for_backend() {
  local attempts=240

  until is_backend_healthy "$BACKEND_PORT"; do
    if [[ -n "$BACKEND_PID" ]] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      echo "Backend failed to start."
      exit 1
    fi

    attempts=$((attempts - 1))
    if (( attempts == 0 )); then
      echo "Backend did not become healthy at http://$BACKEND_HOST:$BACKEND_PORT/health"
      exit 1
    fi

    sleep 0.25
  done
}

trap cleanup EXIT INT TERM

require_path "$APP_DIR" "Missing app directory: $APP_DIR"
require_path "$BACKEND_DIR/server.py" "Missing backend server: $BACKEND_DIR/server.py"
require_path "$FRONTEND_DIR/package.json" "Missing frontend package.json: $FRONTEND_DIR/package.json"
require_path "$VENV_DIR/bin/activate" "Missing virtual environment. Create it first, then install requirements."

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Missing frontend dependencies. Run: cd $FRONTEND_DIR && npm install"
  exit 1
fi

source "$VENV_DIR/bin/activate"

START_BACKEND=1
if is_port_in_use "$BACKEND_PORT"; then
  if is_backend_healthy "$BACKEND_PORT"; then
    START_BACKEND=0
    echo "Reusing backend at http://$BACKEND_HOST:$BACKEND_PORT"
  else
    BACKEND_PORT="$(find_available_port "$((BACKEND_PORT + 1))")"
  fi
fi

FRONTEND_PORT="$(find_available_port "$FRONTEND_PORT")"

if (( START_BACKEND )); then
  cd "$BACKEND_DIR"
  if [[ "$BACKEND_RELOAD" == "1" ]]; then
    python -m uvicorn server:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload &
  else
    python -m uvicorn server:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
  fi
  BACKEND_PID=$!
fi

wait_for_backend

cd "$FRONTEND_DIR"
VITE_WS_BASE_URL="ws://$BACKEND_HOST:$BACKEND_PORT/ws" \
  npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" --strictPort &
FRONTEND_PID=$!

echo "Backend:  http://$BACKEND_HOST:$BACKEND_PORT"
echo "Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"
echo "Press Ctrl-C to stop both servers."

wait
