import pytest

from atlas.cli import seed
from atlas.evaluation import evaluate


@pytest.mark.asyncio
async def test_golden_suite_scores(store):
    assert seed(store) == 3
    assert seed(store) == 0
    result = await evaluate(store, "demo", "atlas-demo-v1")
    assert result["cases"] == 3
    assert result["retrieval_recall_at_5"] >= 0.66
    assert result["citation_coverage"] >= 0.66
