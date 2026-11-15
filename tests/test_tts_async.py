import json

import httpx
import pytest

from vbee_mcp import tools
from vbee_mcp.errors import VbeeConfigError


def test_tts_async_requires_webhook(env, mock_http):
    with pytest.raises(VbeeConfigError) as ei:
        tools.tts_synthesize_async(text="hello", voice_code="v")
    assert ei.value.code == "MISSING_WEBHOOK_URL"


def test_tts_async_webhook_env_fallback(env, mock_http, monkeypatch):
    monkeypatch.setenv("VBEE_WEBHOOK_URL", "https://example.com/hook")
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"requestId": "req-1", "status": "PENDING"})

    mock_http(handler)
    out = tools.tts_synthesize_async(text="hello", voice_code="v")
    assert seen["body"]["webhookUrl"] == "https://example.com/hook"
    assert seen["body"]["mode"] == "async"
    assert out == {"requestId": "req-1", "status": "PENDING"}


def test_tts_async_full_params(env, mock_http):
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"requestId": "r", "status": "PENDING"})

    mock_http(handler)
    pause = tools.ClientPause(major_break=1.0, sentence_break=0.5)
    tools.tts_synthesize_async(
        text="hello",
        voice_code="v",
        output_format="wav",
        bitrate=64,
        speed=1.2,
        sample_rate=22050,
        emphasis_intensity=50,
        client_pause=pause,
        webhook_url="https://example.com/hook",
    )
    body = seen["body"]
    assert body["outputFormat"] == "wav"
    assert body["bitrate"] == 64
    assert body["sampleRate"] == 22050
    assert body["emphasisIntensity"] == 50
    assert body["clientPause"] == {"majorBreak": 1.0, "sentenceBreak": 0.5}


def test_tts_async_text_limit(env, mock_http):
    with pytest.raises(VbeeConfigError):
        tools.tts_synthesize_async(text="x" * 100_001, voice_code="v", webhook_url="https://w")


def test_tts_get_request(env, mock_http):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"requestId": "r1", "status": "DONE", "audioLink": "https://a"})

    mock_http(handler)
    out = tools.tts_get_request("r1")
    assert seen["url"] == "https://api.vbee.vn/v1/tts/requests/r1"
    assert out["audioLink"] == "https://a"
