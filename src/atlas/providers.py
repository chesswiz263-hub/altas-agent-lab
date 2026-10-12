"""Thin native HTTP adapters that normalize OpenAI, Anthropic and Gemini tool calls.

Canonical message schema:
  {role:'system'|'user'|'assistant'|'tool', content:str,
   tool_calls?:[{id,name,arguments}], tool_call_id?:str,name?:str}
"""
import json
import os
import re
import uuid
from typing import Any, Protocol

import httpx

from atlas.schemas import ModelReply, ToolCall


class Provider(Protocol):
    async def complete(self, messages: list[dict], tools: list[dict], model: str) -> ModelReply: ...


class ProviderError(Exception):
    pass


def _json_args(raw: Any) -> dict:
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


class NativeProvider:
    """Provider-portable logic; only boundary translation is provider-specific."""

    def __init__(self, name: str, key: str | None = None, client: httpx.AsyncClient | None = None):
        self.name = name
        env_name = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
                    "gemini": "GEMINI_API_KEY"}.get(name)
        if env_name is None:
            raise ValueError("Unsupported provider")
        self.key = key or os.getenv(env_name)
        if not self.key:
            raise ProviderError(f"{name} API key not configured on server")
        self.client = client

    async def complete(self, messages: list[dict], tools: list[dict], model: str) -> ModelReply:
        if self.name == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.key}"}
            payload = self.openai_request(messages, tools, model)
        elif self.name == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            headers = {"x-api-key": self.key, "anthropic-version": "2023-06-01"}
            payload = self.anthropic_request(messages, tools, model)
        else:
            # The model is a simple ID, never a URL; credentials only in a header.
            if not re.fullmatch(r"[a-zA-Z0-9._-]{1,100}", model):
                raise ProviderError("Invalid Gemini model ID")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            headers = {"x-goog-api-key": self.key}
            payload = self.gemini_request(messages, tools)
        try:
            if self.client is not None:
                response = await self.client.post(url, headers=headers, json=payload, timeout=55)
            else:
                async with httpx.AsyncClient(timeout=55) as client:
                    response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if self.name == "openai":
                return self.parse_openai(data)
            if self.name == "anthropic":
                return self.parse_anthropic(data)
            return self.parse_gemini(data)
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"{self.name} HTTP {exc.response.status_code}; check credentials, quota or model") from exc
        except (httpx.RequestError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(f"{self.name} request or response failed: {type(exc).__name__}") from exc

    @staticmethod
    def openai_request(messages: list[dict], tools: list[dict], model: str) -> dict:
        converted = []
        for m in messages:
            role = m["role"]
            if role == "assistant" and m.get("tool_calls"):
                converted.append({"role": role, "content": m.get("content") or None,
                    "tool_calls": [{"id": c["id"], "type": "function", "function": {
                        "name": c["name"], "arguments": json.dumps(c["arguments"]),
                    }} for c in m["tool_calls"]]})
            elif role == "tool":
                converted.append({"role": role, "tool_call_id": m["tool_call_id"],
                                  "content": m["content"]})
            else:
                converted.append({"role": role, "content": m["content"]})
        return {"model": model, "messages": converted, "temperature": 0.2,
                "tools": [{"type": "function", "function": t} for t in tools],
                "tool_choice": "auto"}

    @staticmethod
    def anthropic_request(messages: list[dict], tools: list[dict], model: str) -> dict:
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        converted = []
        for m in messages:
            role = m["role"]
            if role == "system":
                continue
            if role == "assistant":
                blocks = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                blocks.extend({"type": "tool_use", "id": c["id"], "name": c["name"],
                               "input": c["arguments"]} for c in m.get("tool_calls", []))
                converted.append({"role": "assistant", "content": blocks})
            elif role == "tool":
                block = {"type": "tool_result", "tool_use_id": m["tool_call_id"],
                         "content": m["content"]}
                if converted and converted[-1]["role"] == "user" and isinstance(converted[-1]["content"], list):
                    converted[-1]["content"].append(block)
                else:
                    converted.append({"role": "user", "content": [block]})
            else:
                converted.append({"role": "user", "content": m["content"]})
        return {"model": model, "system": system, "messages": converted, "max_tokens": 1600,
                "tools": [{"name": t["name"], "description": t["description"],
                           "input_schema": t["parameters"]} for t in tools]}

    @staticmethod
    def gemini_request(messages: list[dict], tools: list[dict]) -> dict:
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = []
        call_names = {c["id"]: c["name"] for m in messages for c in m.get("tool_calls", [])}
        for m in messages:
            role = m["role"]
            if role == "system":
                continue
            if role == "assistant":
                parts = []
                if m.get("content"):
                    parts.append({"text": m["content"]})
                parts += [{"functionCall": {"name": c["name"], "args": c["arguments"]}}
                          for c in m.get("tool_calls", [])]
                contents.append({"role": "model", "parts": parts})
            elif role == "tool":
                name = call_names.get(m["tool_call_id"], m.get("name", "unknown"))
                contents.append({"role": "user", "parts": [{"functionResponse": {
                    "name": name, "response": {"result": m["content"]},
                }}]})
            else:
                contents.append({"role": "user", "parts": [{"text": m["content"]}]})
        return {"systemInstruction": {"parts": [{"text": system}]},
                "contents": contents, "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1600},
                "tools": [{"functionDeclarations": [{"name": t["name"],
                    "description": t["description"], "parameters": t["parameters"]} for t in tools]}]}

    @staticmethod
    def parse_openai(data: dict) -> ModelReply:
        m = data["choices"][0]["message"]
        calls = [ToolCall(id=c["id"], name=c["function"]["name"],
                          arguments=_json_args(c["function"]["arguments"]))
                 for c in m.get("tool_calls") or []]
        usage = data.get("usage") or {}
        return ModelReply(m.get("content") or "", calls,
                          usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))

    @staticmethod
    def parse_anthropic(data: dict) -> ModelReply:
        blocks = data.get("content", [])
        calls = [ToolCall(id=b["id"], name=b["name"], arguments=_json_args(b.get("input", {})))
                 for b in blocks if b["type"] == "tool_use"]
        content = "\n".join(b["text"] for b in blocks if b["type"] == "text")
        usage = data.get("usage") or {}
        return ModelReply(content, calls, usage.get("input_tokens", 0), usage.get("output_tokens", 0))

    @staticmethod
    def parse_gemini(data: dict) -> ModelReply:
        parts = data["candidates"][0]["content"].get("parts", [])
        calls = [ToolCall(id="gemini_" + uuid.uuid4().hex[:12],
                          name=p["functionCall"]["name"],
                          arguments=_json_args(p["functionCall"].get("args", {})))
                 for p in parts if "functionCall" in p]
        content = "\n".join(p["text"] for p in parts if "text" in p)
        usage = data.get("usageMetadata") or {}
        return ModelReply(content, calls, usage.get("promptTokenCount", 0),
                          usage.get("candidatesTokenCount", 0))


class DemoProvider:
    """Offline, repeatable model simulator; never misrepresents itself as an LLM.

    It plans one tool call, observes its result, and composes an attributed demonstration.
    """

    async def complete(self, messages: list[dict], tools: list[dict], model: str) -> ModelReply:
        user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        observations = [m for m in messages if m["role"] == "tool"]
        if not observations:
            matches = re.findall(r"(?<![\w.])[0-9().+*/%\-\s]{3,}", user)
            expressions = [m.strip() for m in matches if re.search(r"\d\s*[+*/%\-]|[+*/%\-]\s*\d", m)]
            if expressions and any(s in user.lower() for s in ("calculate", "what is", "solve", "compute")):
                return ModelReply(tool_calls=[ToolCall("demo_calc", "calculator", {"expression": max(expressions, key=len)})])
            return ModelReply(tool_calls=[ToolCall("demo_search", "search_documents", {"query": user})])
        try:
            payload = json.loads(observations[-1]["content"])
        except (ValueError, KeyError):
            payload = {}
        if "result" in payload:
            return ModelReply(content=f"**Calculated result:** {payload['expression']} = **{payload['result']}**.\n\nThis was computed by the allowlisted calculator tool (offline demo mode).")
        hits = payload.get("results", [])
        if not hits:
            return ModelReply(content="No relevant passage was found in the local knowledge base. I won't invent a source. Add a document and try again. **Offline demo mode** uses deterministic tool routing, not generative AI.")
        paragraphs = []
        for hit in hits[:3]:
            excerpt = hit["body"][:360].strip()
            paragraphs.append(f"**{hit['title']}** [{hit['citation']}]\n> {excerpt}{'…' if len(hit['body']) > 360 else ''}")
        return ModelReply(content="### Evidence retrieved\n\n" + "\n\n".join(paragraphs) +
                          "\n\n*Offline demo: these are sourced excerpts, not a synthesized LLM answer. Select a live provider to use a generative model.*")
