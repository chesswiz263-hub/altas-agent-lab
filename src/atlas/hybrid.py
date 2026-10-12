"""Dependency-free lexical vector retrieval and Reciprocal Rank Fusion.

    The vector channel is character n-gram TF/IDF-style similarity, NOT a
    pretrained semantic embedding. This catches spelling and morphology
    variation without pretending to offer semantic comprehension.
"""
import hashlib
import math
import re
from collections import Counter

VEC_DIM = 256


def grams(text: str) -> Counter[str]:
    tokens = re.findall(r"[\w]+", text.casefold(), flags=re.UNICODE)
    bag: Counter[str] = Counter()
    for token in tokens[:8000]:
        if len(token) < 2:
            continue
        padded = f"^{token}$"
        bag.update(padded[i:i + 3] for i in range(max(1, len(padded) - 2)))
    return bag


def vectorize(text: str) -> list[float]:
    """Signed hashed character trigrams with log-TF scaling and L2 normalization."""
    v = [0.0] * VEC_DIM
    for gram, count in grams(text).items():
        h = int.from_bytes(hashlib.blake2b(gram.encode(), digest_size=8).digest(), "big")
        v[h % VEC_DIM] += (1 if (h >> 8) & 1 else -1) * (1.0 + math.log(count))
    norm = math.sqrt(sum(n*n for n in v))
    return [round(x / norm, 7) for x in v] if norm else v


def similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def reciprocal_rank_fuse(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for i, ident in enumerate(ranking):
            scores[ident] = scores.get(ident, 0.0) + 1 / (k + i + 1)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))
