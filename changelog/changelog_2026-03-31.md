# Changelog — 2026-03-31

## Summary
The Railway deployment was significantly simplified: redundant Dockerfiles and entrypoint scripts for Rule Engine, Decision Center, MCP, and the Admin UI were removed from this repo now that the `unreal_objects` upstream ships its own Dockerfiles. Concurrently, three production bugs were fixed — `RULE_GROUP_ID` was not being forwarded to the company server, and `INTERNAL_API_KEY` was not sent as the `X-Internal-Key` header on two separate call paths — causing worker evaluation failures and 401/502 errors in production.

## Changes

### Architecture slim-down
- Removed 7 files that are now owned by the `unreal_objects` repo and its Dockerfiles:
  - `Dockerfile.rule-engine`
  - `Dockerfile.decision-center`
  - `Dockerfile.mcp`
  - `Dockerfile.ui`
  - `Dockerfile.backend`
  - `Dockerfile.dashboard`
  - `entrypoint-backend.sh`
- Updated the `unreal_objects` submodule pointer to the latest upstream commit (`524481d`), which includes the upstream Dockerfiles under `unreal_objects/docker/`.

### Railway restructure — split into two projects
- The 5-service Railway project (`athletic-spirit`) is now split:
  - **`unreal_objects` project**: Rule Engine, Decision Center, MCP, UI — deployed directly from the `unreal_objects` repo.
  - **`unreal_objects_inc` project**: Company API + Dashboard only — the single remaining service in this repo.
- `railway.toml` rewritten to document the single-service topology, external URLs for Rule Engine and Decision Center, and the local worker configuration.
- `docs/deployment-railway.md` rewritten to match the new 2-project architecture: removed now-irrelevant multi-service setup steps, updated env var table to reference external `RULE_ENGINE_URL` / `DECISION_CENTER_URL`, and compressed the guide to only cover the company service.
- `CLAUDE.md` updated: replaced the 5-service table with the 2-project topology, added a `Split Railway projects` design decision entry.

### Bug fixes
- **`entrypoint-company.sh`**: Added conditional forwarding of `RULE_GROUP_ID` via `--rule-group-id`. Without this, the company server started with a `null` rule group and the worker could not evaluate orders against governance rules.
- **`company_api/service.py` (finalize approval)**: Added `X-Internal-Key` header to the Decision Center call on the approval-finalization path. Missing header caused 502 responses when operators approved waiting orders.
- **`bot_adapter/governance.py` (GovernanceClient)**: Added `X-Internal-Key` header to `POST /v1/decide` calls. Missing header caused 401 responses when the bot worker submitted actions for evaluation.
  - Added `--internal-api-key` CLI option wired through `cli.py` → `app.py` → `service.py` → `GovernanceClient`.

## Files Modified
- `Dockerfile.backend` — deleted (superseded by upstream)
- `Dockerfile.dashboard` — deleted (superseded by upstream)
- `Dockerfile.decision-center` — deleted (superseded by upstream)
- `Dockerfile.mcp` — deleted (superseded by upstream)
- `Dockerfile.rule-engine` — deleted (superseded by upstream)
- `Dockerfile.ui` — deleted (superseded by upstream)
- `entrypoint-backend.sh` — deleted (superseded by upstream)
- `entrypoint-company.sh` — added `RULE_GROUP_ID` and `INTERNAL_API_KEY` conditional CLI flag forwarding
- `railway.toml` — rewritten: single-service topology with external URLs
- `docs/deployment-railway.md` — rewritten: 2-project architecture, condensed to company service only
- `CLAUDE.md` — updated Railway section and Key Design Decisions to reflect 2-project split
- `unreal_objects` (submodule) — pointer updated to `524481d`

## Code Quality Notes
- Tests: **39 passed, 0 failed** (`pytest -v`). One new test was counted vs yesterday (39 vs 38), suggesting a test was added upstream or in a prior commit this session.
- Linting: No Python or shell files changed today contain new TODO/FIXME/HACK comments or debug print statements.
- UI linting: No dashboard files were modified today. Pre-existing ESLint errors in `AgentAdminPanel.tsx` and `ChatInterface.tsx` remain unchanged (not new issues).
- The `entrypoint-mcp.sh` and `entrypoint-rule-engine.sh` files remain in the repo root — these are referenced by the upstream Dockerfiles during their builds and should be retained.

## Open Items / Carry-over
- Railway ephemeral storage: Rule Engine rules and Decision Center logs reset on every redeploy. A PostgreSQL persistence layer remains a future improvement.
- The bot worker on Raspberry Pi must have `COMPANY_API_URL`, `DECISION_CENTER_URL`, and `INTERNAL_API_KEY` env vars configured manually to point at the live Railway public URLs.
- `entrypoint-mcp.sh` is still in this repo — confirm whether the upstream `unreal_objects` Dockerfile references it or if it can be deleted in a future cleanup.
