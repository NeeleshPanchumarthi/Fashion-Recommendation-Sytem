from concurrent.futures import CancelledError

import httpx
import pytest

from app.clients.tryon_client import CONNECT_RETRIES, UNREACHABLE, TryOnClient, _friendly_error


def test_every_httpx_connection_retries_once_a_client_exists():
    TryOnClient("owner/space")
    # gradio_client opens connections through httpx's module-level calls,
    # which build a default transport -- that default must now retry.
    assert httpx.HTTPTransport()._pool._retries == CONNECT_RETRIES
    assert httpx.AsyncHTTPTransport()._pool._retries == CONNECT_RETRIES


def test_explicit_retries_are_kept():
    TryOnClient("owner/space")
    assert httpx.HTTPTransport(retries=1)._pool._retries == 1


def test_installing_twice_does_not_stack():
    TryOnClient("owner/space")
    TryOnClient("owner/space")
    assert httpx.HTTPTransport()._pool._retries == CONNECT_RETRIES


def _chained(outer: Exception, cause: BaseException) -> Exception:
    outer.__cause__ = cause
    return outer


@pytest.mark.parametrize(
    "exc, expected",
    [
        (Exception("You have exceeded your ZeroGPU runs limit."), "quota"),
        (Exception("You have exceeded your GPU quota"), "quota"),
        (httpx.ConnectError("[WinError 10054] forcibly closed"), UNREACHABLE),
        (_chained(RuntimeError("stream failed"), httpx.ReadError("reset")), UNREACHABLE),
        (CancelledError(), UNREACHABLE),
        (ValueError("bad image"), "different photo"),
    ],
)
def test_errors_are_explained_to_the_user(exc, expected):
    assert expected in _friendly_error(exc)
