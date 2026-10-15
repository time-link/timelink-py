# Web migration working documents

This directory holds the working documents for the migration of the Java
MHK web application (`mhk/idb`, Tomcat + Velocity servlets) to
**timelink-py**. They are written for the humans and coding agents that
pick up this work across sessions — everything needed to orient is here,
no need to re-analyse the Java codebase from scratch.

## Where this work lives

* Branch: **`timelink-web-dev`** (created from `test-gsilva-web-merge`,
  then merged with `main`).
* Worktree: `/Users/jrc/develop/timelink-web-dev`
* The old Java implementation stays untouched at `/Users/jrc/develop/mhk`
  — it is the reference implementation and source of SQL/logic to port.

## Document map

| File | Content |
|---|---|
| [decisions.md](decisions.md) | Owner decisions that constrain the work. **Read first.** |
| [mhk-web-inventory.md](mhk-web-inventory.md) | Complete feature/route/schema inventory of the Java MHK web app. |
| [timelink-py-status.md](timelink-py-status.md) | What exists in timelink-py (main + web branches), gap matrix, CLI gaps, known issues. |
| [record-linking-port.md](record-linking-port.md) | Inventory of the ~90 MySQL stored procedures/functions to port to Python, grouping and proposed strategy. |
| [roadmap.md](roadmap.md) | Phased work plan and current status of each phase. |
| [reference/](reference/) | Reference material (e.g. the owner's `linking_dictionary.py` prototype for the linking-dictionary export). |

## Status snapshot (2026-10-16)

* `main` merged into `timelink-web-dev`; only conflict was `.gitignore`
  (resolved, both sides kept).
* Web dependencies that were previously undeclared are now in
  `setup.py` (`extras_require["web"]`) and `requirements_web.txt`
  (nicegui, nicegui-tabulator, apscheduler, pysolr, starlette-admin,
  passlib, jinja2, httpx).
* Test suite: see [roadmap.md](roadmap.md) for the latest run results.

## Running the web app from this branch

```bash
cd /Users/jrc/develop/timelink-web-dev
pip install -r requirements_web.txt   # or: pip install -e .[web]
timelink start web                    # scans ports 8000-8020
# or directly:
python timelink/web/timelink_web.py --port 8000 --directory . --database sqlite
```

Note: the app expects a Kleio server (docker image
`timelinkserver/kleio-server`) and, for free-form search, a Solr
container (managed automatically by `timelink/web/backend/solr_wrapper.py`).
