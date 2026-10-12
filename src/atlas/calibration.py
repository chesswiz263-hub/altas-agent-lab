"""Human-labeled, isolated fixture evaluation of citation-audit heuristics.

The human-defined labels are about evidence-surface categories, not actual truth.
Calibration creates a temporary database and never modifies the user's corpus.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from atlas.store import Store
from atlas.verification import review

GOLD = Path(__file__).resolve().parents[2] / 'examples' / 'claim_gold.json'


def calibrate(path: Path | None = None) -> dict:
    cases = json.loads((path or GOLD).read_text(encoding='utf-8'))
    if not isinstance(cases, list) or not 2 <= len(cases) <= 100:
        raise ValueError('Expected 2–100 labeled cases')
    predictions = []
    with TemporaryDirectory(prefix='atlas-calibration-') as directory:
        db = Store(Path(directory) / 'fixture.sqlite')
        for item in cases:
            d = db.add_document(item['title'], item['source'])
            if d['duplicate']:
                raise ValueError('Calibration document titles and content must be unique')
            citation = db.search(item['keyword'], 10)
            matched = next((h['citation'] for h in citation if h['doc_id'] == d['id']), None)
            if matched is None:
                raise ValueError(f"Failed to index fixture {item['id']}")
            answer = item['claim'].replace('[CITE]', f'[{matched}]')
            labels = review(answer, db)['claims']
            if len(labels) != 1:
                raise ValueError(f"Fixture {item['id']} did not yield exactly one claim")
            predicted = labels[0]['status']
            predictions.append({'id': item['id'], 'expected': item['expected'],
                                'predicted': predicted, 'match': item['expected'] == predicted})
    labels = sorted({x['expected'] for x in predictions} | {x['predicted'] for x in predictions})
    matrix = {e: {p: sum(x['expected'] == e and x['predicted'] == p for x in predictions)
                  for p in labels} for e in labels}
    count = len(predictions)
    per_label = {}
    for label in labels:
        tp = matrix[label][label]
        support = sum(matrix[label].values())
        predicted_as = sum(matrix[actual][label] for actual in labels)
        per_label[label] = {'support': support,
                            'precision': round(tp / predicted_as, 3) if predicted_as else None,
                            'recall': round(tp / support, 3) if support else None}
    return {'cases': count, 'accuracy': round(sum(x['match'] for x in predictions) / count, 3),
            'per_label': per_label, 'confusion_matrix': matrix, 'results': predictions,
            'scope': 'Citation surface-alignment heuristic on a small hand-labeled fixture. NOT a truthfulness or semantic-entailment benchmark.'}
