# Changelog — 2026-03-29

## Summary
Full Railway cloud deployment of the unreal_objects_inc stack was planned, implemented, debugged, and confirmed working. The original 3-service architecture was refactored mid-day into a 5-service split so that the Unreal Objects admin UI can reach both the Rule Engine and Decision Center over public URLs.

## Changes

### Railway Deployment (initial architecture — 3 services)
- Added `Dockerfile.backend` (combined Rule Engine + Decision Center) with `entrypoint-backend.sh` that starts both processes, waits for readiness, loads the rule pack, and keeps both processes alive with `wait -n`.
- Added `Dockerfile.company` installing Node.js alongside Python to build the React dashboard at image-build time; `entrypoint-company.sh` translates env vars into `uo-company-server` CLI flags, including optional `CASES`, `PUBLIC_VOTING`, `OPERATOR_AUTH`, and `OPERATOR_TOKEN` env vars.
- Added `Dockerfile.mcp` for the MCP Server service.
- Added `railway.toml` describing the 5-service topology and all required environment variables with inline documentation.
- Added `docs/deployment-railway.md` (step-by-step guide).
- Fixed submodule cloning: switched all Dockerfiles from `git submodule update --init` to `pip install git+https://github.com/BigSlikTobi/unreal_objects.git` because Railway does not clone submodules.
- Fixed rule pack path: changed hardcoded relative path to `/app/rule_packs/support_company.json` for the containerised company server.
- Fixed rule pack auth: `entrypoint-backend.sh` reads `INTERNAL_API_KEY` and passes it as `X-Internal-Key` header when creating the rule group.
- Fixed dashboard path resolution: Dockerfile.company copies `dashboard/` before build so the path is consistent inside the container.
- Added CORS fixes: forced rebuild of rule-engine and decision-center images to pick up CORS policy changes from the upstream `unreal_objects` package.

### Architecture split — Rule Engine and Decision Center become separate services
- The Unreal Objects admin UI (`ui/`) needs to issue browser-side requests to the Rule Engine. Railway exposes one port per service, so the combined backend container cannot surface both services publicly.
- Added `Dockerfile.rule-engine` (standalone Rule Engine service): installs from GitHub, copies rule packs, uses `entrypoint-rule-engine.sh`.
- Added `entrypoint-rule-engine.sh`: starts Rule Engine, polls `/docs` until ready, then loads the waste-company rule pack via the HTTP API (respects `INTERNAL_API_KEY`).
- Added `Dockerfile.decision-center` (standalone Decision Center service): minimal — installs from GitHub and starts `uvicorn`.
- Added `Dockerfile.ui`: multi-stage Node.js build that clones the `unreal_objects` repo, builds the Vite app with `VITE_RULE_ENGINE_BASE_URL` / `VITE_DECISION_CENTER_BASE_URL` build args, and serves the static dist with `serve`.
  - Added `ca-certificates` to the UI Dockerfile's apt install so HTTPS git clone succeeds in the build stage.
- Updated `railway.toml` to document all 5 services, their Dockerfiles, and the full env var matrix.
- Added `CASES` env var support to `entrypoint-company.sh` (conditionally passes `--cases` flag).

### company_api/app.py
- Minor additions to support deployment-mode-aware configuration (changes introduced within earlier commits in today's series).

## Files Modified
- `Dockerfile.backend` — old combined backend; updated with GitHub pip install and rule pack loading
- `Dockerfile.company` — Node.js + Python image for company server + dashboard build
- `Dockerfile.decision-center` — new standalone Decision Center service (v2)
- `Dockerfile.mcp` — MCP Server service
- `Dockerfile.rule-engine` — new standalone Rule Engine service (v3)
- `Dockerfile.ui` — new Unreal Objects admin UI service
- `entrypoint-backend.sh` — starts both RE + DC, loads rule pack, waits with `wait -n`
- `entrypoint-company.sh` — translates env vars to CLI flags; added `CASES` support
- `entrypoint-rule-engine.sh` — new; starts RE, waits for readiness, loads rule pack
- `railway.toml` — rewritten to document 5-service topology and all env vars
- `company_api/app.py` — minor deployment-mode configuration additions

## Code Quality Notes
- Tests: **38 passed, 0 failed** (`pytest -v`). Full suite passes cleanly.
- Linting: Dashboard has no new ESLint issues (pre-existing 2 errors + 2 warnings in `ChatInterface.tsx` / `AgentAdminPanel.tsx` are unchanged).
- No TODO/FIXME/HACK comments introduced in any of today's new files.
- `print()` calls in entrypoint scripts are intentional startup logging (not debug noise).
- `Dockerfile.backend` and `entrypoint-backend.sh` are now superseded by the split architecture but remain in the repo as a reference / fallback. Consider removing them once the 5-service deployment is confirmed stable.

## Open Items / Carry-over
- `docs/deployment-railway.md` still describes the old 3-service architecture. It should be updated to reflect the current 5-service split (rule-engine, decision-center, company, mcp, ui) — done in today's commit.
- `Dockerfile.backend` / `entrypoint-backend.sh` are dead code now that rule-engine and decision-center are separate services. Evaluate whether to keep as fallback or remove.
- Railway's ephemeral storage means rules and decision logs reset on every redeploy. A PostgreSQL persistence layer is a future improvement.
- Bot worker on Raspberry Pi requires `COMPANY_API_URL` and `DECISION_CENTER_URL` env vars pointing at the live Railway public URLs — these must be configured manually on the Pi.
- The `VITE_RULE_ENGINE_BASE_URL` and `VITE_DECISION_CENTER_BASE_URL` build-time env vars for `Dockerfile.ui` must be set in Railway before deploying — if missing, the UI will build with empty strings and fail at runtime.
