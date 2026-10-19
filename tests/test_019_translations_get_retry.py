"""Tests for the translations_get retry in KleioServer.get_translations.

The kleio server briefly stops knowing translations_get (-32601 Method not
found) while it reloads its RPC method modules, e.g. while processing
translate requests — this made CI flaky (issue #98). get_translations
retries that specific error a few times before giving up. No docker needed:
the RPC call is monkeypatched.
"""

import logging

import pytest

from timelink.kleio.kleio_server import KleioServer, KleioServerException

E32601 = KleioServerException("Error -32601: Method not found: translations_get (None id:1)")


@pytest.fixture
def kserver():
    return KleioServer(url="http://localhost:1", token="t", kleio_home=".")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("timelink.kleio.kleio_server.time.sleep", lambda *_: None)


def make_call_script(outcomes):
    calls = []

    def fake_call(method, params, token=None):
        calls.append(method)
        outcome = outcomes[min(len(calls) - 1, len(outcomes) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return fake_call, calls


def test_retries_then_succeeds(kserver, monkeypatch, caplog):
    fake_call, calls = make_call_script([E32601, E32601, []])
    monkeypatch.setattr(kserver, "call", fake_call)
    result = kserver.get_translations(path="", recurse="no")
    assert result == []
    assert calls == ["translations_get"] * 3
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("retrying" in m for m in warnings)


def test_gives_up_after_max_attempts(kserver, monkeypatch):
    fake_call, calls = make_call_script([E32601] * 99)
    monkeypatch.setattr(kserver, "call", fake_call)
    with pytest.raises(KleioServerException):
        kserver.get_translations(path="", recurse="no")
    assert calls == ["translations_get"] * 6


def test_other_errors_not_retried(kserver, monkeypatch):
    other = KleioServerException("Error -32000: something else (None id:1)")
    fake_call, calls = make_call_script([other])
    monkeypatch.setattr(kserver, "call", fake_call)
    with pytest.raises(KleioServerException):
        kserver.get_translations(path="", recurse="no")
    assert calls == ["translations_get"]
