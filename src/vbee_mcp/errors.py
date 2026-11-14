"""Error types and API error-code mapping for vbee.vn."""

from __future__ import annotations


class VbeeError(Exception):
    """Base error carrying a stable machine-readable code."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class VbeeConfigError(VbeeError):
    """Missing or invalid local configuration (env vars, files)."""


class VbeeAPIError(VbeeError):
    """Error returned by the vbee.vn API (or transport failure)."""


# HTTP status -> default error code, per vbee docs.
_STATUS_CODE_MAP = {
    401: "UNAUTHORIZED",
    400: "BAD_REQUEST",
    429: "TTS_CCR_MAX_LIMIT_REACHED",
    500: "INTERNAL_SERVER_ERROR",
}


def error_from_response(status_code: int, body: bytes | str | None) -> VbeeAPIError:
    """Build a VbeeAPIError from an HTTP response, extracting code/message if present."""
    code = _STATUS_CODE_MAP.get(status_code, f"HTTP_{status_code}")
    message = f"vbee API request failed with status {status_code}"

    parsed: object | None = None
    if body:
        text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
        try:
            import json

            parsed = json.loads(text)
        except Exception:
            parsed = None
        if parsed is None and text.strip():
            message = text.strip()[:500]

    if isinstance(parsed, dict):
        err = parsed.get("error") if isinstance(parsed.get("error"), dict) else parsed
        if isinstance(err, dict):
            code = str(err.get("code") or err.get("error_code") or code)
            message = str(
                err.get("message") or err.get("error_message") or err.get("detail") or message
            )
        else:
            message = str(parsed.get("message") or parsed.get("detail") or message)
    elif isinstance(parsed, str):
        message = parsed

    return VbeeAPIError(code=code, message=message)
