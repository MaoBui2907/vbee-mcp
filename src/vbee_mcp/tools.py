"""vbee.vn MCP tools (7 tools)."""

from __future__ import annotations

import base64
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from . import client
from .config import load_settings, require_credentials
from .errors import VbeeConfigError, VbeeError

MAX_SYNC_TEXT = 300
MAX_ASYNC_TEXT = 100_000

CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
}


def _error_payload(exc: VbeeError) -> dict[str, Any]:
    return {"error": {"code": exc.code, "message": exc.message}}


def _settings():
    return require_credentials(load_settings())


class ClientPause(BaseModel):
    major_break: float | None = Field(
        default=None, description="Pause after major breaks, seconds"
    )
    medium_break: float | None = Field(
        default=None, description="Pause after medium breaks, seconds"
    )
    paragraph_break: float | None = Field(
        default=None, description="Pause between paragraphs, seconds"
    )
    sentence_break: float | None = Field(
        default=None, description="Pause between sentences, seconds"
    )


def _pause_json(pause: ClientPause | None) -> dict[str, float] | None:
    if pause is None:
        return None
    mapping = {
        "majorBreak": pause.major_break,
        "mediumBreak": pause.medium_break,
        "paragraphBreak": pause.paragraph_break,
        "sentenceBreak": pause.sentence_break,
    }
    out = {k: v for k, v in mapping.items() if v is not None}
    return out or None


def tts_synthesize(
    text: str,
    voice_code: str,
    output_format: Literal["mp3", "wav", "pcm"] = "mp3",
    bitrate: Literal[8, 16, 32, 64, 128] = 128,
    speed: float = 1.0,
    sample_rate: Literal[8000, 16000, 22050, 24000, 32000, 44100, 48000] | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Realtime TTS (sync). Text must be <= 300 characters.

    Returns the audio file path + metadata when output_path is given,
    otherwise base64-encoded audio with its content_type.
    """
    if len(text) > MAX_SYNC_TEXT:
        raise VbeeConfigError(
            code="BAD_REQUEST",
            message=f"text exceeds {MAX_SYNC_TEXT} characters (got {len(text)})",
        )
    if not (0.25 <= speed <= 1.9):
        raise VbeeConfigError(code="BAD_REQUEST", message="speed must be between 0.25 and 1.9")
    settings = _settings()
    body: dict[str, Any] = {
        "text": text,
        "voiceCode": voice_code,
        "mode": "sync",
        "outputFormat": output_format,
        "bitrate": bitrate,
        "speed": speed,
    }
    if sample_rate is not None:
        body["sampleRate"] = sample_rate
    resp = client.post_json(settings, "/v1/tts", body)
    content_type = resp.headers.get("content-type", CONTENT_TYPES.get(output_format, "audio/mpeg"))
    audio = resp.content
    if output_path:
        with open(output_path, "wb") as fh:
            fh.write(audio)
        return {
            "output_path": output_path,
            "content_type": content_type,
            "bytes": len(audio),
            "format": output_format,
            "bitrate": bitrate,
            "speed": speed,
        }
    return {
        "audio_base64": base64.b64encode(audio).decode("ascii"),
        "content_type": content_type,
        "bytes": len(audio),
        "format": output_format,
        "bitrate": bitrate,
        "speed": speed,
    }


def tts_synthesize_async(
    text: str,
    voice_code: str,
    output_format: Literal["mp3", "wav"] = "mp3",
    bitrate: Literal[8, 16, 32, 64, 128] = 128,
    speed: float = 1.0,
    sample_rate: Literal[8000, 16000, 22050, 24000, 32000, 44100, 48000] | None = None,
    emphasis_intensity: Literal[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100] | None = None,
    client_pause: ClientPause | None = None,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """Batch TTS (async). Text may be up to 100,000 characters.

    Returns {requestId, status}. The API currently requires webhook_url;
    falls back to the VBEE_WEBHOOK_URL environment variable when not passed.
    """
    if len(text) > MAX_ASYNC_TEXT:
        raise VbeeConfigError(
            code="BAD_REQUEST",
            message=f"text exceeds {MAX_ASYNC_TEXT} characters (got {len(text)})",
        )
    if not (0.25 <= speed <= 1.9):
        raise VbeeConfigError(code="BAD_REQUEST", message="speed must be between 0.25 and 1.9")
    settings = _settings()
    webhook = webhook_url or settings.webhook_url
    if not webhook:
        raise VbeeConfigError(
            code="MISSING_WEBHOOK_URL",
            message=(
                "webhook_url is required by the vbee batch API; "
                "pass it or set VBEE_WEBHOOK_URL"
            ),
        )
    body: dict[str, Any] = {
        "text": text,
        "voiceCode": voice_code,
        "mode": "async",
        "outputFormat": output_format,
        "bitrate": bitrate,
        "speed": speed,
        "webhookUrl": webhook,
    }
    if sample_rate is not None:
        body["sampleRate"] = sample_rate
    if emphasis_intensity is not None:
        body["emphasisIntensity"] = emphasis_intensity
    pause = _pause_json(client_pause)
    if pause:
        body["clientPause"] = pause
    return client.post_json(settings, "/v1/tts", body).json()


def tts_get_request(request_id: str) -> dict[str, Any]:
    """Get the status of a batch TTS request.

    Returns {requestId, status, audioLink?, error_code?, error_message?}.
    Note: audioLink expires after 3 minutes; generated audio is stored for 3 days.
    """
    settings = _settings()
    return client.get_json(settings, f"/v1/tts/requests/{request_id}")


def stt_transcribe(
    file_path: str | None = None,
    audio_url: str | None = None,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """Realtime STT (sync). WAV only. File must be < 10s and < 10MB.

    Provide exactly one of file_path or audio_url.
    Returns {transcriptId, status, transcript, utterances[], audioDurationSeconds}.
    """
    if bool(file_path) == bool(audio_url):
        raise VbeeConfigError(
            code="BAD_REQUEST",
            message="provide exactly one of file_path or audio_url",
        )
    settings = _settings()
    data: dict[str, Any] = {"mode": "sync"}
    if audio_url:
        data["audioUrl"] = audio_url
    if webhook_url:
        data["webhookUrl"] = webhook_url
    files = None
    if file_path:
        try:
            fh = open(file_path, "rb")  # noqa: SIM115 - passed to httpx, closed by caller below
        except OSError as exc:
            raise VbeeConfigError(code="FILE_NOT_FOUND", message=str(exc)) from exc
        files = {"audioContent": (file_path.rsplit("/", 1)[-1], fh, "audio/wav")}
        try:
            resp = client.post_multipart(settings, "/v1/stt", data, files)
        finally:
            fh.close()
    else:
        resp = client.post_multipart(settings, "/v1/stt", data, files)
    return resp.json()


def stt_transcribe_async(
    file_path: str | None = None,
    audio_url: str | None = None,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """Batch STT (async). WAV only; file must be < 100MB. webhook_url recommended.

    Provide exactly one of file_path or audio_url.
    Returns {transcriptId, status}.
    """
    if bool(file_path) == bool(audio_url):
        raise VbeeConfigError(
            code="BAD_REQUEST",
            message="provide exactly one of file_path or audio_url",
        )
    settings = _settings()
    webhook = webhook_url or settings.webhook_url
    data: dict[str, Any] = {"mode": "async"}
    if audio_url:
        data["audioUrl"] = audio_url
    if webhook:
        data["webhookUrl"] = webhook
    files = None
    if file_path:
        try:
            fh = open(file_path, "rb")  # noqa: SIM115
        except OSError as exc:
            raise VbeeConfigError(code="FILE_NOT_FOUND", message=str(exc)) from exc
        files = {"audioContent": (file_path.rsplit("/", 1)[-1], fh, "audio/wav")}
        try:
            resp = client.post_multipart(settings, "/v1/stt", data, files)
        finally:
            fh.close()
    else:
        resp = client.post_multipart(settings, "/v1/stt", data, files)
    return resp.json()


def stt_get_transcript(transcript_id: str) -> dict[str, Any]:
    """Get the status/result of an STT transcript. Poll every 2-5 seconds."""
    settings = _settings()
    return client.get_json(settings, f"/v1/stt/transcripts/{transcript_id}")


def list_voices(
    voice_ownership: Literal["VBEE", "COMMUNITY", "PERSONAL"] = "VBEE",
    code: str | None = None,
    language_code: str | None = None,
    gender: Literal["male", "female"] | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    """List available vbee voices. limit is 1-100 (default 20).

    The vbee voices API requires the voiceOwnership query parameter
    (VBEE|COMMUNITY|PERSONAL); this tool always sends it and defaults to VBEE.
    """
    if not (1 <= limit <= 100):
        raise VbeeConfigError(code="BAD_REQUEST", message="limit must be between 1 and 100")
    settings = _settings()
    params: dict[str, Any] = {"limit": limit, "voiceOwnership": voice_ownership}
    if code:
        params["code"] = code
    if language_code:
        params["languageCode"] = language_code
    if gender:
        params["gender"] = gender
    if cursor:
        params["cursor"] = cursor
    return client.get_voices(settings, params)


ALL_TOOLS = [
    tts_synthesize,
    tts_synthesize_async,
    tts_get_request,
    stt_transcribe,
    stt_transcribe_async,
    stt_get_transcript,
    list_voices,
]


def register(mcp) -> None:
    for fn in ALL_TOOLS:
        mcp.tool()(fn)


def dumps_error(exc: VbeeError) -> str:
    return json.dumps(_error_payload(exc), ensure_ascii=False)
