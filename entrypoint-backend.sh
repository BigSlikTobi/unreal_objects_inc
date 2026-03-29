#!/usr/bin/env bash
set -euo pipefail

echo "Starting Rule Engine on :8001..."
uvicorn rule_engine.app:app --host 0.0.0.0 --port 8001 &
RE_PID=$!

echo "Starting Decision Center on :8002..."
uvicorn decision_center.app:app --host 0.0.0.0 --port 8002 &
DC_PID=$!

# Wait for both services to be ready
for port in 8001 8002; do
    for i in $(seq 1 60); do
        if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$port/docs', timeout=2)" 2>/dev/null; then
            echo "  Port $port ready"
            break
        fi
        sleep 0.5
    done
done

# Load the waste-company rule pack
echo "Loading rule pack..."
python3 -c "
import json, urllib.request

BASE = 'http://127.0.0.1:8001'
pack = json.loads(open('rule_packs/support_company.json').read())
req = urllib.request.Request(
    f'{BASE}/v1/groups',
    data=json.dumps({'name': pack['name'], 'description': pack['description']}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
with urllib.request.urlopen(req, timeout=30) as r:
    group = json.loads(r.read())
group_id = group['id']
print(f'Created group: {group_id}')

for rule in pack['rules']:
    req = urllib.request.Request(
        f'{BASE}/v1/groups/{group_id}/rules',
        data=json.dumps(rule).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        pass

# Write group_id to a file the company server can read
open('/tmp/rule_group_id.txt', 'w').write(group_id)
print(f'Rule pack loaded: {len(pack[\"rules\"])} rules into group {group_id}')
"

echo "Backend stack ready."

# Keep running until either process exits
wait -n $RE_PID $DC_PID
