# Migration decisions

Decisions taken by the project owner (Joaquim Carvalho). These constrain
all work on `timelink-web-dev`; do not re-litigate them in code or docs.

## D1 — Web baseline is `test-gsilva-web-merge`, consolidated on `timelink-web-dev`

The NiceGUI-based web application developed on `test-gsilva-web-merge`
(29 commits, last touched 2025-11-28) is the one true baseline. It was
created by merging that branch with `main` onto the new branch
`timelink-web-dev` (worktree `/Users/jrc/develop/timelink-web-dev`) on
2026-10-16.

Consequences:

* `gsilva-timelink-webapp` is fully contained in the baseline and is
  dead; safe to delete once `timelink-web-dev` is pushed.
* `test-jrc-web-merge` is superseded; salvage `webapp_settings.py`
  (pydantic settings) and the admin-page ideas from it, then retire it.
* The half-deprecated `timelink/app/` FastAPI stack (FastUI remnants,
  stub search endpoint) coexists with `timelink/web/`. Target
  architecture is **one stack: `timelink/web/`**; the still-live assets
  of `timelink/app/` (JWT auth service, starlette-admin mount, kleio
  REST endpoints, Jinja2 markdown entity templates) are to be folded
  into it and the duplicates removed (two `TimelinkWebApp` classes, two
  user/project model sets).

## D2 — No legacy MySQL/MariaDB support, except a migration utility

timelink-py supports **SQLite and PostgreSQL** only. Legacy MHK
MySQL/MariaDB databases are *not* a supported runtime backend. The only
MySQL/MariaDB-related work item is a possible **one-way migration
utility** (legacy MHK database → timelink SQLite/Postgres database).
The existing `timelink/mhk/` package (legacy models + install
inspection) is the starting point for that utility.

## D3 — Record-linking stored procedures must be ported to Python

The record-linking engine of MHK lives in ~90 MySQL stored
procedures/functions (`mhk/idb/etc/db/system/record_linking/*.sql`,
plus `families/`, `networks/` helpers). Per owner decision:

* Port them to Python **inside the timelink-py package** (proposed new
  subpackage `timelink/linking/`), working against the SQLAlchemy 2
  models / SQLAlchemy Core SQL, dialect-neutral between SQLite and
  PostgreSQL.
* After the package-level port, integrate with the web interface
  (linking page, graph inspection, candidate review).
* See [record-linking-port.md](record-linking-port.md) for the full
  inventory and proposed grouping/order.

## D4 — Priority order of the remaining web gaps

From the gap analysis (see `timelink-py-status.md`), the agreed
priority:

1. Record linking / entity resolution UI + Python linking engine (D3).
2. Exports: GEDCOM (needs a Python `FamilyManagement` equivalent),
   CSV, KML.
3. CLI parity (translate/import wrapper, db backup/restore, sources
   git operations, user management).
4. Remaining pages: calendar/timeline, families, Kleio source web
   editor.
5. Legacy migration utility (D2).

## Open questions (not yet decided)

* Scope of the Solr dependency for free-form search (keep Solr
  container, or replace with SQLite FTS5/PostgreSQL full-text as
  default with Solr optional).
* Whether the public-signup / captcha flow of MHK is needed in the new
  app, or whether the GitHub-OAuth + local-account flow of the baseline
  suffices.
* Multi-user *collaborative* linking on the same database (MHK allowed
  several researchers to share a DB with per-user link ownership
  `links.user` / `rentities.user`) — how much of that model the new
  `ProjectAccess` roles should reproduce.
