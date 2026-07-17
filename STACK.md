# Timelink stack — compatibility manifest

This file records a **known-good combination** of the three Timelink
repositories. It is the single source of truth for "what works together"
and replaces the scattered version references that used to drift
(`:latest` docker pulls, stale `0.2.8` mentions, malformed `pip -U`).

The three repositories are versioned **independently**; this file records a
**verified set**. Each consuming project (e.g. `dehergne`) is encouraged to
pin the same combination in its own `.kleio.json` / requirements.

## Current set

Released: 2026-07-17

| Component      | Version   | Where                                                       |
|----------------|-----------|-------------------------------------------------------------|
| kleio-server   | 12.9.588  | docker `timelinkserver/kleio-server:12.9.588` (also `:12.9`, `:latest` — all the same digest as of this date) |
| timelink-py    | 1.1.33    | PyPI `timelink` ; git `time-link/timelink-py@main`          |
| timelink-docs  | _pending_ | git `time-link/timelink-docs`; to be filled by the docs phase |

### Notes on the kleio build number

- `12.9.588` is the latest build **promoted** to Docker Hub. The `:12.9`,
  `:12`, `:latest` **and** `:12.9.588` tags all resolve to the same image
  digest (`sha256:f7dbc284…`, verified 2026-07-17).
- The `timelink-kleio` source tree may be ahead of this (local dev builds
  such as `12.9.591`/`12.9.592` are **not** on Docker Hub until promoted via
  `make build-multi` + `make tag-multi-stable`). STACK.md always records the
  promoted value, not the dev value.

## Verified against

- timelink-py test suite: green against kleio `12.9.588` (Python 3.10–3.13).
- Consuming project `dehergne` imports cleanly with kleio `12.9` / build 588
  (see `dehergne/.kleio.json`).

## Where the pin lives

The kleio pin is expressed in **three places** that must stay in sync — all
use the same env-var name `KLEIO_VERSION`:

| Site                                             | Purpose                                  |
|--------------------------------------------------|------------------------------------------|
| `timelink/kleio/kleio_server.py` `DEFAULT_KLEIO_VERSION` | runtime default, overridable by `$KLEIO_VERSION` |
| `tests/__init__.py` `use_kleio_version`          | test fixture                             |
| `.github/workflows/ci.yml` `env.KLEIO_VERSION`   | CI image pull                            |

`scripts/check-stack.sh` verifies the local reality matches this file.

## Update rule

**This file is updated LAST in every coordinated release** (kleio change of
type A or B — see RELEASE_CHECKLIST.md). Only after kleio has been promoted,
timelink-py has been tested against the new image and released, and docs
have been updated, do you edit the three rows above and commit.

For single-repo releases (timelink-py-only or docs-only), only the affected
row moves.
