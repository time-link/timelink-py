# Session state / handoff

Last updated: 2026-10-16 (end of consolidation session). Read this
together with [README.md](README.md) and [roadmap.md](roadmap.md).

## Repos and paths

| What | Where |
|---|---|
| timelink-py main checkout | `/Users/jrc/develop/timelink-py` (on `test-gsilva-web-merge`, clean) |
| **Worktree for web work** | `/Users/jrc/develop/timelink-web-dev` (branch `timelink-web-dev`) |
| Legacy Java MHK (reference, read-only) | `/Users/jrc/develop/mhk` (branch `master`) |
| Shared venv | `/Users/jrc/develop/timelink-py/.venv` (Python 3.12; used to run worktree tests) |

## Branch state at handoff

`timelink-web-dev` (local only, **not pushed**) — clean tree, 4 commits
on top of the merged history:

1. `0e3dc14` — merge `main` into `timelink-web-dev` (from
   `test-gsilva-web-merge` @ 5b996e5; only conflict was `.gitignore`)
2. `4b6794f` — web deps declared (`setup.py` extras `web`,
   `requirements_web.txt`) + `docs/web-migration/` document set
3. `87fba9c` — add `argon2-cffi`; ignore `.nicegui/`; test results in
   roadmap

## Environment changes made this session

* Installed into `/Users/jrc/develop/timelink-py/.venv`:
  `apscheduler` 3.11.3, `passlib` 1.7.4, `argon2-cffi` 25.1.0
  (these were used by the webapp but undeclared — now in packaging).
* Docker was already running with two `timelinkserver/kleio-server`
  containers (ports 8088, 8089) — the full-suite test run reused them.

## Validated state

* Full pytest suite in the worktree: **391 passed / 13 skipped /
  6 failed**; the 6 failures were 4× missing argon2 backend (fixed)
  and 2× flaky `test_050_import_TL` kleio-import tests that pass on
  re-run (race with Kleio server under load — hardening task in
  roadmap Phase 1).
* Test runs bump a `translations=N` counter inside tracked `.cli`
  fixtures under `tests/timelink-home/...` — restore with
  `git checkout -- tests/` after runs; do not commit that noise.
* Running the webapp: `cd /Users/jrc/develop/timelink-web-dev &&
  timelink start web` (or `python timelink/web/timelink_web.py
  --port 8000 --directory . --database sqlite`).

## Immediate next actions (in order)

0. ~~Push `timelink-web-dev` to origin~~ done 2026-10-16 (later
   commits pushed too — see git log).
1. Phase 1 hygiene (roadmap): configurable secrets, gate SQL console,
   reconcile duplicate `timelink/app/` vs `timelink/web/` stacks,
   salvage `webapp_settings.py` from `test-jrc-web-merge`, CI.
2. Phase 2 linking workstream: `timelink/linking/` package per
   [record-linking-port.md](record-linking-port.md), then web linking
   page — build against the captured UX in
   [mhk-ux-walkthrough.md](mhk-ux-walkthrough.md).
3. Live instance access (owner-provided, temporary credentials kept
   out of this repo): `https://linode.timelink-mhk.net/mhk/`, user
   `beta-tester` level 3, db `beta_tester_db` (Ílhavo parish data).
   Available for re-checking flows during linking-page development.

## Pending owner decisions (see decisions.md "Open questions")

* Solr vs SQLite FTS5/PostgreSQL full-text as default search backend.
* Public signup/captcha flow: needed or not.
* Collaborative linking semantics (per-user link ownership vs
  ProjectAccess roles).

## Branches to clean up AFTER push

* `gsilva-timelink-webapp` — fully contained in baseline, delete.
* `test-jrc-web-merge`, `test-gsilva-web-merge` — retire after
  salvage/push respectively.
* Review separately (not web): `kleio-home-marker-walk` (project
  creation hardening, 161 unique commits), `export_rentities`
  (real-entity export sketch, 1 commit).
