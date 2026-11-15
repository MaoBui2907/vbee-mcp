import httpx
import pytest

from vbee_mcp import client as client_mod


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setenv("VBEE_APP_ID", "test-app-id")
    monkeypatch.setenv("VBEE_TOKEN", "test-token")
    monkeypatch.delenv("VBEE_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("VBEE_API_BASE", raising=False)


@pytest.fixture()
def mock_http(monkeypatch):
    """Route httpx.Client creations through an httpx.MockTransport."""
    handler = {"fn": None}
    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler["fn"])
        return real_client(*args, **kwargs)

    monkeypatch.setattr(client_mod.httpx, "Client", factory)

    def set_handler(fn):
        handler["fn"] = fn

    return set_handler


def audio_bytes():
    return b"\xff\xfb\x90\x00fake-mp3-bytes"
