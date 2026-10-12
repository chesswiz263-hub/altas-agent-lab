"""Repeatable retrieval and agent-level citation tests over a small golden dataset."""
import json
import os
import time
from pathlib import Path

from atlas.agent import Agent
from atlas.costs import estimate_usd
from atlas.store import Store
from atlas.verification import review

ROOT = Path(os.getenv("ATLAS_PROJECT_ROOT", str(Path(__file__).resolve().parents[2])))
DEFAULT_SUITE = ROOT / "examples" / "eval_suite.json"


def load_suite(path: Path = DEFAULT_SUITE) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) > 20:
        raise ValueError("Evaluation suite must contain at most 20 cases")
    return data


async def evaluate(store: Store, provider_name: str, model: str,
                   agent: Agent | None = None) -> dict:
    runner = agent or Agent(store)
    items = []
    for case in load_suite():
        expected_title = case["expected_title"]
        retrieved = store.search(case["question"], limit=5)
        retrieved_hit = any(r["title"] == expected_title for r in retrieved)
        hybrid_hit = any(r["title"] == expected_title for r in store.search_hybrid(case["question"], limit=5))
        semantic_hit = None
        if store.semantic_status()["ready"]:
            semantic_hit = any(r["title"] == expected_title for r in
                               store.search_semantic_hybrid(case["question"], 5))
        answer = ""
        steps = 0
        input_tokens = output_tokens = 0
        began = time.perf_counter()
        citations = []
        try:
            async for event in runner.stream(case["question"], provider_name, model, max_steps=4):
                if event["type"] == "tool_result" and event["tool"] == "search_documents":
                    citations.extend([x["citation"] for x in json.loads(event["result"]).get("results", [])])
                if event["type"] == "final":
                    answer = event["answer"]
                    steps = event["steps"]
                    input_tokens = event.get("input_tokens", 0)
                    output_tokens = event.get("output_tokens", 0)
            # Cite a passage that was actually returned by the tool; we do NOT grade truth.
            grounded_citation = any(f"[{c}]" in answer for c in citations)
            claim_audit = review(answer, store)
            items.append({"id": case["id"], "question": case["question"],
                          "expected_title": expected_title, "retrieval_hit": retrieved_hit,
                          "hybrid_hit": hybrid_hit, "semantic_hit": semantic_hit,
                          "claim_audit": {"total_claims": claim_audit["total_claims"],
                                          "surface_aligned_claims": claim_audit["surface_aligned_claims"]},
                          "grounded_citation": grounded_citation,
                          "steps": steps, "preview": answer[:280],
                          "duration_ms": int((time.perf_counter()-began)*1000),
                          "input_tokens": input_tokens, "output_tokens": output_tokens,
                          "estimated_cost_usd": estimate_usd(provider_name, model, input_tokens, output_tokens)})
        except Exception as exc:
            items.append({"id": case["id"], "question": case["question"],
                          "expected_title": expected_title, "retrieval_hit": retrieved_hit,
                          "hybrid_hit": hybrid_hit, "semantic_hit": semantic_hit,
                          "grounded_citation": False, "error": type(exc).__name__,
                          "duration_ms": int((time.perf_counter()-began)*1000),
                          "estimated_cost_usd": None})
    n = len(items)
    costs = [x["estimated_cost_usd"] for x in items]
    known_total = round(sum(x for x in costs if x is not None), 9) if all(x is not None for x in costs) else None
    return {"estimated_cost_usd": known_total,
            "total_duration_ms": sum(x.get("duration_ms", 0) for x in items),
            "provider": provider_name, "model": model, "cases": n,
            "retrieval_recall_at_5": round(sum(x["retrieval_hit"] for x in items) / n, 3) if n else 0,
            "hybrid_recall_at_5": round(sum(x["hybrid_hit"] for x in items) / n, 3) if n else 0,
            "semantic_hybrid_recall_at_5": (round(sum(x.get("semantic_hit", False) for x in items) / n, 3)
                                            if n and all(x.get("semantic_hit") is not None for x in items) else None),
            "claim_surface_alignment_rate": (round(sum(x.get("claim_audit", {}).get("surface_aligned_claims", 0) for x in items) /
                                                    sum(x.get("claim_audit", {}).get("total_claims", 0) for x in items), 3)
                                            if any(x.get("claim_audit", {}).get("total_claims", 0) for x in items) else None),
            "citation_coverage": round(sum(x["grounded_citation"] for x in items) / n, 3) if n else 0,
            "results": items,
            "note": "Retrieval/citation/claim-surface-alignment are proxies, NOT factuality or hallucination scores."}
