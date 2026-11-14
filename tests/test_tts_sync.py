import json

import httpx
import pytest

from tests.conftest import audio_bytes
from vbee_mcp import tools
from vbee_mcp.errors import VbeeAPIError, VbeeConfigError


def test_tts_synthesize_base64(env, mock_http):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=audio_bytes(), headers={"content-type": "audio/mpeg"})

    mock_http(handler)
    out = tools.tts_synthesize(text="hello", voice_code="hn_female_ngochuyen_full_48k-fhg")

    assert seen["url"] == "https://api.vbee.vn/v1/tts"
    assert seen["body"]["mode"] == "sync"
    assert seen["body"]["text"] == "hello"
    assert seen["body"]["voiceCode"] == "hn_female_ngochuyen_full_48k-fhg"
    assert seen["body"]["outputFormat"] == "mp3"
    assert seen["body"]["bitrate"] == 128
    assert seen["body"]["speed"] == 1.0
    assert seen["headers"]["app-id"] == "test-app-id"
    assert seen["headers"]["authorization"] == "Bearer test-token"
    assert out["content_type"] == "audio/mpeg"
    assert out["bytes"] == len(audio_bytes())
    import base64

    assert base64.b64decode(out["audio_base64"]) == audio_bytes()


def test_tts_synthesize_output_path(env, mock_http, tmp_path):
    mock_http(
        lambda req: httpx.Response(
            200, content=audio_bytes(), headers={"content-type": "audio/mpeg"}
        )
    )
    dest = tmp_path / "out.mp3"
    out = tools.tts_synthesize(text="hi", voice_code="v", output_path=str(dest))
    assert out["output_path"] == str(dest)
    assert dest.read_bytes() == audio_bytes()
    assert "audio_base64" not in out


def test_tts_synthesize_text_too_long(env, mock_http):
    with pytest.raises(VbeeConfigError) as ei:
        tools.tts_synthesize(text="x" * 301, voice_code="v")
    assert ei.value.code == "BAD_REQUEST"


def test_tts_synthesize_speed_out_of_range(env, mock_http):
    with pytest.raises(VbeeConfigError):
        tools.tts_synthesize(text="x", voice_code="v", speed=2.5)


def test_tts_synthesize_missing_credentials(monkeypatch):
    monkeypatch.delenv("VBEE_APP_ID", raising=False)
    monkeypatch.delenv("VBEE_TOKEN", raising=False)
    with pytest.raises(VbeeConfigError) as ei:
        tools.tts_synthesize(text="x", voice_code="v")
    assert ei.value.code == "MISSING_CREDENTIALS"


def test_tts_synthesize_api_error_mapping(env, mock_http):
    def handler(request):
        return httpx.Response(
            429, json={"error": {"code": "TTS_CCR_MAX_LIMIT_REACHED", "message": "quota"}}
        )

    mock_http(handler)
    with pytest.raises(VbeeAPIError) as ei:
        tools.tts_synthesize(text="x", voice_code="v")
    assert ei.value.code == "TTS_CCR_MAX_LIMIT_REACHED"
    assert "quota" in ei.value.message


def test_tts_synthesize_error_default_codes(env, mock_http):
    cases = {400: "BAD_REQUEST", 401: "UNAUTHORIZED", 500: "INTERNAL_SERVER_ERROR"}
    for status, code in cases.items():
        mock_http(lambda req, s=status: httpx.Response(s, text="oops"))
        with pytest.raises(VbeeAPIError) as ei:
            tools.tts_synthesize(text="x", voice_code="v")
        assert ei.value.code == code
