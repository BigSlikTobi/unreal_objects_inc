# unreal_objects_inc Setup Guide

This is the exact step-by-step process for starting `unreal_objects_inc` with an external bot on the same network.

## 1. One-Time Setup

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
git submodule update --init
cd dashboard && npm install && cd ..
cd unreal_objects
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ..
```

Create a local `.env` file in the repo root if you want mixed LLM-plus-template order generation:

```bash
OPENAI_API_KEY=...
```

## 2. Start Unreal Objects

Open terminal 1:

```bash
bash scripts/start_full_stack.sh
```

This starts:

- Rule Engine on `:8001`
- Decision Center on `:8002`
- MCP Server on `:8000`

The Rule Engine now stores its live rules in:

```text
unreal_objects/data/rule_engine_store.json
```

That file is local runtime data only. It is not committed to git, but it does
survive service restarts on the machine or server where Unreal Objects is
running.

## 3. Load the Waste Rule Pack

After every Unreal Objects restart, load the current local waste-company rules:

```bash
python3 scripts/load_rule_pack.py
```

That command prints a fresh `group_id`. Save it. You need it for MCP enrollment.

## 4. Find Your Mac's LAN IP

The external bot is on another machine, so do not use `127.0.0.1`.

On your Mac:

```bash
ipconfig getifaddr en0
```

If needed:

```bash
ifconfig | rg "inet "
```

Assume the result is:

```text
192.168.178.21
```

Use that IP from the bot machine.

## 5. Start the Company Server

Open terminal 2.

Continuous mode, endless generation, 24x speed:

```bash
source .venv/bin/activate
uo-company-server --host 0.0.0.0 --port 8010
```

Fixed batch mode:

```bash
source .venv/bin/activate
uo-company-server --host 0.0.0.0 --port 8010 --cases 24 --seed 42
```

Bounded rolling mode:

```bash
source .venv/bin/activate
uo-company-server --host 0.0.0.0 --port 8010 --cases 1000 --rolling --seed 42
```

Notes:

- if `--cases` is omitted, the company keeps generating disposal orders indefinitely
- if `--cases` is used without `--rolling`, all seeded orders are created immediately
- `--cases N --rolling` trickles orders in over time and stops after `N` total orders
- rolling generation targets roughly `1000` orders per simulated day by default
- at the default clock speed this means a new order roughly every `2.7s` to `4.5s` in real time
- continuous mode runs at `24x` virtual speed by default, so `1` real hour equals `1` simulated day
- continuous mode uses `--generator-mode mixed` by default, so the live stream blends LLM-generated and deterministic orders
- if the Unreal Objects Rule Engine is reachable, the dashboard auto-discovers live groups and mirrors them
- `--rule-group-id` is optional and only needed if you want to pin the dashboard to one specific group
- `0.0.0.0` is required so the external bot can reach the company server

## 6. Start the Company Dashboard

Open terminal 3:

```bash
cd dashboard
npm run dev
```

Open:

- Company dashboard: `http://localhost:5174`
- Unreal Objects UI: `http://localhost:5173`

## 7. Create the MCP Agent

The local MCP admin API key is:

```text
admin-secret
```

Create the agent:

```bash
curl -s http://127.0.0.1:8000/v1/admin/agents \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Key: admin-secret' \
  -d '{
    "name": "openclaw-waste-bot",
    "description": "External waste-operations bot for unreal_objects_inc"
  }'
```

Save the returned `agent_id`.

Create a one-time enrollment token:

```bash
curl -s http://127.0.0.1:8000/v1/admin/agents/<AGENT_ID>/enrollment-tokens \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Key: admin-secret' \
  -d '{
    "credential_name": "openclaw-lan",
    "default_group_id": "<GROUP_ID>",
    "allowed_group_ids": ["<GROUP_ID>"]
  }'
```

Save the returned `enrollment_token`.

Important:

- the enrollment token is one-time only
- MCP auth state is stored in memory only
- after restarting the MCP server, you need a fresh enrollment flow

## 8. Connect the External Bot

On the bot machine, use your Mac's LAN IP.

Check bootstrap instructions:

```bash
curl http://192.168.178.21:8000/instructions
```

Enroll:

```bash
curl -s http://192.168.178.21:8000/v1/agents/enroll \
  -H 'Content-Type: application/json' \
  -d '{"enrollment_token":"<ENROLLMENT_TOKEN>"}'
```

Save:

- `client_id`
- `client_secret`

Exchange for an access token:

```bash
curl -s http://192.168.178.21:8000/oauth/token \
  -H 'Content-Type: application/json' \
  -d '{
    "grant_type":"client_credentials",
    "client_id":"<CLIENT_ID>",
    "client_secret":"<CLIENT_SECRET>"
  }'
```

Use the returned bearer token with:

```text
http://192.168.178.21:8000/mcp
```

## 9. Give the Bot the Company APIs

The bot should use these endpoints.

List open disposal orders:

```text
GET http://192.168.178.21:8010/api/v1/orders?status=open
```

Claim an order:

```text
POST http://192.168.178.21:8010/api/v1/orders/{order_id}/claim
```

Body:

```json
{"bot_id":"openclaw-waste-bot"}
```

Submit a result:

```text
POST http://192.168.178.21:8010/api/v1/orders/{order_id}/result
```

Body:

```json
{
  "bot_id": "openclaw-waste-bot",
  "outcome": "APPROVAL_REQUIRED",
  "bot_action": "rent_container",
  "action_payload": {
    "target_waste_type": "paper",
    "added_capacity_m3": 16,
    "extra_rental_cost_eur": 520,
    "route_quantity_m3": 6
  },
  "decision_summary": "I chose to rent extra paper capacity so the order can be accepted without overflowing the current fleet.",
  "resolution": "Waiting for approval inside Unreal Objects before renting the extra container.",
  "request_id": "req_123",
  "matched_rules": ["Large extra rentals require approval"]
}
```

Allowed outcome values:

- `APPROVED`
- `REJECTED`
- `APPROVAL_REQUIRED`

Supported `bot_action` values in v1:

- `accept_and_route`
- `reject_order`
- `rent_container`
- `schedule_early_empty`

Optional pricing and planning context:

```text
GET http://192.168.178.21:8010/api/v1/pricing
GET http://192.168.178.21:8010/api/v1/pricing?waste_type=paper
```

This pricing API exposes:

- market-reference customer quotes
- company rental options
- company early-empty options

Important:

- the bot should decide the action first
- then it should evaluate that chosen action with Unreal Objects
- this company server does not own the approval workflow anymore
- if the guardrails require approval, that approval happens in Unreal Objects and the bot should only send the final company result once the action state is resolved

## 10. Quick Health Checks

From your Mac:

```bash
curl http://127.0.0.1:8000/instructions
curl http://127.0.0.1:8010/v1/health
curl -s http://127.0.0.1:8010/api/v1/orders?status=open | jq
curl -s http://127.0.0.1:8010/api/v1/containers | jq
curl -s http://127.0.0.1:8010/api/v1/economics | jq
curl -s http://127.0.0.1:8010/api/v1/pricing | jq
```

From the bot machine:

```bash
curl http://192.168.178.21:8000/instructions
curl http://192.168.178.21:8010/v1/health
```

## 11. Common Mistakes

- Using `127.0.0.1` on the bot machine
- Forgetting `--host 0.0.0.0` for `uo-company-server`
- Forgetting to reload the rule pack after restarting Unreal Objects
- Trying `/mcp` before enroll and OAuth
- Reusing a one-time enrollment token
- Posting bot results without `bot_action` and `action_payload`
