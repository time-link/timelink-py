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
* [x] Flakiness: the two `test_050_import_TL` tests race with the
      Kleio server under load — hardened with a `kleio_retry`
      decorator (3 attempts) plus fixing a swallowed import exception
      (2026-10-16); full file now passes (20/20).
* [x] Make secrets configurable (storage_secret, admin password) via
      env/settings; remove hardcoded defaults (2026-10-16):
      `TIMELINK_STORAGE_SECRET`, `TIMELINK_ADMIN_PASSWORD`,
      `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET` (committed GitHub
      secret removed; GitHub login disabled when unset).
* [ ] Gate the raw SQL console to manager/admin roles.
* [x] Reconcile duplicate stacks — `timelink/web/` is now the only
      app (2026-10-16): REST endpoints salvaged into
      `timelink/web/api.py` (mounted at `/api`), entity markdown
      templates moved to `timelink/web/templates/`, user-property
      methods ported into web `UserDatabase`; `timelink/app/` and
      empty `timelink/static`/`timelink/statics` deleted, docs pruned.
      Note: the app stack's "JWT auth" was a stub (get_current_user
      returned None) — real token auth for `/api` is future work.
* [x] Salvage from `test-jrc-web-merge` (2026-10-16):
      `webapp_settings.py` → `timelink/web/backend/webapp_settings.py`;
      `web-specs.md` → `docs/web-migration/reference/web-specs.md`.
      The branch's admin page was an empty stub — skipped (the
      consolidated stack already mounts starlette-admin).
* [x] After push: delete `gsilva-timelink-webapp`; retire
      `test-jrc-web-merge`, `test-gsilva-web-merge` (done 2026-10-20,
      after PR #106 merged; `timelink-web-dev` also deleted).
* [ ] Review side branches (owner, not web work):
      `kleio-home-marker-walk` (project creation hardening — likely
      merge to main independently) and `export_rentities`
      (real-entity export sketch).

## Phase 1b — Database-native free-form search (D5)

* [x] `timelink/linking/normalize.py` — shared name/value normalizers
      (prerequisite for both this phase and Phase 2; step 1 of the
      proposed port order in
      [record-linking-port.md](record-linking-port.md)).
      Done 2026-10-27: faithful ports of break_name, plig/pligp,
      strip_commas, strip_interrog/count_interrog, normalize_place,
      normalize_civil_status; split_person_name (pure part of
      name_to_attributes) and fold_text (D5 search normalizer:
      lowercase + accent-fold + collapse). Pure functions, no DB
      access; covered by tests/test_linking_normalize.py.
* [x] `SearchBackend` interface; SQLite FTS5 backend (trigram
      tokenizer, text accent-folded at index/query time via
      `fold_text`) and PostgreSQL backend (`portuguese` tsvector +
      folded text, short-word LIKE fallback); index the entity's
      searchable values (same extraction as the Solr index);
      `entities.indexed` job reused with batch 200 (2026-10-27).
      Solr kept as an adapter behind `TIMELINK_SEARCH_BACKEND=solr`;
      freeform search reads `search_backend.search()`.
* [x] Demote Solr behind a flag (2026-10-27): Solr container starts
      only when `TIMELINK_SEARCH_BACKEND=solr`; default startup has no
      Solr. Delete `solr_wrapper.py` after one release if unused.

## Phase 1c — Public access without registration (D6)

* [ ] `public_read` flag on `Project` + resource-level auth gating to
      replace the global `AuthMiddleware` anonymous-rejection.
* [ ] Rate limiting / bot protection (parameters = open question,
      see [decisions.md](decisions.md)).
* [ ] Decide fate of `register_page.py` (open question in
      [decisions.md](decisions.md)); admin-created local users if
      self-registration is removed.

## Phase 2 — Web interface workstream (owner decision 2026-10-16: web
interface first, then record linking, then GEDCOM)

Build out the timelink/web app against the UX captured in
[mhk-ux-walkthrough.md](mhk-ux-walkthrough.md) before porting the
linking engine, so the engine grows alongside real pages.

* [ ] Entity display pages to MHK parity: person/act/real-person
  display with identifications tab, attribute/relation rendering
  (Jinja2 entity markdown templates salvaged into
  `timelink/web/templates/markdown/` are the starting point).
  *Started (2026-10-16): manual linking loop done — person page has
  the RID line, Same as/Link form and Unlink; `/id/{rid}` renders a
  real-entity page with merged-biography, All the Acts, Related
  Persons and Identifications tabs (batch same-as, safe-rid markers),
  backed by `timelink/linking/service.py`. Also done: the IDList
  batch mechanism (Save id + navbar Link preview + `/idlist` page)
  and entity comments (Comment model + form on display pages).
  The whole loop was verified live in the browser (same-as, tabs,
  identifications, batch link, comments, unlink, IDList); two bugs
  fixed along the way (LinkSchema.source not Optional; backslash
  users-db path). Remaining: act-display parity checks.*
* [ ] Sources pipeline page parity: translation/import status,
  report viewers, git operations over the Kleio server API.
* [ ] Explore/facets, calendar/timeline page (`calendar.vm`
  equivalent — moved up from Phase 5), families page + family tab.
* [x] API auth for `/api` (2026-10-20, Copilot PR review): the
  session middleware now returns 401 for unauthenticated `/api`
  calls instead of exempting them. Token-based auth for non-browser
  API clients is still future work.
* [x] Explore the running MHK instance (2026-10-16): done — full
      walkthrough with 19 screenshots in
      [mhk-ux-walkthrough.md](mhk-ux-walkthrough.md) (search, act/
      person/real-person display, identifications tab, linking
      dashboard with export/import, sources pipeline incl. git and
      report viewers, system, explore facets, calendar, SQL query,
      networks generation).

## Phase 2b — Record linking (after the web interface bones exist)

* [ ] Python linking engine `timelink/linking/` per
      [record-linking-port.md](record-linking-port.md) (normalize →
      statistics → blocking → compare → gtest rules → graph →
      rentities → queue → dictionary). Port incrementally: build the
      minimum slice the linking page needs first (same-as queue +
      operations), then the statistical pipeline.
      Reference implementation: `~/develop/mhk` (Java, read-only).
* [~] Web linking page: same-as / unlink from `display_id_page`,
      batch confirmation lists (`sameas_list.vm` equivalent),
      per-user identification browser (`linking_show.vm` equivalent).
      Done (2026-10-20): `/linking` page lists real entities with
      occurrences, filterable by user, with unlink per occurrence
      (existing links only — no automatic linking, per owner decision).
* [ ] Linking dictionary export/import in web UI (productize
      `docs/web-migration/reference/linking_dictionary.py`).
* [ ] Linking-graph inspection page (`graph.vm` equivalent).
      Deferred: depends on the ported record-linking engine
      (`lgraphs`/`candidates`/`ledges` tables, decision D3); a
      manual-links graph over `REntity`/`Link` can be added later.
* [ ] Preserve and display per-user link provenance in the linking UI
      (D7: `rentities.user`, `links.user`, `rule='*robot'` — schema
      already supports it).

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

* [ ] ~~Calendar/timeline page~~ and ~~families page + family tab~~ —
  moved up into Phase 2 (2026-10-16 owner decision: web interface
  first).
* [ ] Web editor for `.cli` sources (CodeMirror or Monaco in NiceGUI).
* [ ] Legacy MHK migration utility: MySQL/MariaDB dump → timelink
      SQLite/Postgres (decision D2; basis `timelink/mhk/`), including
      real entities + links via the linking dictionary format.

## Cross-cutting

* Entity comments feature (MHK `comments` table) — done 2026-10-16
  (Comment model + form on display pages).
* **Multi-user correctness (from Copilot PR review, 2026-10-20):**
  project switching on the homepage mutates the process-wide app
  wrapper and re-registers routes, so concurrent users can see each
  other's project databases. Needs session-scoped project resolution
  — architectural, before any multi-user deployment. Same class of
  issue: `explore_page` keeps per-client input state on the shared
  page instance. Linking-page occurrence expansions still render
  eagerly (pagination/lazy loading pending).
* i18n: MHK had pt/en bundles; decide scope for the new app.
* Security: parameterized queries everywhere; keep MHK's "expert SQL"
  behind a role gate.
