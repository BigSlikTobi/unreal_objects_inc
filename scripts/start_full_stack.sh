#!/usr/bin/env bash
# Start the Unreal Objects backend services used by the simulated company.
# Assumes unreal_objects is cloned as a submodule at ./unreal_objects/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."
UO_DIR="$ROOT/unreal_objects"

if [ ! -d "$UO_DIR" ]; then
    echo "Error: unreal_objects not found at $UO_DIR"
    echo "Run: git submodule update --init"
    exit 1
fi

echo "==> Starting Unreal Objects backend stack..."
if [ -f "$UO_DIR/scripts/start_backend_stack.sh" ]; then
    bash "$UO_DIR/scripts/start_backend_stack.sh"
else
    echo "Starting Rule Engine on :8001..."
    cd "$UO_DIR" && source .venv/bin/activate 2>/dev/null || true
    uvicorn rule_engine.app:app --port 8001 &
    echo "Starting Decision Center on :8002..."
    uvicorn decision_center.app:app --port 8002 &
    cd "$ROOT"
fi

echo "==> Waiting for services..."
for port in 8001 8002; do
    for i in $(seq 1 30); do
        if curl -s "http://127.0.0.1:$port/docs" > /dev/null 2>&1; then
            echo "  Port $port ready"
            break
        fi
        sleep 0.5
    done
done

echo "==> Backend stack is up."
echo "    Start the company simulation with:"
echo "    uo-company-server --cases 24 --seed 42 --acceleration 24"
