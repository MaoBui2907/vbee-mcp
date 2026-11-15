# vbee-mcp

Unofficial [MCP](https://modelcontextprotocol.io) server for [vbee.vn](https://vbee.vn) — Vietnamese Text-to-Speech (TTS) and Speech-to-Text (STT).

> Not affiliated with vbee.vn. Use at your own risk; API behavior and quotas are controlled by vbee.

## Install

Requires Python 3.10+.

```bash
pip install -e .
# or, with dev tooling (pytest, ruff):
pip install -e '.[dev]'
```

This installs the `vbee-mcp` console script, which runs the MCP server over stdio.

## Configuration

Environment variables:

| Variable          | Required | Default                  | Description                                   |
| ----------------- | -------- | ------------------------ | --------------------------------------------- |
| `VBEE_APP_ID`     | yes      | —                        | App ID from https://studio.vbee.vn/apps      |
| `VBEE_TOKEN`      | yes      | —                        | API token (Bearer). Never commit it.          |
| `VBEE_API_BASE`   | no       | `https://api.vbee.vn`    | API base URL                                  |
| `VBEE_WEBHOOK_URL`| no       | —                        | Fallback webhook for batch (async) TTS/STT    |

The server starts without credentials; they are only required when a tool is actually called. The server does not load `.env` files — environment variables must be exported in your shell or provided by your MCP client config (e.g. the `env` block below). `.env.example` is provided as a reference for the variable names only.

Example MCP client config (Claude Desktop / compatible):

```json
{
  "mcpServers": {
    "vbee": {
      "command": "vbee-mcp",
      "env": {
        "VBEE_APP_ID": "your-app-id",
        "VBEE_TOKEN": "your-token"
      }
    }
  }
}
```

## Tools

### 1. `tts_synthesize` — Realtime TTS (sync)

POST `/v1/tts` with `mode=sync`. Text **≤ 300 chars** (required).

Params: `text` (req), `voice_code` (req), `output_format` (`mp3`|`wav`|`pcm`, default `mp3`), `bitrate` (`8|16|32|64|128`, default `128`), `speed` (`0.25–1.9`, default `1.0`), `sample_rate` (`8000|16000|22050|24000|32000|44100|48000`, optional), `output_path` (optional).

The response is raw audio. If `output_path` is given, the file is written and the tool returns `{output_path, content_type, bytes, ...}`; otherwise it returns `{audio_base64, content_type, bytes, ...}`.

```json
{"text": "Xin chào", "voice_code": "hn_female_ngochuyen_full_48k-fhg", "output_path": "/tmp/out.mp3"}
```

### 2. `tts_synthesize_async` — Batch TTS (async)

POST `/v1/tts` with `mode=async`. Text up to **100,000 chars**.

Params: `text` (req), `voice_code` (req), `output_format` (`mp3`|`wav`, default `mp3`), `bitrate`, `speed`, `sample_rate`, `emphasis_intensity` (`0–100`, multiple of 10, optional), `client_pause` (object optional: `major_break`/`medium_break`/`paragraph_break`/`sentence_break` in seconds), `webhook_url` (optional but the API currently requires it — falls back to `VBEE_WEBHOOK_URL`).

Returns `{requestId, status}`.

```json
{"text": "...", "voice_code": "hn_female_ngochuyen_full_48k-fhg", "webhook_url": "https://example.com/hook"}
```

### 3. `tts_get_request` — Poll batch TTS

GET `/v1/tts/requests/{requestId}` → `{requestId, status, audioLink?, error_code?, error_message?}`.

**Note:** `audioLink` expires after **3 minutes**; generated audio is stored for **3 days**.

Example invocation:

```json
{"request_id": "9f2c1a7e-1234-4abc-8def-000000000000"}
```

Example response:

```json
{"requestId": "9f2c1a7e-1234-4abc-8def-000000000000", "status": "COMPLETED", "audioLink": "https://..."}
```

### 4. `stt_transcribe` — Realtime STT (sync)

POST `/v1/stt`, multipart/form-data, `mode=sync`. **WAV only**, file **< 10s** and **< 10MB**.

Params: exactly one of `file_path` or `audio_url`; optional `webhook_url`.

Returns `{transcriptId, status, transcript, utterances[], audioDurationSeconds}`. `audioDurationSeconds` is used for prepaid billing.

Example invocation:

```json
{"file_path": "/path/to/audio.wav"}
```

or with a remote URL:

```json
{"audio_url": "https://example.com/audio.wav", "webhook_url": "https://example.com/hook"}
```

### 5. `stt_transcribe_async` — Batch STT (async)

Same endpoint, `mode=async`. File **< 100MB**. `webhook_url` optional (recommended; falls back to `VBEE_WEBHOOK_URL`).

Returns `{transcriptId, status}`.

Example invocation:

```json
{"file_path": "/path/to/long-audio.wav", "webhook_url": "https://example.com/hook"}
```

or with a remote URL (falls back to `VBEE_WEBHOOK_URL` when `webhook_url` is omitted):

```json
{"audio_url": "https://example.com/long-audio.wav"}
```

### 6. `stt_get_transcript` — Poll STT

GET `/v1/stt/transcripts/{transcriptId}` → transcript object. Poll every **2–5 seconds**.

Example invocation:

```json
{"transcript_id": "c3d4e5f6-1234-4abc-8def-000000000000"}
```

Example response:

```json
{"transcriptId": "c3d4e5f6-1234-4abc-8def-000000000000", "status": "COMPLETED", "transcript": "Xin chào...", "utterances": [], "audioDurationSeconds": 12.4}
```

### 7. `list_voices` — List voices

GET `https://vbee.vn/api/public/v1/voices` with `App-Id` + `Bearer` headers.

Params: `voice_ownership` (`VBEE`|`COMMUNITY`|`PERSONAL`, **required by the API** — the tool always sends it and defaults to `VBEE`), `code`, `language_code` (e.g. `vi-VN`), `gender` (`male`|`female`), `limit` (1–100, default 20), `cursor`.

Returns `{result: {pagination, voices[]}, status}`.

Example invocation (list the first 5 Vietnamese female VBEE voices):

```json
{"voice_ownership": "VBEE", "language_code": "vi-VN", "gender": "female", "limit": 5}
```

Example invocation (paginate):

```json
{"limit": 20, "cursor": "next-cursor-from-previous-response"}
```

## API limits & gotchas

- **Realtime TTS supports only 5 voices** today: HN - Ngọc Huyền, SG - Tường Vy, HN - Mai Phương, SG - Lan Trinh, SG - Thảo Trinh. Batch TTS / `list_voices` are not restricted the same way.
- **STT accepts WAV only.** Convert with ffmpeg, e.g.:
  ```bash
  ffmpeg -i input.mp3 -ar 16000 -ac 1 -sample_fmt s16 output.wav
  ```
  Supported sample rates: 8000/16000/22050/32000/44100/48000.
- Sync TTS text limit: **300 characters**. Batch TTS: **100,000 characters**.
- Sync STT file: **< 10s, < 10MB**. Batch STT: **< 100MB**.
- `audioLink` expiry: **3 minutes**. Audio retention: **3 days**.

## Error handling

Errors are raised as MCP tool errors with a stable `code` and `message`, mapped from the vbee API:

| Code                         | HTTP | Meaning                                   |
| ---------------------------- | ---- | ----------------------------------------- |
| `UNAUTHORIZED`               | 401  | Bad/missing App-Id or token               |
| `BAD_REQUEST`                | 400  | e.g. text > 300 chars, bad voiceCode, insufficient credit |
| `TTS_CCR_MAX_LIMIT_REACHED`  | 429  | Rate/quota limit reached                  |
| `TTS_SPEND_CREDITS_FAILED`   | 500  | Credit spend failed                       |
| `INTERNAL_SERVER_ERROR`      | 500  | vbee internal error                       |
| `NETWORK_ERROR`              | —    | Transport failure                         |
| `MISSING_CREDENTIALS`        | —    | `VBEE_APP_ID`/`VBEE_TOKEN` not set        |
| `MISSING_WEBHOOK_URL`        | —    | Batch call without webhook                |

Tokens are never logged or committed. `.env` is gitignored; only `.env.example` (with placeholders) is tracked. Note that `.env` is not read at runtime — export the variables or set them in your MCP client config.

## Development

```bash
pip install -e '.[dev]'
pytest          # unit tests; all HTTP is mocked, no live API calls
ruff check .
```

## Tương lai (not implemented in v1)

- Streaming STT qua WebSocket (`/v1/stt/streaming`, ~500ms) — cần MCP streaming/transport phù hợp.
- Voice cloning / PERSONAL voices, community voices.
- AI Dubbing, `emphasis_intensity` / `client_pause` nâng cao, pronunciation dictionary.
- Webhook receiver helper (local tunnel) để nhận callback cho batch.
- Cache audio + auto-refresh `audioLink` qua `tts_get_request`; retry/backoff cho 429.
- Đóng gói MCP resources (audio file), progress reporting, chọn mp3/wav theo use-case.
- Publish lên MCP Hub / registry, Docker image, `uvx` install.
