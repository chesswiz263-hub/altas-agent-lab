"""Typed canonical messages shared by every provider adapter."""
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelReply:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


class RunRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=4000)
    provider: str = Field(default="demo", pattern="^(demo|openai|anthropic|gemini)$")
    model: str | None = Field(default=None, max_length=100)
    max_steps: int = Field(default=5, ge=1, le=8)
    use_memory: bool = False
    max_cost_usd: float | None = Field(default=None, gt=0, le=100)


class DocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=10, max_length=100_000)


class EvaluationRequest(BaseModel):
    provider: str = Field(default="demo", pattern="^(demo|openai|anthropic|gemini)$")
    model: str | None = Field(default=None, max_length=100)


class ComparisonTarget(BaseModel):
    provider: str = Field(pattern="^(demo|openai|anthropic|gemini)$")
    model: str | None = Field(default=None, max_length=100)


class ComparisonRequest(BaseModel):
    models: list[ComparisonTarget] = Field(min_length=2, max_length=3)


class RouteRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=4000)


class SemanticIndexRequest(BaseModel):
    batch_size: int = Field(default=16, ge=1, le=64)
    max_chunks: int = Field(default=256, ge=1, le=1000)


class VerifyRequest(BaseModel):
    answer: str = Field(min_length=5, max_length=15000)
    method: str = Field(default="heuristic", pattern="^(heuristic|nli)$")


class JobRequest(RunRequest):
    mode: str = Field(default='auto', pattern='^(single|team|auto)$')


class MemoryRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=4000)


class ResearchDossierRequest(BaseModel):
    question: str = Field(min_length=4, max_length=1200)
    hypotheses: list[str] = Field(default_factory=list, max_length=6)
    equations: list[str] = Field(default_factory=list, max_length=8)
