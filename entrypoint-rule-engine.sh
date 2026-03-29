#!/usr/bin/env bash
set -euo pipefail

RE_PORT="${PORT:-8001}"

echo "Starting Rule Engine on :${RE_PORT}..."
uvicorn rule_engine.app:app --host 0.0.0.0 --port "$RE_PORT" &
RE_PID=$!

# Wait for Rule Engine to be ready
for i in $(seq 1 60); do
    if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$RE_PORT/docs', timeout=2)" 2>/dev/null; then
        echo "  Rule Engine ready"
        break
    fi
    sleep 0.5
done

# Load the waste-company rule pack
echo "Loading rule pack..."
python3 -c "
import json, os, urllib.request

BASE = 'http://127.0.0.1:${RE_PORT}'
API_KEY = os.environ.get('INTERNAL_API_KEY', '')
pack = json.loads(open('rule_packs/support_company.json').read())

headers = {'Content-Type': 'application/json'}
if API_KEY:
    headers['X-Internal-Key'] = API_KEY

req = urllib.request.Request(
    f'{BASE}/v1/groups',
    data=json.dumps({'name': pack['name'], 'description': pack['description']}).encode(),
    headers=headers,
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
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        pass

print(f'Rule pack loaded: {len(pack[\"rules\"])} rules into group {group_id}')
"

echo "Rule Engine ready."
wait $RE_PID
