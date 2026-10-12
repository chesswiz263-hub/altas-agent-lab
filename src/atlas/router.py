"""Transparent, deterministic task planner; NOT a learned routing model.

The plan is an auditable engineering baseline, not a claim of semantic intent
classification or automatic vendor capability discovery.
"""
import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Plan:
    execution: str
    retrieval: str
    complexity: str
    reasons: list[str]
    semantic_ready: bool

    def as_dict(self) -> dict:
        return asdict(self)


MATH_RE = re.compile(r"\b(calculate|evaluate|compute|simplify|arithmetic)\b", re.I)
RESEARCH_RE = re.compile(r"\b(compare|contrast|critique|investigate|research|tradeoffs?|risks?|assess|evaluate evidence|synthesi[sz]e)\b", re.I)
MULTI_RE = re.compile(r"\b(and then|step by step|multiple sources|pros and cons|different perspectives|on the other hand)\b", re.I)


def plan(prompt: str, *, semantic_ready: bool = False) -> Plan:
    terms = re.findall(r"\w+", prompt.lower())
    complex_task = bool(RESEARCH_RE.search(prompt) or MULTI_RE.search(prompt) or len(terms) >= 65)
    math_task = bool(MATH_RE.search(prompt)) and not complex_task and len(terms) <= 30
    if math_task:
        return Plan("single", "bm25", "simple", ["Arithmetic-oriented request; avoid unnecessary specialist stages"], semantic_ready)
    if complex_task:
        return Plan("team", "semantic_hybrid" if semantic_ready else "hybrid", "complex",
                    ["Request benefits from research, critique and synthesis",
                     "Semantic index ready" if semantic_ready else "Semantic index unavailable; using offline lexical hybrid"], semantic_ready)
    return Plan("single", "semantic_hybrid" if semantic_ready else "hybrid", "moderate",
                ["Bounded single-agent loop is sufficient",
                 "Semantic index ready" if semantic_ready else "Using offline lexical hybrid retrieval"], semantic_ready)
