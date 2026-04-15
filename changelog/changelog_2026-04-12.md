# Changelog — 2026-04-12

## Summary
Major economics and container-management session. Payment timing was fixed to ensure the simulation stays solvent, proactive container management was added with dynamic pricing, and the dashboard and CLI were cleaned up and made more configurable.

## Changes

### Economics: payment timing fix
- Customer payment delays (6/18/30h) now float ahead of vendor payment delays (12/24/36h), ensuring receivables arrive before payables are due and preventing cash drain during normal simulation runs.

### Proactive container management (PR #4)
- Renamed `WasteContainer.early_empty_cost_eur` → `base_early_empty_cost_eur` to make room for dynamic pricing.
- Added `compute_dynamic_early_empty_cost()`: high fill = cheaper (discounted to incentivize prevention), near scheduled pickup = expensive (just wait).
- New standalone endpoint `POST /api/v1/containers/{id}/early-empty` so the worker can trigger empties independently of an order.
- Worker now scans all containers each cycle and applies expected-value logic: empty proactively when `early_cost < penalty * fill_ratio` and `fill_ratio > 0.5`.
- Economics tracking: `overflow_prevented_count` and `overflow_penalty_avoided_eur` added to the economics model.
- Dashboard: "AT RISK" badge on containers approaching overflow; "Penalty Avoided" figure shown in the economics panel.
- PR review fixes: persistence migration uses `AliasChoices` for backward compat; dynamic cost is also applied for order-driven early-empties; `overflow_penalty_eur` is capped to avoid runaway values.

### Governance routing for proactive early-empties (uncommitted on main)
- `worker/unreal_worker.py`: `manage_containers()` now builds a guardrail context and calls `evaluate_action()` / Decision Center before triggering any proactive empty.
- APPROVE → trigger empty; REJECT → log skip with reasoning; anything else → HOLD and log.
- `group_id` is now threaded through from `run()` to `manage_containers()`.
- This change is **not yet committed** — see Open Items.

### Dashboard cleanup (PR #5)
- Removed the Guardrails tab from the dashboard; rule management lives in the `unreal_objects` repo, not here.
- Added `--order-interval` CLI flag to `uo-company-server` (default: 120s real-time between orders), making simulation pace configurable without code changes.

### Production branch
- Created a dedicated `production` branch for Railway deploy isolation; PRs targeting Railway deploys merge there rather than directly to main.

## Files Modified
- `company_api/` — payment delay constants; container economics model (base cost rename, dynamic cost function, new endpoint, economics counters).
- `support_company/models.py` — `WasteContainer` field rename + `AliasChoices` migration alias.
- `dashboard/src/` — Removed Guardrails tab component and route; added AT RISK badge and Penalty Avoided display.
- `company_api/cli.py` (or equivalent) — `--order-interval` flag added.
- `worker/unreal_worker.py` — governance routing for proactive early-empties (unstaged).

## Code Quality Notes
- **Tests: 49 passed, 0 failed** (full `pytest -v` run clean).
- **Dashboard lint**: no `lint` script defined in `dashboard/package.json`; only `dev`, `build`, `preview` are available. TypeScript errors would surface at build time (`tsc -b`).
- No debug print statements, stray TODOs, or commented-out code blocks observed in the diff.

## Open Items / Carry-over
- **Uncommitted change**: `worker/unreal_worker.py` governance routing for proactive early-empties is sitting unstaged on `main`. This should be committed and PR'd next session.
- **Dashboard lint script**: consider adding an ESLint step to `package.json` so quality checks can run in CI without requiring a full build.
- **Production branch strategy**: verify Railway is actually deploying from `production` branch and that the branch protection / PR flow is documented.
