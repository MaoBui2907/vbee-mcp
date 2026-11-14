import httpx
import pytest

from vbee_mcp import tools
from vbee_mcp.errors import VbeeConfigError


def test_stt_requires_exactly_one_source(env, mock_http):
    with pytest.raises(VbeeConfigError):
        tools.stt_transcribe()
    with pytest.raises(VbeeConfigError):
        tools.stt_transcribe(file_path="a.wav", audio_url="https://x/a.wav")


def test_stt_sync_with_file(env, mock_http, tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF....WAVEfmt ")
    seen = {}

    def handler(request):
        seen["body"] = request.content
        seen["headers"] = dict(request.headers)
        return httpx.Response(
            200,
            json={
                "transcriptId": "t1",
                "status": "COMPLETED",
                "transcript": "xin chào",
                "utterances": [],
                "audioDurationSeconds": 1.5,
            },
        )

    mock_http(handler)
    out = tools.stt_transcribe(file_path=str(wav))
    assert seen["headers"]["content-type"].startswith("multipart/form-data")
    assert b'name="file"' in seen["body"]
    assert b'name="mode"' in seen["body"] and b"sync" in seen["body"]
    assert out["transcriptId"] == "t1"
    assert out["audioDurationSeconds"] == 1.5


def test_stt_sync_with_url(env, mock_http):
    seen = {}

    def handler(request):
        seen["body"] = request.content
        return httpx.Response(200, json={"transcriptId": "t2", "status": "COMPLETED"})

    mock_http(handler)
    tools.stt_transcribe(audio_url="https://example.com/a.wav", webhook_url="https://hook")
    assert b"audioUrl" in seen["body"]
    assert b'name="audioUrl"' in seen["body"]
    assert b"https://example.com/a.wav" in seen["body"]
    assert b"webhookUrl" in seen["body"]


def test_stt_sync_missing_file(env):
    with pytest.raises(VbeeConfigError) as ei:
        tools.stt_transcribe(file_path="/nonexistent/nope.wav")
    assert ei.value.code == "FILE_NOT_FOUND"


def test_stt_async(env, mock_http, tmp_path, monkeypatch):
    monkeypatch.setenv("VBEE_WEBHOOK_URL", "https://example.com/hook")
    wav = tmp_path / "b.wav"
    wav.write_bytes(b"RIFF....WAVEfmt ")
    seen = {}

    def handler(request):
        seen["body"] = request.content
        return httpx.Response(200, json={"transcriptId": "t3", "status": "PENDING"})

    mock_http(handler)
    out = tools.stt_transcribe_async(file_path=str(wav))
    assert b"async" in seen["body"]
    assert b"https://example.com/hook" in seen["body"]
    assert out == {"transcriptId": "t3", "status": "PENDING"}


def test_stt_get_transcript(env, mock_http):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(
            200, json={"transcriptId": "t1", "status": "COMPLETED", "transcript": "x"}
        )

    mock_http(handler)
    out = tools.stt_get_transcript("t1")
    assert seen["url"] == "https://api.vbee.vn/v1/stt/transcripts/t1"
    assert out["status"] == "COMPLETED"
