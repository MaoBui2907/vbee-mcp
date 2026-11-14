import asyncio

from vbee_mcp import server


def test_all_seven_tools_registered():
    async def collect():
        return await server.mcp.list_tools()

    tool_list = asyncio.run(collect())
    names = {t.name for t in tool_list}
    assert names == {
        "tts_synthesize",
        "tts_synthesize_async",
        "tts_get_request",
        "stt_transcribe",
        "stt_transcribe_async",
        "stt_get_transcript",
        "list_voices",
    }
    for tool in tool_list:
        assert tool.description
        assert tool.inputSchema.get("type") == "object"
