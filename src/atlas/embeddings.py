"""Opt-in *neural* sentence embeddings, separate from v0.2 lexical vectors.

No model download or heavyweight import at app startup. The selected local model
is operator-controlled through ATLAS_EMBEDDING_MODEL. Callers may inject a
compatible encoder for deterministic tests. Storage never mixes model spaces.
"""
import math
import os
from functools import lru_cache
from typing import Protocol


class EmbeddingUnavailable(RuntimeError):
    """Semantic retrieval was requested without a ready local embedding model/index."""


class Encoder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


def model_name() -> str:
    return os.environ.get("ATLAS_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


@lru_cache(maxsize=2)
def _load_model(name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingUnavailable("Semantic search needs: pip install -e '.[semantic]'") from exc
    try:
        return SentenceTransformer(name)
    except Exception as exc:
        raise EmbeddingUnavailable("Cannot initialize embedding model. Check network, model name and cache.") from exc


class SentenceEncoder:
    def __init__(self, name: str | None = None):
        self.name = name or model_name()

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            raw = _load_model(self.name).encode(texts, normalize_embeddings=True)
            return [list(map(float, arr)) for arr in raw]
        except EmbeddingUnavailable:
            raise
        except Exception as exc:
            raise EmbeddingUnavailable("Embedding inference failed; inspect local model configuration.") from exc


def normalize(vector: list[float]) -> list[float]:
    if not isinstance(vector, (list, tuple)) or not 2 <= len(vector) <= 4096:
        raise ValueError("Embedding must contain 2 to 4096 dimensions")
    if any(not isinstance(x, (float, int)) or not math.isfinite(x) for x in vector):
        raise ValueError("Embedding must contain finite numeric values")
    magnitude = math.sqrt(sum(x*x for x in vector))
    if magnitude < 1e-12:
        raise ValueError("Zero embedding is invalid")
    return [float(x)/magnitude for x in vector]


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Semantic embedding dimensions differ")
    return sum(x*y for x, y in zip(a, b))
