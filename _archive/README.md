# ARCHIVE — DO NOT EDIT OR RUN

Historical snapshots of runners and infrastructure, preserved for reference
only. They have **already drifted** from production (e.g. they still use
`covariance_type="full"` for intraday HMMs and lack the 2026-07 NaN guards).

**Production code lives in the repo root** — that is what `scheduler.py` and
`.github/workflows/monitor.yml` execute. Never import from, edit, or run
anything under `_archive/`.

Moved here 2026-07-11 from `files/` and `updates_in_trading_system/`.
