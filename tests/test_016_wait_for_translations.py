"""Tests for TimelinkDatabase._wait_for_translations.

Exercises the retry / terminal-error / timeout behavior with a fake kleio
server that walks scripted status sequences — no real Kleio server needed.
time.sleep is patched out so polls run back-to-back.

Observed failure mode these tests lock in (kleio-server 12.9.588): a failed
translation reverts the file to status "T" instead of a terminal state
(trace: T -> P -> T -> P -> E), which the old P/Q-only wait loop turned
into a silent skip. See issue #96.
"""

import logging
from types import SimpleNamespace

import pytest

from timelink.api.database import TimelinkDatabase


class FakeKleioFile:
    def __init__(self, path, status):
        self.path = path
        self.status = SimpleNamespace(value=status)


class ScriptedKleioServer:
    """Fake kleio server returning scripted translation statuses.

    script: {path: [status, ...]} — each get_translations() call returns the
    head of the list and advances it; the last status sticks once reached.
    retry_script: {path: [status, ...]} — installed when translate() is
    called for that path, modelling the server's behavior on a retry.
    """

    def __init__(self, script, retry_script=None):
        self._seq = {p: list(seq) for p, seq in script.items()}
        self._retry_script = retry_script or {}
        self.translate_calls = []

    def get_translations(self, path="", recurse=True, status=None):
        files = []
        for p, seq in self._seq.items():
            files.append(FakeKleioFile(p, seq[0]))
            if len(seq) > 1:
                seq.pop(0)
        return files

    def translate(self, path, recurse="no", spawn="no"):
        self.translate_calls.append(path)
        if path in self._retry_script:
            self._seq[path] = list(self._retry_script[path])


@pytest.fixture
def db(tmp_path):
    return TimelinkDatabase(db_url=f"sqlite:///{tmp_path}/wait_test.db")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("timelink.api.database_kleio.time.sleep", lambda *_: None)


def warnings_and_errors(caplog):
    return [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_all_reach_terminal_status(db, caplog):
    """Files that translate cleanly just finish; no retry, no warnings."""
    db.kserver = ScriptedKleioServer({"a.cli": ["T", "P", "V"], "b.cli": ["Q", "P", "W"]})
    db._wait_for_translations(["a.cli", "b.cli"])
    assert db.kserver.translate_calls == []
    assert warnings_and_errors(caplog) == []


def test_failed_translation_is_retried_once(db, caplog):
    """A revert from P back to T means the translation failed: retry once,
    then accept the terminal status (here E, as the server does on retry)."""
    db.kserver = ScriptedKleioServer(
        {"good.cli": ["P", "V"], "bad.cli": ["T", "P", "T"]},
        retry_script={"bad.cli": ["P", "E"]},
    )
    db._wait_for_translations(["good.cli", "bad.cli"])
    assert db.kserver.translate_calls == ["bad.cli"]
    messages = [r.getMessage() for r in warnings_and_errors(caplog)]
    assert any("bad.cli failed; retrying" in m for m in messages)
    assert any("bad.cli finished with errors" in m for m in messages)


def test_second_failure_gives_up_with_error(db, caplog):
    """A file that reverts to T again after the retry is reported and
    dropped from the pending set — not silently skipped, not retried twice."""
    db.kserver = ScriptedKleioServer(
        {"bad.cli": ["P", "T"]},
        retry_script={"bad.cli": ["P", "T"]},
    )
    db._wait_for_translations(["bad.cli"])
    assert db.kserver.translate_calls == ["bad.cli"]
    messages = [r.getMessage() for r in warnings_and_errors(caplog)]
    assert any("bad.cli failed; retrying" in m for m in messages)
    assert any("bad.cli failed twice" in m for m in messages)


def test_translation_errors_accepted_when_requested(db, caplog):
    """With with_translation_errors=True an E status is terminal but not an
    error (the caller will import the file anyway)."""
    db.kserver = ScriptedKleioServer({"e.cli": ["P", "E"]})
    db._wait_for_translations(["e.cli"], with_translation_errors=True)
    assert db.kserver.translate_calls == []
    assert warnings_and_errors(caplog) == []


def test_timeout_reports_unfinished_files(db, caplog):
    """Files that never reach a terminal status (stuck in T, or absent from
    the listing because the job was never registered) are reported."""
    db.kserver = ScriptedKleioServer({"stuck.cli": ["T"]})
    db._wait_for_translations(["stuck.cli", "ghost.cli"], max_wait=0)
    assert db.kserver.translate_calls == []
    messages = [r.getMessage() for r in warnings_and_errors(caplog)]
    assert any("stuck.cli did not complete" in m for m in messages)
    assert any("ghost.cli did not complete" in m for m in messages)
