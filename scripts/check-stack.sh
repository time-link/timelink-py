#!/usr/bin/env bash
# check-stack.sh — verify the local Timelink stack matches STACK.md.
#
# Reads the pinned versions from STACK.md and checks local reality:
#   - installed timelink-py version
#   - $KLEIO_VERSION env override (warns if it differs from the pin)
#   - kleio-server docker image present locally / on the registry
#
# Run before any release and after any `git pull`. Non-zero exit on mismatch.
#
# Usage:
#   ./scripts/check-stack.sh            # from repo root
#   ./scripts/check-stack.sh --quiet    # only print on mismatch
#
# No dependencies beyond git, python3, and (optionally) docker.

set -u

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

# Locate STACK.md: this script may be run from repo root or from scripts/.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STACK_FILE="$REPO_ROOT/STACK.md"

note() { [ "$QUIET" -eq 0 ] && echo "$@" || true; }
fail() { echo "FAIL: $*" >&2; exit 1; }

if [ ! -f "$STACK_FILE" ]; then
  fail "STACK.md not found at $STACK_FILE"
fi

# --- read pinned values from STACK.md ----------------------------------------
# Parse the markdown table rows. The version is in the 2nd column (between the
# 2nd and 3rd "|"), so awk on "|" gives it as field 3 (field 1 is empty before
# the leading "|"). We then trim whitespace and keep only the leading version
# token, so any trailing annotation in the cell is ignored.
extract_version() {
  # $1 = component name (kleio-server | timelink-py)
  awk -F'|' -v name="$1" '
    $2 ~ "^[[:space:]]*" name "[[:space:]]*$" {
      v = $3; sub(/^[[:space:]]+/, "", v); sub(/[[:space:]].*$/, "", v); print v; exit
    }
  ' "$STACK_FILE"
}
PINNED_KLEIO=$(extract_version "kleio-server")
PINNED_PY=$(extract_version "timelink-py")

[ -z "$PINNED_KLEIO" ] && fail "could not parse kleio-server version from STACK.md"
[ -z "$PINNED_PY" ]    && fail "could not parse timelink-py version from STACK.md"

note "STACK.md pin:  kleio-server=$PINNED_KLEIO  timelink-py=$PINNED_PY"
echo

# --- check 1: installed timelink-py version ----------------------------------
note "## timelink-py"
# Try the current python3; fall back to a sibling worktree's venv if present
# (this repo uses a git-worktree layout where only `main/` may have a .venv).
PY_FOR_CHECK="python3"
if ! python3 -c "import timelink" >/dev/null 2>&1; then
  for cand in "$REPO_ROOT/../main/.venv/bin/python" "$REPO_ROOT/.venv/bin/python"; do
    if [ -x "$cand" ] && "$cand" -c "import timelink" >/dev/null 2>&1; then
      PY_FOR_CHECK="$cand"; break
    fi
  done
fi
INSTALLED_PY=$("$PY_FOR_CHECK" -c "import timelink; print(timelink.__version__)" 2>/dev/null || true)
if [ -z "$INSTALLED_PY" ]; then
  echo "WARN: timelink-py not importable in any available python (skipped)"
else
  note "   installed: $INSTALLED_PY  (via $PY_FOR_CHECK)"
  if [ "$INSTALLED_PY" = "$PINNED_PY" ]; then
    note "   OK"
  else
    echo "WARN: installed timelink-py ($INSTALLED_PY) != STACK.md ($PINNED_PY)"
    echo "      (expected if you are mid-release; update STACK.md last)"
  fi
fi
echo

# --- check 2: KLEIO_VERSION env override -------------------------------------
note "## KLEIO_VERSION env"
ENV_KLEIO="${KLEIO_VERSION:-}"
if [ -z "$ENV_KLEIO" ]; then
  note "   (not set — runtime/CI will use DEFAULT_KLEIO_VERSION=$PINNED_KLEIO)"
else
  note "   set to: $ENV_KLEIO"
  if [ "$ENV_KLEIO" = "$PINNED_KLEIO" ]; then
    note "   OK"
  else
    echo "WARN: \$KLEIO_VERSION ($ENV_KLEIO) != STACK.md ($PINNED_KLEIO)"
    echo "      (intentional when testing a pre-release build)"
  fi
fi
echo

# --- check 3: docker image ---------------------------------------------------
note "## kleio-server docker image: timelinkserver/kleio-server:$PINNED_KLEIO"
IMAGE="timelinkserver/kleio-server:$PINNED_KLEIO"
if ! command -v docker >/dev/null 2>&1; then
  echo "WARN: docker not available (skipped image check)"
elif ! docker info >/dev/null 2>&1; then
  echo "WARN: docker daemon not running (skipped image check)"
else
  # local first
  if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    note "   present locally"
  else
    note "   not local; checking registry…"
    if docker manifest inspect "$IMAGE" >/dev/null 2>&1; then
      note "   available on registry (will pull on demand)"
    else
      fail "image $IMAGE not found locally or on registry"
    fi
  fi
fi
echo

note "OK — checks complete (WARN lines are informational; FAIL is fatal)."
