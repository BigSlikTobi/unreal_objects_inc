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
                                    bot_adapter/ → POST /v1/decide → Decision Center (:8002)
                                                                          ↓
                                                                   Rule Engine (:8001)
```

### Packages

- **`support_company/`** — Domain models (`DisposalOrder`, `WasteContainer`, enums) and scenario generation (deterministic templates + optional LLM via OpenAI).
- **`company_api/`** — FastAPI server (:8010) that runs the simulation. Manages virtual clock, order lifecycle, container fleet, economics, approvals, and pricing. Serves the dashboard static build at `/` if `dashboard/dist/` exists.
- **`bot_adapter/`** — Maps bot actions to Unreal Objects evaluation requests. `GovernanceClient` calls `POST /v1/decide` on Decision Center. `rule_loader.py` uploads rule packs to Rule Engine.
- **`stress_runner/`** — CLI batch runner (`uo-stress-company`) that generates N orders, evaluates them, and saves JSON reports to `reports/`.
- **`dashboard/`** — Standalone Vite + React + TypeScript + Tailwind CSS 4 app. Polls company server via Vite dev proxy (`/api` → `localhost:8010`). In production, set `VITE_API_BASE`.
- **`rule_packs/`** — JSON rule definitions loaded into Rule Engine at startup.

### Key Domain Model (`support_company/models.py`)

`DisposalOrder` is the central Pydantic model — fields include `declared_waste_type` (6 waste types), `quantity_m3`, `offered_price_eur`, `priority` (standard/urgent), `service_window` (same_day/next_day/scheduled), `hazardous_flag`, `contamination_risk`. The `to_evaluation_context()` method converts it to the flat dict expected by `POST /v1/decide`.

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

# Stress test CLI
uo-stress-company --cases 50 --seed 42
uo-stress-company --generator-mode template --cases 10  # no LLM needed
```

Tests use `pytest-asyncio` (auto mode) and `pytest-httpx` for HTTP mocking. Config is in `pyproject.toml` under `[tool.pytest.ini_options]`.

### Company Server

```bash
uo-company-server --acceleration 10 --no-ai   # runs on :8010
```

The `--no-ai` flag uses template-only generation (no OpenAI key needed). `--acceleration` controls virtual clock speed.

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

## Key Design Decisions

- **Submodule is read-only**: All `unreal_objects/` modifications must go through the upstream repo. This harness only consumes its APIs.
- **Dashboard is standalone**: Separate `package.json` and Vite config at `dashboard/`, not inside the submodule's `ui/`. This avoids submodule coupling.
- **Vite dev proxy**: The dashboard proxies `/api` to the company server during development, eliminating CORS configuration.
- **Deterministic generation**: Case generators use seeds for reproducible runs (`seed=42` default).
- **Company API serves dashboard**: When `dashboard/dist/` exists, the FastAPI app mounts it as a catch-all SPA route, enabling single-process deployment.
