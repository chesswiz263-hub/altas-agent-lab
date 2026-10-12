"""Optional local natural language inference backend for claim support audits.

Requires the 'nli' extra and explicitly chosen ATLAS_NLI_MODEL. Inference
scores estimate entailment, not historical or scientific truth.
"""
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _pipeline(model_name: str):
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise RuntimeError("Install the NLI extra: pip install -e '.[nli]'") from exc
    return pipeline("text-classification", model=model_name)


def judge(premise: str, hypothesis: str) -> str:
    model = os.getenv("ATLAS_NLI_MODEL")
    if not model:
        raise RuntimeError("Set ATLAS_NLI_MODEL to a compatible 3-label entailment model")
    pipeline = _pipeline(model)
    prediction = pipeline({"text": premise[:4000], "text_pair": hypothesis[:1000]}, truncation=True)
    if isinstance(prediction, list):
        prediction = prediction[0]
    label = str(prediction.get("label", "")).lower()
    if label in ("entailment", "neutral", "contradiction"):
        return label
    raise RuntimeError("NLI checkpoint must expose descriptive entailment/neutral/contradiction labels")
