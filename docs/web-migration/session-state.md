# Session state / handoff

Last updated: 2026-10-27 (decisions D5-D7 recorded, merged from the
other machine; PR #106 merged 2026-10-20). Read this
together with [README.md](README.md) and [roadmap.md](roadmap.md).

## Repos and paths

| What | Where |
|---|---|
| timelink-py main checkout | `/Users/jrc/develop/timelink-py` (on `main`, synced to the merge commit) |
| **Worktree for web work** | `/Users/jrc/develop/timelink-web-dev` (branch `feature/web-interface`, cut from `main` after the merge) |
| Legacy Java MHK (reference, read-only) | `/Users/jrc/develop/mhk` (branch `master`) |
| Shared venv | `/Users/jrc/develop/timelink-py/.venv` (Python 3.13; has web extra + selenium + pytest-asyncio + flake8 7.1.1 installed) |

## Where we are

**PR #106 merged** (merge commit `4aac8c6`, 2026-10-20): the whole
`timelink.web` NiceGUI app — entity display with the manual linking
loop, real-entity pages, IDList, comments, linking management page,
`/api` router, secrets config, CI green on Python 3.10–3.13. Copilot
review comments were all addressed (fixed or deferred with roadmap
entries) and CI now installs the web stack.

**Branches cleaned up** (2026-10-20): deleted on origin —
`timelink-web-dev`, `gsilva-timelink-webapp`, `test-gsilva-web-merge`
(all fully contained in main) and `test-jrc-web-merge` (superseded;
salvage landed). Remaining to review separately, NOT web:
`kleio-home-marker-walk` (project creation hardening, 161 unique
commits), `export_rentities` (real-entity export sketch, 1 commit).

New web work goes on `feature/web-interface` (per the branch
conventions in CONTRIBUTING.rst) and merges back to `main` via PR.

## Work in flight (coordination, 2026-10-27)

* **Nicegui 2.24.2 → 3.x upgrade**: owner runs it in ANOTHER
  worktree/session, on its own branch (suggested `chore/nicegui-3-upgrade`
  from main; all 30 Dependabot alerts are nicegui, fixed by 3.12+).
  This branch (`feature/web-interface`) must NOT touch the nicegui
  pin (`pyproject.toml` web extra / `requirements_web.txt`) until the
  upgrade lands; merge main after it does.
* This session continues Phase 1b here: `timelink/linking/normalize.py`
  and the search backends are done (SQLite FTS5 + PostgreSQL tsvector,
  Solr demoted to `TIMELINK_SEARCH_BACKEND=solr`, indexing batch 200);
  Phase 1b complete pending live smoke test.

## Immediate next actions (in order)

1. Act-display parity verification (small): compare the current act
   rendering against [mhk-ux-walkthrough.md](mhk-ux-walkthrough.md)
   §2 and the act templates in `~/develop/mhk`
   (`act_show.vm`, `entity_show.vm`).
2. Sources pipeline page (next big chunk): translation/import status,
   report viewers, git operations over the Kleio server API —
   walkthrough §4, MHK `sources_*.vm` + `DoTranslate`/`DoGitCmd`.
3. After that: explore/facets, calendar, families (moved up from
   Phase 5), token auth for `/api` (currently session/401 only).

## Known deferred items (before multi-user deployment)

* Session-scoped project selection (homepage mutates the process-wide
  wrapper — cross-user data leak). Plus per-client state in
  `explore_page`; linking-page lazy loading/pagination. See roadmap
  Cross-cutting.
* Linking reassignment deletes the old link; MHK kept an audit trail
  (`linklog`, `INVALID` status) — port if history matters.

## Environment notes

* Test runs bump a `translations=N` counter inside tracked `.cli`
  fixtures under `tests/timelink-home/...` — restore with
  `git checkout -- tests/` after runs; do not commit that noise.
* Running the webapp: `cd /Users/jrc/develop/timelink-web-dev &&
  PYTHONPATH=. timelink start web` (or `python
  timelink/web/timelink_web.py --port 8000 --directory <project>
  --database sqlite`). Needs Docker (Kleio server + Solr containers).
* Docker Desktop on this machine occasionally dies with a
  "lingering processes" dialog — `pkill -f "Docker Desktop"`, relaunch,
  then restart the webapp.

## Owner decisions (updated 2026-10-27; see [decisions.md](decisions.md))

The three formerly-open questions are now decided: **D5**
database-native free-form search (FTS5/PostgreSQL FTS; Solr optional
behind a flag), **D6** public databases without registration + bot
protection, no public signup, **D7** keep MHK per-user link ownership
(schema already supports it). Still open (D6 details only): rate-limit
parameters, Google OAuth timing, how non-OAuth researchers get
accounts (decides the fate of `register_page.py`).
