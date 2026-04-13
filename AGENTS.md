# Repository Guidelines

## What This Repo Is

`unreal_objects_inc` simulates a real company that uses an autonomous support bot with Unreal Objects guardrails.

The company story is:

1. The company creates rules in `unreal_objects`
2. The company exposes those rules through an MCP
3. The company gives that MCP to its autonomous bot
4. This repo simulates company operations and raw business events
5. The intake layer turns those events into support cases
6. The bot handles those cases autonomously under the guardrails
7. Cases that need human sign-off are parked in the company approval desk
8. Company operators review those parked cases in the dashboard

Points 1 to 3 happen outside this repo. This repo owns points 4 to 7.

The `unreal_objects/` directory is a git submodule. Treat it as an external, read-only dependency from this repo unless the task explicitly requires submodule work.

## Project Structure & Module Organization

- `company_api/`: company-owned API server for dashboard data, bot processing, and the approval desk
- `support_company/`: operations simulation, raw event generation, intake models, and domain models
- `rule_packs/`: JSON rule definitions loaded into Unreal Objects
- `dashboard/`: standalone React + Vite + TypeScript + Tailwind UI for company operations
- `scripts/`: shell helpers such as `start_full_stack.sh`
- `tests/`: `pytest` suite for simulator and company workflow behavior
- `reports/`: generated run output
- `unreal_objects/`: external governance system submodule

Important runtime behavior:

- The bot is autonomous. This repo should not manually guide individual decisions.
- Prefer the LLM-first operations -> event -> case pipeline when `OPENAI_API_KEY` is available.
- Unreal Objects decides whether an action is approved, rejected, or needs human approval.
- `ASK_FOR_APPROVAL` cases are parked in the company approval desk while the bot continues with other work.
- Company review is handled from the dashboard through the company API.

## Build, Test, and Development Commands

Requires Python 3.11+ and Node.js 18+.

- `python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`: install the Python environment
- `bash scripts/start_full_stack.sh`: start the Unreal Objects Rule Engine and Decision Center
- `uo-company-server --cases 24 --seed 42 --acceleration 10`: start the simulated company API on port 8010
- `pytest -v`: run the full test suite
- `pytest tests/test_generator.py -v`: run support-case generator tests only
- `pytest tests/test_company_service.py -v`: run approval-desk and company workflow tests
- `git submodule update --init`: fetch the nested `unreal_objects/` dependency if missing
- `cd dashboard && npm install`: install dashboard dependencies
- `cd dashboard && npm run dev`: start the dashboard on port 5174 with `/api` proxied to `localhost:8010`
- `cd dashboard && npm run build`: build the dashboard
- `cd dashboard && npm run preview`: preview the production build

For full local development:

1. Run `bash scripts/start_full_stack.sh`
2. Run `uo-company-server --cases 24 --seed 42 --acceleration 10`
3. Run `cd dashboard && npm run dev`
4. Open `http://localhost:5174`

## Coding Style & Naming Conventions

Use 4-space indentation, type-friendly Python, and small focused modules. Keep filenames and functions in `snake_case`, classes and enums in `PascalCase`, and constants in `UPPER_SNAKE_CASE`.

For dashboard work, keep the frontend standalone inside `dashboard/`. Do not move company UI work into the `unreal_objects` submodule UI.

When working on company workflow behavior:

- model real company states explicitly: `open`, `assigned`, `waiting_approval`, `resolved`
- keep approval metadata first-class on cases and API DTOs
- prefer deterministic seeds and predictable simulator behavior

## Testing Guidelines

Testing uses `pytest`, `pytest-asyncio`, and `pytest-httpx`. Add regression coverage for:

- seeded case generation
- bot-to-governance mapping
- parked approval queue behavior
- company review and resolution flow
- dashboard-facing API payloads

Prefer deterministic inputs like `seed=42` so failures are reproducible.

If a change affects the Unreal Objects handoff:

1. run the relevant local unit tests first
2. validate the dashboard flow against the local stack when practical

## Commit & Pull Request Guidelines

Use short imperative commit subjects and keep commits atomic.

In pull requests:

- describe the company workflow or operator scenario changed
- list the validation commands you ran
- link any related issue
- include screenshots or report snippets if the dashboard or approval desk behavior changed
- call out any required `unreal_objects/` submodule updates

## Design Constraints

- Treat `unreal_objects/` as read-only from this repository
- Keep the dashboard standalone under `dashboard/`
- The dashboard is not just a showcase; it is the company’s operational surface for parked approvals
- `ASK_FOR_APPROVAL` cases must have a clear place where company operators can see and handle them
- The bot must continue with other work while approval-needed cases are parked
