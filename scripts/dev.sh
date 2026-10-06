#!/bin/zsh
# Describe Studio dev loop: service -> Vite -> Electron (or browser).
# Usage: scripts/dev.sh [--web]   (--web skips Electron and prints the URL)
set -e
cd "$(dirname "$0")/.."

WEB_ONLY=0
[[ "$1" == "--web" ]] && WEB_ONLY=1

echo "Starting DescriptorPro service..."
.venv/bin/python -m service.main --dev > /tmp/ds-service.log 2>&1 &
SERVICE_PID=$!

cleanup() {
  echo "Stopping..."
  kill $SERVICE_PID 2>/dev/null || true
  [[ -n "$VITE_PID" ]] && kill $VITE_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Wait for the DS_READY handshake line
for i in {1..60}; do
  READY=$(grep -m1 '^DS_READY ' /tmp/ds-service.log 2>/dev/null || true)
  [[ -n "$READY" ]] && break
  sleep 0.25
done
[[ -z "$READY" ]] && { echo "Service failed to start. See /tmp/ds-service.log"; exit 1; }

export DS_PORT=$(echo "$READY" | sed 's/^DS_READY //' | python3 -c 'import json,sys;print(json.load(sys.stdin)["port"])')
export DS_TOKEN=$(echo "$READY" | sed 's/^DS_READY //' | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')
export DS_SERVICE_PORT=$DS_PORT
export VITE_DS_TOKEN=$DS_TOKEN

echo "Service on 127.0.0.1:$DS_PORT"
echo "Starting Vite..."
(cd ui && npm run dev > /tmp/ds-vite.log 2>&1) &
VITE_PID=$!
sleep 2

if [[ $WEB_ONLY == 1 ]]; then
  echo "Open http://localhost:5173 in your browser. Ctrl+C stops everything."
  wait $VITE_PID
else
  echo "Starting Electron shell..."
  (cd shell && DS_DEV=1 DS_PORT=$DS_PORT DS_TOKEN=$DS_TOKEN npx electron .)
fi
