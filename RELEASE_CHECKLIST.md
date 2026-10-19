# Timelink release checklist

A lightweight, single-developer workflow for releasing changes across the
three Timelink repositories in sync:

| Repo            | Role                                          | Versioning                  |
|-----------------|-----------------------------------------------|-----------------------------|
| `timelink-kleio`| SWI-Prolog server; parses `.cli` → emits XML  | `major.minor.build` (files) |
| `timelink-py`   | Consumes XML; Python API (this repo)          | `X.Y.Z` (bump2version)      |
| `timelink-docs` | User-facing docs (MkDocs Material)            | unversioned (git ref)       |

The **only hard coupling** is `kleio → XML → timelink-py`. Everything else
is soft. The kleio image tag is pinned (not `:latest`); see STACK.md for the
current verified-good combination.

---

## 1. Classify the change

Every change falls into one of five types. The type dictates **which repos
move and in what order**.

| Type | What changes                                                      | kleio | py | docs | Coordination |
|------|-------------------------------------------------------------------|:-----:|:--:|:----:|--------------|
| **A**| Notation grammar (`dataSyntax.pl`, `struSyntax.pl`, `gacto2.str`)| ① | ② if importer/`sax_handler.py` affected | ③ notation ref + tutorial | **coordinated** |
| **B**| XML output (`kleioExport.xsd`, `gactoxml.pl`) — *the contract*    | ① | ② **always** | ③ schema/mapping ref | **coordinated** |
| **C**| Python API/behavior                                               | — | ① | ② if user-visible | single-repo |
| **D**| Docs-only (clarify, typo, new example)                            | — | — | ① | single-repo |
| **E**| Infra/CI/release mechanics                                        | ① | ① | ① | repo-local |

For types A/B the work is **one logical change realized as N linked
branches**, named with a shared token so the link is visible:

```
feat/<id>-kleio   e.g. feat/person-rel-xml-kleio
feat/<id>-py            feat/person-rel-xml-py
feat/<id>-docs          feat/person-rel-xml-docs
```

For C/D/E it's a single branch on one repo.

### Tracking

Open **one checklist issue on `timelink-py`** (the coordination home), label
it per affected repo (`kleio` / `timelink-py` / `timelink-docs`) plus
`change-type-A/B/C/D/E`. Close it only when every box below is ticked. No
GitHub Projects boards, no per-repo issue duplication — for one person that
is overhead with no payoff.

---

## 2. Single-repo release (types C / D / E)

The normal flow for a change that touches only one repo.

### timelink-py

1. Branch off `origin/main` (worktree: `git worktree add <dir> -b feature/<id> origin/main`).
2. Make the change.
3. `pytest --rootdir=tests` (needs Docker + Postgres + kleio; see CI for the env).
4. Add an entry to `HISTORY.rst` under a new version heading.
5. `bumpversion patch|minor|major` — auto-bumps `setup.cfg` `current_version`
   **and** `timelink/__init__.py` `__version__`, commits, and tags `vX.Y.Z`.
6. `git push origin main --tags` (or merge via PR).
7. The `v*` tag triggers the `deploy` job in `.github/workflows/ci.yml`
   (trusted publishing to PyPI).

> **Known drift risk:** the legacy `setup.py` also declares a `version=`.
> `bumpversion` is **not** configured to update it (see `setup.cfg`
> `[bumpversion:file:...]`). Ignore `setup.py`'s version; `pyproject.toml` /
> `__init__.py` are authoritative.

### timelink-docs

1. Branch off `main`.
2. Edit markdown (every file needs an `#` H1; lowercase + underscores in
   filenames — see the repo's `README.md` "Style guidelines").
3. Preview locally with `mkdocs serve`.
4. Merge to `main`. `.github/workflows/ci.yml` runs `mkdocs gh-deploy --force`
   → publishes to GitHub Pages.

### timelink-kleio

1. Branch off `main` in the `timelink-kleio` clone.
2. Edit Prolog source / structure files.
3. `make build-local` — bumps `kleio.build.number`, runs `prepare`
   (substitutes `@@VERSION@@/@@BUILD@@/@@DATE@@`), builds the local image.
4. `make test-semantics` (and `make test-api` if REST-facing).
5. **This repo has no CI and no changelog yet** — see §5 caveats and the
   follow-on list in STACK.md.

---

## 3. Coordinated release (types A / B)

Strict propagation order, because each step feeds the next:

```
kleio ──tag/image──▶ py (pin + test against new image) ──tag──▶ docs (cite both) ──merge──▶ STACK.md
```

### Step 1 — kleio

1. Finish the `feat/<id>-kleio` branch; run `make test-semantics`.
2. `make inc-build` → bumps `kleio.build.number` (e.g. 588 → 589).
   - Use `make inc-minor` / `inc-major` only for a real version bump; see
     caveats in §5 (they do **not** reset the build number).
3. `make build-multi` → builds multi-arch and `docker buildx build --push`s
   `timelinkserver/kleio-server:<ver>` to Docker Hub.
4. `make tag-multi-stable` → re-tags as `:12.9` and `:12`, and creates the
   git tag `<ver>` (e.g. `12.9.589`).
5. **Push the git tag** — `make tag-multi-stable` does **not** run
   `git push --tags` (caveat §5). Do it yourself.
6. Add a `CHANGELOG.md` entry (the kleio repo has no changelog yet — see
   STACK.md follow-on list; until it exists, record the change in the
   tracking issue).
7. Verify on Docker Hub that `<ver>`, `:12.9`, `:latest` all point to the
   same new digest:
   ```bash
   for t in 12.9.589 12.9 latest; do
     docker manifest inspect timelinkserver/kleio-server:$t \
       | python3 -c "import sys,json;print(json.load(sys.stdin)['manifests'][0]['digest'])"
   done
   ```

### Step 2 — timelink-py

1. Finish the `feat/<id>-py` branch.
2. Update the kleio pin in **all three** sync sites to the new build:
   - `timelink/kleio/kleio_server.py` → `DEFAULT_KLEIO_VERSION`
   - `tests/__init__.py` → `use_kleio_version`
   - `.github/workflows/ci.yml` → `env.KLEIO_VERSION`
3. `pytest --rootdir=tests` against the new image.
4. Add a `HISTORY.rst` entry.
5. `bumpversion patch|minor|major` → tags `vX.Y.Z`.
6. `git push origin main --tags` → PyPI publish.

### Step 3 — timelink-docs

1. Finish the `feat/<id>-docs` branch.
2. Add a version note ("Requires kleio ≥12.9.589, timelink-py ≥1.1.34").
3. Merge to `main` → auto-`gh-deploy`.

### Step 4 — STACK.md (LAST)

1. Update the three rows in STACK.md (kleio build, py version, docs ref/date).
2. Update the "Verified against" line.
3. Commit to `timelink-py`.
4. Optionally create a GitHub Release on `timelink-py` summarizing the three
   changelogs.
5. Run `./scripts/check-stack.sh` to confirm local reality matches.
6. Close the tracking issue.

---

## 4. Defending the contract boundary (`kleio → XML → py`)

The XML output is the only hard coupling. Defend it explicitly:

- **Schema is the contract:** `timelink-kleio/src/kleioExport.xsd` + the XML
  emitted by `src/gactoxml.pl`. Any type-B change edits these **first**.
- **Round-trip test (follow-on):** a frozen representative `.cli` →
  expected-XML pair under `tests/xml_data/`. On every kleio bump, re-export
  that `.cli` with the new image and diff against expected. A diff fails the
  py build before it reaches users. *(Not yet implemented — see STACK.md
  follow-on list.)*
- **Version handshake (follow-on):** kleio exposes its version via
  `clio_version_version/1` predicates but has **no REST/JSON-RPC endpoint**
  to return it. A future enhancement: add a `version` JSON-RPC method so
  `timelink-py` can log the running kleio version on connect and warn if it
  differs from `DEFAULT_KLEIO_VERSION`.

---

## 5. kleio release caveats (recorded so you don't re-hit them)

These are sharp edges in the current `timelink-kleio` Makefile/release flow.
Read before the first coordinated release.

- **`tag-multi-stable` does not push tags.** It runs `git tag ${patch}` but
  not `git push --tags`. You must push manually.
- **Build number is never reset on minor/major bumps.** `inc-minor` and
  `inc-major` bump their own number but leave `kleio.build.number` climbing
  monotonically. (So `12.10` would start at whatever build `12.9` reached.)
- **`inc-major` resets the minor (patch) number to 0** but `inc-minor` does
  not reset build (consistent with the above, but worth knowing).
- **No CI exists in `timelink-kleio`.** There is no `.github/` directory at
  all. All builds and image releases are manual via `make`.
- **`make prepare` path mismatch.** The `prepare` target `sed`s into
  `.build/src/sources-structure.yaml`, but `cp -r ./src .build` places the
  file at `.build/src/stru/sources-structure.yaml`. The substitution may
  silently miss. Verify the built image reports the right version via its
  `VERSION`/`BUILD` labels after `build-multi`.
- **`get_server()` still defaults to `"latest"`.**
  `KleioServer.get_server(kleio_version="latest")` is a *lookup-by-version*
  helper, not a provisioning default; changing its behavior is a separate
  decision and was intentionally left alone in the pin change. Revisit if it
  causes confusion.
- **No machine-readable version endpoint** — see §4 "Version handshake".

---

## 6. Security note

`timelink-docs/.kleio.json` is tracked in git and historically contained a
live `kleio_admin_token`. Remediation (deferred to the docs phase, per the
user's "rotate + untrack forward" decision):

1. Add `.kleio.json` to `timelink-docs/.gitignore`.
2. `git rm --cached .kleio.json`.
3. **Rotate** the live `kleio_admin_token` on the Kleio server side.

Git history retains the old (now-dead) token. Scrubbing history
(`git filter-repo` + force-push) was considered and rejected as destructive
for a solo project; once rotated, the leaked token is harmless.

---

## 7. Day-to-day loop, condensed

```
1. Classify the change (A/B/C/D/E)            → §1 table
2. Open one checklist issue on timelink-py,
   label per affected repo                     → §1
3. Create linked branches feat/<id>-{kleio,py,docs} as needed
4. Work in propagation order; for type B, XML/schema first
5. Per-repo: test → changelog → tag (kleio image, py tag, docs merge)
6. Update STACK.md last; run scripts/check-stack.sh
7. Close the issue; note in docs changelog
```
