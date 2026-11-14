import httpx
import pytest

from vbee_mcp import tools
from vbee_mcp.errors import VbeeConfigError

VOICES_PAYLOAD = {
    "result": {
        "pagination": {"next_cursor": None, "total": 1},
        "voices": [
            {
                "code": "hn_female_ngochuyen_full_48k-fhg",
                "gender": "female",
                "language_code": "vi-VN",
            }
        ],
    },
    "status": "success",
}


def test_list_voices_defaults(env, mock_http):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        return httpx.Response(200, json=VOICES_PAYLOAD)

    mock_http(handler)
    out = tools.list_voices()
    assert seen["url"].startswith("https://vbee.vn/api/public/v1/voices")
    assert "limit=20" in seen["url"]
    assert seen["headers"]["app-id"] == "test-app-id"
    assert out["result"]["voices"][0]["code"].startswith("hn_female")


def test_list_voices_filters(env, mock_http):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json=VOICES_PAYLOAD)

    mock_http(handler)
    tools.list_voices(
        voice_ownership="VBEE",
        code="hn_female_ngochuyen_full_48k-fhg",
        language_code="vi-VN",
        gender="female",
        limit=5,
        cursor="abc",
    )
    url = seen["url"]
    for fragment in [
        "voiceOwnership=VBEE",
        "languageCode=vi-VN",
        "gender=female",
        "limit=5",
        "cursor=abc",
        "code=hn_female",
    ]:
        assert fragment in url


def test_list_voices_limit_bounds(env, mock_http):
    with pytest.raises(VbeeConfigError):
        tools.list_voices(limit=0)
    with pytest.raises(VbeeConfigError):
        tools.list_voices(limit=101)
