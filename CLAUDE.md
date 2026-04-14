# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

`unreal_objects_inc` is a simulated waste-management company that stress-tests the [Unreal Objects](https://github.com/BigSlikTobi/unreal_objects) accountability infrastructure. It generates synthetic disposal orders, evaluates autonomous bot actions through Unreal Objects governance rules (Rule Engine + Decision Center), and provides a live dashboard to visualize the entire pipeline.

The `unreal_objects/` directory is a **git submodule** — treat it as an external dependency and never modify it from this repo.

## Architecture

### Data Flow

```
Generator (support_company/) → DisposalOrders → CompanyAPI (company_api/ :8010)
                                                        ↓
Dashboard (dashboard/ :5174) ← polls /api/v1/* ← CompanyAPI
                                                        ↓
                                    External Bot → POST /v1/decide → Decision Center (:8002)
                                                                          ↓
                                                                   Rule Engine (:8001)
```

### Packages

- **`support_company/`** — Domain models (`DisposalOrder`, `WasteContainer`, enums) and scenario generation (deterministic templates + optional LLM via OpenAI).
- **`company_api/`** — FastAPI server (:8010) that runs the simulation. Manages virtual clock, order lifecycle, container fleet, economics, approvals, and pricing. Serves the dashboard static build at `/` if `dashboard/dist/` exists.
- **`dashboard/`** — Standalone Vite + React + TypeScript + Tailwind CSS 4 app. Polls company server via Vite dev proxy (`/api` → `localhost:8010`). In production, set `VITE_API_BASE`. Uses a CSS design-token system (`index.css`) with `night` and `dawn` theme variants. Pages: Overview, Approvals, Orders (paginated table + detail modal), Containers (visual fill-level shapes), Pricing (grouped tile layout), Bot Activity, Vision. Sidebar is always collapsed behind a hamburger menu; theme toggle lives inside the sidebar. SVG assets (logo, favicon) are in `dashboard/src/assets/`.
- **`rule_packs/`** — JSON rule definitions loaded into Rule Engine at startup.

### Key Domain Model (`support_company/models.py`)

`DisposalOrder` is the central Pydantic model — fields include `declared_waste_type` (6 waste types), `quantity_m3`, `offered_price_eur`, `priority` (standard/urgent), `service_window` (same_day/next_day/scheduled), `hazardous_flag`, `contamination_risk`. The `to_evaluation_context()` method converts it to the flat dict expected by `POST /v1/decide`.

`WasteContainer` tracks the physical fleet. Key fields: `base_early_empty_cost_eur` (static base cost, renamed from `early_empty_cost_eur`), `overflow_penalty_eur` (capped penalty for overflowing), `fill_ratio`. Use `compute_dynamic_early_empty_cost(*, base_cost, fill_ratio, hours_to_pickup, overflow_penalty_eur)` to get the fill-adjusted cost (high fill = cheaper to incentivize prevention). Standalone emptying: `POST /api/v1/containers/{id}/early-empty` with body `{"bot_id": "..."}`.


`GeneratedScenario` bundles an order with its operational context, source event, expected bot action (`BotActionType`), and expected governance outcome (`ExpectedPath`: APPROVE/ASK_FOR_APPROVAL/REJECT).

### Scenario Generation Modes

The `--generator-mode` flag controls how orders are created:
- **template** — Fully deterministic from seed, no external calls.
- **llm** — OpenAI-generated realistic scenarios (requires `OPENAI_API_KEY`).
- **mixed** (default) — Half LLM, half template. Falls back to all-template if no API key.

## Commands

Requires **Python 3.11+** and **Node.js 18+**.

### Python Setup & Tests

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest -v                           # full suite
pytest tests/test_generator.py -v   # single test file
pytest -k "test_name" -v            # single test by name

```

Tests use `pytest-asyncio` (auto mode) and `pytest-httpx` for HTTP mocking. Config is in `pyproject.toml` under `[tool.pytest.ini_options]`.

### Company Server

```bash
uo-company-server --acceleration 10 --no-ai   # runs on :8010
```

The `--no-ai` flag uses template-only generation (no OpenAI key needed). `--acceleration` controls virtual clock speed. `--order-interval` sets real-time seconds between generated orders (default: 60).

### Backend Services (Unreal Objects submodule)

```bash
git submodule update --init   # if submodule is missing
bash scripts/start_full_stack.sh   # Rule Engine :8001, Decision Center :8002
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev      # dev server on :5174 (proxies /api → :8010)
npm run build    # production build → dist/
```

### Full Local Stack

Run in three terminals:
1. `bash scripts/start_full_stack.sh` — backend services
2. `uo-company-server --acceleration 10 --no-ai` — company simulation
3. `cd dashboard && npm run dev` — dashboard at http://localhost:5174

## Railway Deployment (Cloud)

The stack splits across two Railway projects:

- **`unreal_objects` project** — Rule Engine, Decision Center, MCP, UI. Deployed directly from the [unreal_objects](https://github.com/BigSlikTobi/unreal_objects) repo.
- **`unreal_objects_inc` project** — Two services:

| Service | Dockerfile | Port | Public URL |
|---------|-----------|------|------------|
| `company` | `Dockerfile.company.api` | 8010 | `unrealobjectsinc.up.railway.app` |
| `dashboard` | `Dockerfile.dashboard` | 8081 | `dashboard-production-fcf4.up.railway.app` |

The company service connects to the external unreal_objects services via their public URLs:
- Rule Engine: `https://ruleengine-production-d6fe.up.railway.app`
- Decision Center: `https://decisioncenter-production-1c81.up.railway.app`

The bot worker is developed and deployed from a separate repository. It connects to the company API and Decision Center via their public Railway URLs.

See `docs/deployment-railway.md` for the full step-by-step guide and `railway.toml` for the complete env var matrix.

## Key Design Decisions

- **Submodule is read-only**: All `unreal_objects/` modifications must go through the upstream repo. This harness only consumes its APIs.
- **Dashboard is standalone**: Separate `package.json` and Vite config at `dashboard/`, not inside the submodule's `ui/`. This avoids submodule coupling.
- **Vite dev proxy**: The dashboard proxies `/api` to the company server during development, eliminating CORS configuration.
- **Deterministic generation**: Case generators use seeds for reproducible runs (`seed=42` default).
- **Company API serves dashboard**: When `dashboard/dist/` exists, the FastAPI app mounts it as a catch-all SPA route, enabling single-process deployment.
- **One-port-per-Railway-service constraint**: The reason Rule Engine and Decision Center are split into separate Railway services is that Railway only exposes one port per service, and the admin UI needs browser access to both.
- **Split Railway projects**: The Unreal Objects infrastructure (Rule Engine, Decision Center, MCP, UI) deploys from the `unreal_objects` repo into its own Railway project. This repo only deploys the company simulation, which connects to those services via public HTTPS URLs.
- **Production branch**: Railway deploys from the `production` branch of this repo, not `main`. PRs for Railway releases target `production`; feature work merges to `main` first.
- **Bot lives in a separate repo**: The autonomous bot worker was extracted into its own repository to enforce the trust boundary — the bot is an independent agent and should not share a codebase with the company it operates against.
