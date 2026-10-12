import json

import httpx
import pytest

from atlas.providers import NativeProvider, ProviderError
from atlas.tools import TOOL_SCHEMAS

MESSAGES = [
    {"role": "system", "content": "Use tools"},
    {"role": "user", "content": "Find evidence"},
    {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1", "name": "search_documents", "arguments": {"query": "evidence"}}]},
    {"role": "tool", "content": json.dumps({"results": []}), "name": "search_documents", "tool_call_id": "call_1"},
]


def test_openai_contract():
    p = NativeProvider.openai_request(MESSAGES, TOOL_SCHEMAS, "example")
    assert p["messages"][-1]["tool_call_id"] == "call_1"
    assert p["messages"][-2]["tool_calls"][0]["function"]["name"] == "search_documents"
    reply = NativeProvider.parse_openai({"choices": [{"message": {"content": None,
        "tool_calls": [{"id": "a", "function": {"name": "calculator", "arguments": '{"expression":"1+1"}'}}]}}],
        "usage": {"prompt_tokens": 15, "completion_tokens": 3}})
    assert reply.tool_calls[0].arguments == {"expression": "1+1"}
    assert reply.input_tokens == 15


def test_anthropic_contract():
    p = NativeProvider.anthropic_request(MESSAGES, TOOL_SCHEMAS, "example")
    assert p["system"] == "Use tools"
    assert p["messages"][-1]["content"][0]["tool_use_id"] == "call_1"
    reply = NativeProvider.parse_anthropic({"content": [
        {"type": "text", "text": "I can calculate."},
        {"type": "tool_use", "id": "a", "name": "calculator", "input": {"expression": "2+2"}},
    ], "usage": {"input_tokens": 10, "output_tokens": 7}})
    assert reply.content == "I can calculate."
    assert reply.tool_calls[0].name == "calculator"


def test_gemini_contract():
    p = NativeProvider.gemini_request(MESSAGES, TOOL_SCHEMAS)
    assert p["contents"][-1]["parts"][0]["functionResponse"]["name"] == "search_documents"
    reply = NativeProvider.parse_gemini({"candidates": [{"content": {"parts": [
        {"functionCall": {"name": "calculator", "args": {"expression": "8/2"}}},
    ]}}], "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 4}})
    assert reply.tool_calls[0].name == "calculator"
    assert reply.output_tokens == 4


@pytest.mark.asyncio
async def test_native_http_adapter_with_mock_transport():
    def handler(request):
        assert request.headers["authorization"] == "Bearer fake-test-key"
        return httpx.Response(200, json={"choices": [{"message": {"content": "Hello!"}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = NativeProvider("openai", key="fake-test-key", client=client)
        reply = await provider.complete(MESSAGES, TOOL_SCHEMAS, "example")
        assert reply.content == "Hello!"


@pytest.mark.asyncio
async def test_http_errors_are_sanitized():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(401, text="private"))) as client:
        provider = NativeProvider("openai", key="fake-test-key", client=client)
        with pytest.raises(ProviderError, match="HTTP 401") as exc:
            await provider.complete(MESSAGES, TOOL_SCHEMAS, "example")
        assert "private" not in str(exc.value)
