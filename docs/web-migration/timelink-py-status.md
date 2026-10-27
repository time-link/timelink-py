# timelink-py status and gap analysis

Snapshot taken 2026-10-16, before/around the consolidation merge onto
`timelink-web-dev`.

## A. `main` branch (v1.1.26, af00825)

Solid data layer, tested:

* **Kleio import pipeline**: `timelink/kleio/importer.py::import_from_xml`
  (SAX) loads translated XML into the ORM;
  `TimelinkDatabase.update_from_sources()` orchestrates translate →
  wait-for-status → import.
* **KleioServer client** (`timelink/kleio/kleio_server.py`): JSON-RPC,
  Docker lifecycle (`timelinkserver/kleio-server`), token
  generate/invalidate, `get_translations`, `translate`,
  `translation_clean`, `get_sources`, `get_report`,
  `find_local_kleio_home()`.
* **Kleio group classes** (`timelink/kleio/groups/`): `KPerson, KAct,
  KAttribute, KRelation, KSource, ...` with `to_kleio()` (Python →
  `.cli` text).
* **SQLAlchemy 2 ORM** (`timelink/api/models/`, single-table
  inheritance off `Entity`): `entities, persons, attributes,
  relations, acts, sources, aregisters, objects, geoentities,
  rentities` + `links`/`blinks`, `classes`/`class_attributes`,
  `syspar`, `syslog`, `kleiofiles`. `REntity.same_as()` implements
  same-as at model level.
* **Databases** (`timelink/api/database.py::TimelinkDatabase`):
  create/drop/check, Alembic migrations, **SQLite and PostgreSQL**
  (MySQL only read-only legacy `timelink/mhk/` inspection).
* **Search via pandas** (`timelink/pandas/`):
  `entities_with_attribute`, `group_attributes`, `attribute_values`,
  `name_to_df`.
* **Networks** (`timelink/networks/`): networkx + matplotlib.
* **CLI** (Typer, `timelink/cli.py`, entry points `timelink`/`tmlk`):
  `create project|multiproject`, `start project|web`, `db
  list|current|upgrade|create|heads|revision|autogenerate|history|stamp`,
  `mhk version|status` (legacy install inspection).
* **No GEDCOM, KML, or CSV export** anywhere on main. Only `to_kleio()`
  and DataFrames.
* `timelink/app/` on main: minimal FastAPI app — JWT auth,
  starlette-admin mount, kleio/import endpoints, entity JSON
  `GET /get/{id}`, markdown entity display `GET /web/show/{id}`;
  `POST /web/search/` is a **hardcoded stub**; `app/web/*` deprecated
  (FastUI sunset, Fief removed).
* Tests: 237 test functions; no CI (GitHub Actions workflows disabled).

## B. Web branches (pre-consolidation)

| Branch | Last commit | vs main | Verdict |
|---|---|---|---|
| `gsilva-timelink-webapp` | 2025-07-17 | 112 behind, 10 unique | Dead — fully contained in `test-gsilva-web-merge`; delete after push. |
| `test-gsilva-web-merge` | 2025-11-28 (5b996e5) | 21 behind, 29 unique | **The baseline** — now consolidated onto `timelink-web-dev`. |
| `test-jrc-web-merge` | 2025-10-02 (ef12416) | 10 behind, 37 unique | Superseded; salvage `webapp_settings.py`, admin page ideas, `web-specs.md`. |
| `kleio-home-marker-walk` | – | 161 unique | Unrelated to web: hardened `create project/multiproject`; review separately. |
| `export_rentities` | – | 1 unique | "AI generated Real entities export code" — relevant to export gap; review. |

### What the baseline (NiceGUI app) already has

Tech: **NiceGUI 2.x on FastAPI/uvicorn** (pure Python UI, Quasar/aggrid/
tabulator, no node build), APScheduler background jobs, pysolr + Solr
container for free-form search, docker SDK, starlette-admin.

`timelink/web/pages/` (page = file):

* `sources_page.py` (797 lines) — file tree, per-file translate/import
  queues with asyncio locks, error/warning tracking, auto-refresh job.
  *Equivalent of MHK sources pipeline, rebuilt properly.*
* `display_id_page.py` (509) — entity display for person/geoentity/act
  with in/out relations, obs parsing, cross-links.
* `tables_page.py` (1122) — SQL table browser/statistics.
* `search_page.py` (294) — name search, advanced attribute/relation
  search, free-form Solr search, SQL console.
* `status_page.py` (299) — project switching, role-based options
  (viewer/manager/admin), `update_from_sources`, clean translations.
* `overview_page.py` (302), `people_page.py` (250), `explore_page.py`
  (165), `homepage`, `navbar`, `menu`.
* `login.py` (132), `github_login.py` (118 OAuth), `register_page.py`
  (113) — cookie-session auth, `AuthMiddleware` guards.
* **Stubs**: `linking_page.py` (19 lines — header only), `families_page.py`
  (19), `calendar_page.py` (20).

`timelink/web/backend/`: `timelink_app_wrapper.TimelinkWebApp` (kleio
server, db + users db, project list/switching, scheduler),
`solr_wrapper.SolrWrapper` (Solr container lifecycle, core
creation/switching, `entity_to_solr_doc`). `timelink/web/models/`:
User/UserProperty/Project/ProjectAccess (AccessLevel viewer/manager/
admin), user_database, activity (search history).

Tests: `tests/test_web_*.py` (10 files) + sample project
`tests/timelink-home/projects/web-tests` with `extras/web-specs.md`.

## C. Gap matrix — MHK web feature → baseline status

| MHK feature | Baseline status | Notes |
|---|---|---|
| Search fulltext/name/attribute/SQL | ✅ done | Solr replaces MySQL FULLTEXT `entitiesindex` |
| Entity display + relations | ✅ mostly | `display_id_page.py` |
| Sources translate/import/git/status | ✅ done | git UI thinner than MHK's |
| Auth, users, roles, multi-project | ✅ done | **hardcoded `storage_secret` and default admin pwd `admin`** — must become config |
| Comments on entities | ❌ | MHK `comments` table in `mhk_users` DB |
| **Record linking UI (same-as/unlink/batch)** | ❌ stub | model layer (`REntity`, links) exists; `processSameAs` semantics need porting |
| **Linking dictionary export/import** | ❌ | owner prototype: `docs/web-migration/reference/linking_dictionary.py` |
| Linking-graph inspection (lgraphs) | ❌ | depends on D3 linking-engine port |
| **Families + GEDCOM export** | ❌ stub | needs Python `FamilyManagement` + `GedComProcessing` |
| Calendar/timeline | ❌ stub | |
| KML / Pajek-GDF network exports | ❌ | `timelink/networks` partially covers networkx |
| CSV export | ⚠️ partial | pandas layer makes it nearly free |
| Web editor for `.cli` (CodeMirror) | ❌ | |
| Entity-groups page | ❌ (MHK stub too) | drop |
| Batch "process files" | ⚠️ | sources page has queues; MHK bulk-select UI richer |
| Public signup + captcha + validation email | ❌ | decide if needed (see decisions.md open questions) |

## D. CLI gaps (`mhk` manager vs `timelink` Typer)

| Capability | `mhk` (bash+docker) | `timelink` | Gap |
|---|---|---|---|
| Start/stop stack | `up/stop/restart/logs/ps/config` | `start project/web` only | no stop/logs/status |
| DB lifecycle | create/copy/list/status/processlist/log | `db create/list` + alembic suite | partial |
| DB backup/restore | `dump/export/import/copy` | – | **gap** |
| Translate/import orchestration | via webapp | API exists (`update_from_sources`) | **no CLI wrapper — gap** |
| User management | `user create/password/properties/token` | – | **gap** (web-side admin exists) |
| Sources git | `sources list/clone/status/log/<any git>` | – | **gap** |
| Config | `set-var/use-tag/use-mariadb/...` | `~/.timelink/.env` only | partial |
| Self-update | `update --local` (rsync manager) | pip | by design |
| Legacy migration | `migrate`, `db migrate` | `mhk version/status` (read-only) | future utility (D2) |

## E. Known issues / hygiene on the baseline

1. ~~`apscheduler`, `passlib` not declared anywhere~~ — **fixed** on
   `timelink-web-dev`: `setup.py extras_require["web"]` +
   `requirements_web.txt`.
2. Hardcoded secrets: `storage_secret="Very secret secret!"`
   (`timelink_web.py`), default admin password `admin`
   (`timelink/app/main.py`).
3. Raw SQL console on search page exposed to any logged-in user
   (MHK gated it behind level ≥2; consider ProjectAccess manager/admin).
4. Duplicate stacks to reconcile (target: `timelink/web/` only):
   `TimelinkWebApp` in `app/backend/timelink_webapp.py` vs
   `web/backend/timelink_app_wrapper.py`; user/project models in
   `app/models` vs `web/models`; deprecated `app/web/*` FastUI pages;
   empty `timelink/static` + `timelink/statics`.
5. No CI; GitHub Actions workflows disabled (`.github/disabled_workflows/`).
6. ~~`node_modules/` directory tracked/present at repo root~~ —
   resolved: not present on `timelink-web-dev` and nothing tracked
   (verified 2026-10-27); NiceGUI needs no node build.
