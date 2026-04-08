# Changelog — 2026-04-08

## Summary
Fixed a critical bug in `company_api/service.py` that caused the simulated company to go bankrupt on every run: receivables matured but were never collected into `cash_balance_eur` after a server restart, so the company had zero cash inflow while overhead and payables continued to drain it.

## Changes
- **Fix: virtual-clock rewind on restart blocked receivables collection**
  - `_persist_state_locked` now writes `virtual_now` (the current virtual timestamp) to the state snapshot alongside the existing `virtual_start`.
  - `_load_persisted_state` now anchors `_virtual_start` to the persisted `virtual_now` instead of the original simulation epoch. This ensures `_virtual_now()` returns a time ≥ `_last_financial_update` immediately after restart, so the early-return guard in `_advance_financials_locked` no longer short-circuits the receivables collection loop.
  - Backward-compatible: state files without `virtual_now` fall back to `virtual_start`, the previous behaviour.

## Files Modified
- `company_api/service.py` — added `virtual_now` field to persistence snapshot; changed `_load_persisted_state` to resume virtual clock from persisted `virtual_now` rather than rewinding to the original simulation start.

## Code Quality Notes
- `pytest -v`: 43/43 tests passed (0 failures, 0 warnings).
- No linting run required — only Python backend changed, no dashboard/UI files modified.
- No debug statements, TODO markers, or commented-out code found in the changed file.

## Open Items / Carry-over
- **Change 3 from plan (not implemented):** The plan recommended adding a comment to `_reset_after_bankruptcy_locked` explaining that in-flight receivables are intentionally wiped on insolvency. This is a cosmetic improvement only; the root bug is fixed. Can be picked up in a future session.
- **Soak-test verification:** A long-running end-to-end smoke test (full local stack, 10x acceleration, ≥5 min) was not run as part of this session. Recommend validating on Railway or locally before declaring the fix production-confirmed.
