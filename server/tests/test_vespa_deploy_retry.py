import httpx
import pytest

from . import conftest


def make_response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "http://example.test")
    return httpx.Response(status_code=status_code, request=request)


def test_wait_for_success_retries_http_errors(monkeypatch):
    calls = {"count": 0}

    def operation():
        calls["count"] += 1
        if calls["count"] < 3:
            raise httpx.ReadError("connection reset", request=httpx.Request("POST", "http://example.test"))
        return make_response(200)

    sleeps: list[float] = []
    monkeypatch.setattr(conftest.time, "sleep", sleeps.append)

    response = conftest._wait_for_success(
        operation,
        ok_statuses={200},
        timeout_seconds=5,
        interval_seconds=0.1,
        operation_name="test operation",
    )

    assert response.status_code == 200
    assert calls["count"] == 3
    assert sleeps == [0.1, 0.1]


def test_wait_for_success_retries_non_ok_status(monkeypatch):
    calls = {"count": 0}

    def operation():
        calls["count"] += 1
        if calls["count"] < 3:
            return make_response(503)
        return make_response(202)

    sleeps: list[float] = []
    monkeypatch.setattr(conftest.time, "sleep", sleeps.append)

    response = conftest._wait_for_success(
        operation,
        ok_statuses={202},
        timeout_seconds=5,
        interval_seconds=0.1,
        operation_name="test operation",
    )

    assert response.status_code == 202
    assert calls["count"] == 3
    assert sleeps == [0.1, 0.1]


def test_wait_for_success_raises_after_timeout(monkeypatch):
    monkeypatch.setattr(conftest.time, "sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="did not succeed"):
        conftest._wait_for_success(
            lambda: (_ for _ in ()).throw(
                httpx.ReadError("connection reset", request=httpx.Request("POST", "http://example.test"))
            ),
            ok_statuses={200},
            timeout_seconds=0.01,
            interval_seconds=0.001,
            operation_name="test operation",
        )
