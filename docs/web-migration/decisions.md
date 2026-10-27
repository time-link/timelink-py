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

From the gap analysis (see [timelink-py-status.md](timelink-py-status.md)),
the agreed priority:

1. Record linking / entity resolution UI + Python linking engine (D3).
2. Exports: GEDCOM (needs a Python `FamilyManagement` equivalent),
   CSV, KML.
3. CLI parity (translate/import wrapper, db backup/restore, sources
   git operations, user management).
4. Remaining pages: calendar/timeline, families, Kleio source web
   editor.
5. Legacy migration utility (D2).

## D5 — Free-form search is database-native

Free-form search runs on the database engine, not an external search
server:

* **SQLite projects**: FTS5 with the trigram tokenizer + unicode61
  diacritic folding. **PostgreSQL projects**: full-text search with
  the `portuguese` config + `unaccent` + `pg_trgm`.
* Index source is the **rendered entity description**, normalized with
  the shared `timelink/linking/normalize.py` normalizers — the same
  module the linking engine uses (build once, feed search and
  linking).
* **Solr is demoted** to an optional backend behind a flag; delete
  after one release if unused.
* **Embedding-based semantic search is not the default**; it may be
  added later as an optional hybrid layer on pgvector/sqlite-vec.

Implementation notes (2026-10-27): backend selection follows the
project's database type; the existing `entities.indexed` incremental
indexing job is reused (its batch size must be raised — currently 10
entities per tick). Sequencing: `normalize.py` is the prerequisite
first slice and is also step 1 of the linking port
([record-linking-port.md](record-linking-port.md)); see roadmap
Phase 1b.

## D6 — Public databases, no public signup, bot protection

* We need to be able to provide **public databases with no
  registration** for data dissemination. Access must be protected from
  robots to protect the resources (service quality), not the
  information itself: in the past, harvesters hit MHK servers
  concurrently and degraded service.
* **No new public user registrations**: new users should have a
  GitHub, Google, or other external account. We just manage
  authenticated users' access to databases and permissions (levels).

Implementation consequences (verified 2026-10-27): the app currently
rejects all anonymous users app-wide (`AuthMiddleware`,
`timelink/web/timelink_web.py`) and `Project`/`ProjectAccess` model
only per-user access levels — this decision therefore requires a
public-read flag on `Project`, resource-level auth gating instead of
the global gate, and a rate-limiting component. See roadmap Phase 1c.

## D7 — Keep MHK's per-user link ownership

The data structures for multi-user collaborative linking already
exist, so we keep the same functionality as in MHK: several
researchers share a database, each with their own identifications
(`rentities.user`, `links.user`), robot links flagged with
`rule='*robot'`.

Verified 2026-10-27: `REntity.user`, `Link.user/rule/status` and the
`(rid, entity, user)` unique constraint are already in
`timelink/api/models/rentity.py` — no schema change needed. The
linking UI port must preserve and display link provenance (who/what
made each link).

## Open questions

* D6: rate-limiting parameters (per-IP/per-user limits, throttle
  response) — pick sane defaults at implementation time.
* D6: is Google OAuth in scope now, or GitHub-only first?
* D6: how do researchers without any external account get in —
  admin-created local users? (This also decides the fate of the
  existing `register_page.py` self-registration page.)
