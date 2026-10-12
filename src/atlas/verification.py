"""Citation-attributed claim review.

The default checker validates references and surface alignment, not truth or
logical entailment. Optional injected NLI judges can provide an additional
support signal, still not proof of factual correctness.
"""
import re
from collections.abc import Callable

CITE = re.compile(r"\[doc:(\d+)#chunk:(\d+)\]")
WORD = re.compile(r"[a-z0-9]+", re.I)
STOPWORDS = set("a an the of in on or and to is are was were be been by for from at as that this which with it its their than into has have had also not can may will could should would after before using use more less much most some any all how what when where why agents agent document documents information evidence source sources".split())
NUMBER = re.compile(r"(?<![\w#])\d+(?:\.\d+)?%?(?!\w)")


def tokenize(text: str) -> set[str]:
    return {w for w in WORD.findall(text.casefold()) if len(w) > 2 and w not in STOPWORDS}


def split_claims(answer: str, limit: int = 35) -> list[str]:
    """Bounded, auditable sentence heuristic (not universal claim extraction)."""
    pieces = []
    for line in answer.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        line = re.sub(r"^#{1,6}\s*", "", line)
        if not line or line.startswith("```") or line.startswith("|"):
            continue
        pieces.extend(re.split(r"(?<=[.!?])\s+(?=[A-Z\d*])", line))
    return [p[:1200] for p in pieces if len(tokenize(CITE.sub("", p))) >= 2][:limit]


def review(answer: str, store, *, nli: Callable[[str, str], str] | None = None) -> dict:
    """Check each extracted claim against only its *explicit* citation IDs."""
    claims = []
    for sentence in split_claims(answer):
        cites = list(dict.fromkeys(f"doc:{d}#chunk:{c}" for d, c in CITE.findall(sentence)))[:8]
        missing = []
        evidence = []
        for citation in cites:
            chunk = store.get_citation(citation)
            if chunk is None:
                missing.append(citation)
            else:
                evidence.append(chunk)
        words = tokenize(CITE.sub("", sentence))
        source_words = tokenize(" ".join(c["body"] for c in evidence))
        overlap = len(words & source_words) / max(1, len(words))
        claim_numbers = set(NUMBER.findall(CITE.sub("", sentence)))
        evidence_numbers = set(NUMBER.findall(" ".join(c["body"] for c in evidence)))
        numeric_mismatch = bool(claim_numbers - evidence_numbers)
        if not cites:
            label = "unattributed"
        elif missing:
            label = "invalid_citation"
        elif numeric_mismatch:
            label = "numeric_mismatch"
        elif overlap < 0.35:
            label = "weak_alignment"
        else:
            label = "surface_aligned"
        nli_label = None
        if nli and evidence:
            raw = nli("\n".join(c["body"] for c in evidence)[:5000], CITE.sub("", sentence))
            if raw not in ("entailment", "neutral", "contradiction"):
                raise ValueError("NLI judge must return entailment/neutral/contradiction")
            nli_label = raw
            if raw == "contradiction":
                label = "nli_contradiction"
            elif raw == "neutral" and label == "surface_aligned":
                label = "nli_neutral"
        claims.append({"claim": sentence, "citations": cites, "missing_citations": missing,
                       "evidence": [{"citation": c["citation"], "title": c["title"],
                                     "excerpt": c["body"][:340]} for c in evidence],
                       "surface_overlap": round(overlap, 3), "numeric_mismatch": numeric_mismatch,
                       "status": label, "nli_label": nli_label})
    total = len(claims)
    aligned = sum(c["status"] == "surface_aligned" for c in claims)
    return {"claims": claims, "total_claims": total, "surface_aligned_claims": aligned,
            "surface_alignment_rate": round(aligned / total, 3) if total else None,
            "method": "citation validation + lexical overlap + numeric consistency" + (" + injected NLI" if nli else ""),
            "warning": "Surface alignment and NLI predictions are NOT ground-truth factuality. Claims without citations or low overlap require human review."}
