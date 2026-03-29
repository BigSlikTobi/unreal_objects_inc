# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## What This Project Does

`unreal_objects_inc` is the stress-test harness and showcase layer for the [Unreal Objects](https://github.com/BigSlikTobi/unreal_objects) accountability infrastructure. It generates synthetic support cases for a virtual company, evaluates them through Unreal Objects governance rules, and provides a live dashboard to visualize the entire pipeline.

The `unreal_objects/` directory is a **git submodule** — treat it as an external dependency and never modify it from this repo.

## Architecture

```
unreal_objects_inc/
├── support_company/     Case generators + domain models (Python)
├── bot_adapter/         Maps cases → Unreal Objects evaluation inputs
├── stress_runner/       CLI-driven batch evaluation + reporting
├── rule_packs/          JSON rule definitions loaded into Rule Engine
├── dashboard/           Live showcase UI (React + Vite, standalone app)
├── scripts/             Shell helpers (start_full_stack.sh)
├── tests/               pytest test suite
├── reports/             Generated output
└── unreal_objects/      Git submodule — core backend services
```

### Key Domain Models (`support_company/models.py`)

- `SupportCase` — Pydantic model with fields: case_type, customer_tier, priority, risk_score, requested_action, channel, account_age_days, order_value, refund_amount, etc.
- Enums: `CaseType` (5 families), `CustomerTier` (basic/premium/vip), `Priority` (low/medium/high/urgent), `Channel` (email/chat/phone/api), `ExpectedPath` (APPROVE/ASK_FOR_APPROVAL/REJECT)
- `to_evaluation_context()` converts a case to the flat dict expected by `POST /v1/decide`

### Dashboard (`dashboard/`)

Standalone Vite + React + TypeScript + Tailwind CSS app. Independently deployable — has its own `package.json` and build pipeline, no dependency on the submodule's `ui/`.

Polls the company server (port 8010) via Vite dev proxy (`/api` → `localhost:8010`). In production, set `VITE_API_BASE` to the company server URL.

**Polling intervals:** clock 2s, status/cases 5s, rules 30s.

**Components:** TopBar (virtual clock + connection), KpiStrip (4 metric cards), CaseFeed (scrollable list, max 50), CaseCard (expandable detail), BotActivity (assigned cases), RulesPanel (active rules + edge cases), DecisionOutcomes (APPROVE/REJECT/ASK counters + ratio bars).

## Commands

Requires **Python 3.11+** and **Node.js 18+**.

### Python Setup & Tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Tests
pytest -v                           # full suite
pytest tests/test_generator.py -v   # generator tests only

# Stress test CLI
uo-stress-company --cases 50 --seed 42
```

### Start Backend Services

```bash
# Start the unreal_objects submodule services (Rule Engine :8001, Decision Center :8002)
bash scripts/start_full_stack.sh

# If submodule is missing
git submodule update --init
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev      # dev server on :5174 (proxies /api → :8010)
npm run build    # production build → dist/
npm run preview  # preview production build
```

### Full Local Stack (for dashboard development)

```bash
# Terminal 1: backend services
bash scripts/start_full_stack.sh

# Terminal 2: company server (from the unreal_objects submodule)
cd unreal_objects && source .venv/bin/activate
uo-company-server --acceleration 10 --no-ai

# Terminal 3: dashboard
cd dashboard && npm run dev
# Open http://localhost:5174
```

## Key Design Decisions

- **Submodule is read-only**: All `unreal_objects/` modifications must go through the upstream repo. This harness only consumes its APIs.
- **Dashboard is standalone**: Separate `package.json` and Vite config at `dashboard/`, not inside the submodule's `ui/`. This avoids submodule coupling and allows independent deployment.
- **Vite dev proxy**: The dashboard proxies `/api` to the company server during development, eliminating the need for CORS configuration on the backend.
- **Deterministic generation**: Case generators use seeds for reproducible stress test runs (`seed=42` default).
