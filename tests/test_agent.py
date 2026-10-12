import json

import pytest

from atlas.agent import Agent
from atlas.providers import DemoProvider
from atlas.schemas import ModelReply, ToolCall


@pytest.mark.asyncio
async def test_agent_executes_demo_search_and_cites(store):
    store.add_document("Safety", "Agent safety requires allowlists and an execution budget for tools.")
    events = [e async for e in Agent(store, DemoProvider()).stream(
        "What are agent safety allowlists and execution budgets?", "demo", "demo", 5)]
    assert [e["type"] for e in events] == ["start", "thinking", "tool_call", "tool_result", "thinking", "final"]
    assert events[2]["tool"] == "search_documents"
    assert json.loads(events[3]["result"])["results"]
    assert "doc:" in events[-1]["answer"]


@pytest.mark.asyncio
async def test_agent_calculator(store):
    events = [e async for e in Agent(store).stream("Calculate (12+3)*2", "demo", "demo", 5)]
    assert events[-1]["type"] == "final"
    assert "30" in events[-1]["answer"]


class LoopProvider:
    async def complete(self, messages, tools, model):
        return ModelReply(tool_calls=[ToolCall("1", "unknown_tool", {})])


@pytest.mark.asyncio
async def test_agent_step_budget_stops_loop(store):
    events = [e async for e in Agent(store, LoopProvider()).stream("Never stop", "demo", "demo", 2)]
    assert len([e for e in events if e["type"] == "tool_call"]) == 2
    assert events[-1]["budget_exhausted"] is True
