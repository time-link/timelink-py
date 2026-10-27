# Changelog

All notable changes to this project template are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/); the
template version, in `VERSION`, follows semantic versioning.

## [1.0.0] - 2026-10-27

First versioned release of the template, aligned with the single-user,
single-project `timelink-home` spec.

### Added

- `.timelink-project` marker file: identifies the directory as a Timelink
  project; used by `find_local_kleio_home()` marker-based detection and by
  the hardened `timelink create project` command (timelink-py branch
  `kleio-home-marker-walk`).
- `extras/` directory; Kleio VS Code extension ships in `extras/vscode/`
  (`kleio-1.0.20.vsix`).
- `AGENTS.md` for AI coding agents: layout and rules, shared venv policy
  (one venv outside the project, registered as a Jupyter kernel), the
  `TimelinkNotebook` source-processing pipeline, common data-query
  recipes, the public replica (Editor/Server) workflow, VS Code extension
  install.
- Common search notebook `notebooks/A3-search.ipynb` (people by name,
  attribute queries with date windows, acts at dates, `to_kleio`
  inspection), shared with the timelink-py tutorial fixture.
- Version stamping (`VERSION`) and this change log.

### Changed

- `.gitignore` extended to generated files: SQLite databases and backups,
  Kleio translation byproducts (`*.rpt`, `*.err`, `*.ids`, `*.org`,
  `*.old`, `*.cli-renamed`, `*.files.json`, `strs/`), Kleio server state
  (`.kleio/`, `.kleio.json`), `.venv`, `.env`, `.vscode/settings.json`.
- `notebooks/A1-kleio-files.ipynb` updated to the common version with the
  import-error checking workflow (per-file import reports).
- `notebooks/database-overview.ipynb` replaced: runs against the project
  database through `TimelinkNotebook` (row counts, entity classes,
  imported files, attribute vocabularies, relations); the previous
  version used the legacy MHK/MySQL machinery.
- README rewritten: template usage (GitHub "Use this template" and
  `timelink create project`) and the documented directory layout;
  `sources/README.md` documents the translation file types.
- `notebooks/README.md` aligned with the shared venv policy (no
  per-project `.venv` from the VS Code Create Environment prompt).

### Note

The notebooks shared with the timelink-py tutorial fixture
(`A1-kleio-files`, `A2-database-explore`, `A3-search`,
`database-overview`, the index) are maintained jointly: update them in
both places or from the timelink-py seed directory.
