# Web migration roadmap

Phased plan derived from [decisions.md](decisions.md),
[mhk-web-inventory.md](mhk-web-inventory.md) and
[timelink-py-status.md](timelink-py-status.md). Update the status
column as work proceeds; keep commits on `timelink-web-dev`.

## Phase 0 — Consolidate the web baseline ✅ (2026-10-16)

* [x] Branch `timelink-web-dev` created from `test-gsilva-web-merge`
  (worktree `/Users/jrc/develop/timelink-web-dev`).
* [x] `main` merged in (only `.gitignore` conflict; both sides kept).
* [x] Web deps declared: `setup.py extras_require["web"]` +
  `requirements_web.txt` (nicegui, nicegui-tabulator, apscheduler,
  pysolr, starlette-admin, passlib, jinja2, httpx).
* [x] This documentation set added under `docs/web-migration/`.

## Phase 1 — Baseline hygiene (next)

* [x] Test-suite validation of the merged branch (2026-10-16): full
      suite 391 passed / 13 skipped / 6 failed. Of the 6: four were
      missing passlib argon2 backend (fixed — `argon2-cffi` added to
      web extra), two (`test_050_import_TL` kleio import tests) are
      flaky under full-suite load and pass on re-run. No merge
      regressions found.
* [ ] Flakiness: the two `test_050_import_TL` tests race with the
      Kleio server under load — needs retry/timeout hardening.
* [ ] Make secrets configurable (storage_secret, admin password) via
      env/settings; remove hardcoded defaults.
* [ ] Gate the raw SQL console to manager/admin roles.
* [ ] Reconcile duplicate stacks — keep `timelink/web/` as the only
      app: fold JWT auth service, starlette-admin mount, kleio REST
      endpoints, Jinja2 entity templates from `timelink/app/`; delete
      deprecated `app/web/*`, duplicate `TimelinkWebApp`, duplicate
      user/project models, empty static dirs.
* [ ] Salvage from `test-jrc-web-merge`: `webapp_settings.py`
      (pydantic settings), admin page, `extras/web-specs.md`.
* [ ] After push: delete `gsilva-timelink-webapp`; retire
      `test-jrc-web-merge`, `test-gsilva-web-merge`.
* [ ] Review side branches: `kleio-home-marker-walk` (project creation
      hardening — likely merge to main independently) and
      `export_rentities` (real-entity export sketch).

## Phase 1b — Database-native free-form search (D5)

* [ ] `timelink/linking/normalize.py` — shared name/value normalizers
      (prerequisite for both this phase and Phase 2; step 1 of the
      proposed port order in
      [record-linking-port.md](record-linking-port.md)).
* [ ] `SearchBackend` interface; SQLite FTS5 backend (trigram +
      unicode61 fold) and PostgreSQL backend (`portuguese` config +
      `unaccent` + `pg_trgm`); index the rendered entity description;
      reuse the `entities.indexed` job with a sane batch size (not 10).
* [ ] Demote Solr behind a flag (remove auto-start from default
      startup); delete `solr_wrapper.py` after one release if unused.

## Phase 1c — Public access without registration (D6)

* [ ] `public_read` flag on `Project` + resource-level auth gating to
      replace the global `AuthMiddleware` anonymous-rejection.
* [ ] Rate limiting / bot protection (parameters = open question,
      see [decisions.md](decisions.md)).
* [ ] Decide fate of `register_page.py` (open question in
      [decisions.md](decisions.md)); admin-created local users if
      self-registration is removed.

## Phase 2 — Record linking workstream (highest value)

* [ ] Python linking engine `timelink/linking/` per
      [record-linking-port.md](record-linking-port.md) (normalize →
      statistics → blocking → compare → gtest rules → graph →
      rentities → queue → dictionary).
* [ ] Web linking page: same-as / unlink from `display_id_page`,
      batch confirmation lists (`sameas_list.vm` equivalent),
      per-user identification browser (`linking_show.vm` equivalent).
* [ ] Linking dictionary export/import in web UI (productize
      `docs/web-migration/reference/linking_dictionary.py`).
* [ ] Linking-graph inspection page (`graph.vm` equivalent).
* [ ] Preserve and display per-user link provenance in the linking UI
      (D7: `rentities.user`, `links.user`, `rule='*robot'` — schema
      already supports it).
* [x] Explore the running MHK instance (2026-10-16): done — full
      walkthrough with 19 screenshots in
      [mhk-ux-walkthrough.md](mhk-ux-walkthrough.md) (search, act/
      person/real-person display, identifications tab, linking
      dashboard with export/import, sources pipeline incl. git and
      report viewers, system, explore facets, calendar, SQL query,
      networks generation).

## Phase 3 — Exports

* [ ] CSV exports (persons-by-attribute table, acts, links) — pandas
      layer makes this cheap; add download buttons.
* [ ] GEDCOM 5.5 export — requires Python `FamilyManagement`
      equivalent (families/consorts/children from `relations`;
      MHK Java: `geneology/FamilyManagement.java`, `GedComProcessing.java`).
* [ ] KML export of place attributes (`attribute_to_kml.vm`).
* [ ] Network exports (Pajek/GDF) — extend `timelink/networks`.

## Phase 4 — CLI parity

* [ ] `timelink import/update` — wrap `update_from_sources()`
      (translate→import from the command line).
* [ ] `timelink db dump/restore/copy` (SQLite file copy; PostgreSQL
      pg_dump wrapper).
* [ ] `timelink sources` git subcommands (status/clone/pull/commit…)
      over the Kleio server API.
* [ ] `timelink user` management commands (web users DB).
* [ ] `timelink stop/logs/status` for the stack it starts.

## Phase 5 — Remaining pages & migration utility

* [ ] Calendar/timeline page (`calendar.vm` equivalent).
* [ ] Families page + family tab on person display.
* [ ] Web editor for `.cli` sources (CodeMirror or Monaco in NiceGUI).
* [ ] Legacy MHK migration utility: MySQL/MariaDB dump → timelink
      SQLite/Postgres (decision D2; basis `timelink/mhk/`), including
      real entities + links via the linking dictionary format.

## Cross-cutting

* Entity comments feature (MHK `comments` table) — small, can slot
  into any phase.
* i18n: MHK had pt/en bundles; decide scope for the new app.
* Security: parameterized queries everywhere; keep MHK's "expert SQL"
  behind a role gate.
