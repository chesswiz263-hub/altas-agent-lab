"""v0.3 semantic indexing, auto-routing, and evidence review contracts."""
import pytest
from fastapi.testclient import TestClient

from atlas.api import create_app
from atlas.embeddings import EmbeddingUnavailable, normalize
from atlas.router import plan
from atlas.store import Store
from atlas.verification import review, split_claims


class TinyEncoder:
    """Fake deterministic vectors only for fast offline contract tests.

    This is NOT a neural embedding model. Production uses SentenceTransformer.
    """
    def encode(self, texts):
        return [[1.0, 0.0, 0.0] if any(x in t.lower() for x in ('cat', 'feline', 'kitten'))
                else [0.0, 1.0, 0.0] if any(x in t.lower() for x in ('apple', 'fruit'))
                else [0.0, 0.0, 1.0] for t in texts]


def test_index_search_model_version_and_deletion(tmp_path):
    path = tmp_path / 'semantic.sqlite'
    db = Store(path, encoder=TinyEncoder(), embedding_model='fake-semantic-A')
    a = db.add_document('Pets', 'The cat sits beside the porch at sunset.')
    db.add_document('Orchard', 'An apple tree grows near the farmer and her family.')
    assert not db.semantic_status()['ready']
    with pytest.raises(EmbeddingUnavailable):
        db.search_semantic('feline animal')
    assert db.index_semantic(batch_size=1, max_chunks=1)['indexed_this_call'] == 1
    assert not db.semantic_status()['ready']
    assert db.index_semantic()['ready']
    hits = db.search_semantic('feline kitten')
    assert hits[0]['title'] == 'Pets'
    assert hits[0]['citation'] == f"doc:{a['id']}#chunk:{hits[0]['chunk_id']}"
    assert db.search_semantic_hybrid('feline kitten')[0]['retrieval'] == 'hybrid_semantic'
    with pytest.raises(EmbeddingUnavailable):
        Store(path, encoder=TinyEncoder(), embedding_model='fake-semantic-B').search_semantic('feline')
    assert db.delete_document(a['id'])
    assert not db.semantic_status()['ready'] or db.semantic_status()['indexed_chunks'] == 1
    with db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM semantic_vectors").fetchone()[0] == 1


def test_index_partial_and_added_chunk_invalidates_readiness(tmp_path):
    db = Store(tmp_path / 'fresh.db', encoder=TinyEncoder(), embedding_model='fake')
    db.add_document('First', 'Cats are curious when looking out of the window.')
    assert db.index_semantic()['ready']
    db.add_document('Second', 'Dogs love chewing on their favorite toys outside.')
    assert not db.semantic_status()['ready']
    assert db.index_semantic()['ready']
    assert db.index_semantic()['indexed_this_call'] == 0


def test_bad_vectors_rejected(tmp_path):
    for x in ([0.0, 0.0], [float('nan'), 1], [1]):
        with pytest.raises(ValueError):
            normalize(x)
    class BadEncoder:
        def encode(self, texts):
            return [[0.0, 0.0] for _ in texts]
    db = Store(tmp_path / 'bad.db', encoder=BadEncoder(), embedding_model='bad')
    db.add_document('Bad', 'This document has enough words to create a chunk.')
    with pytest.raises(ValueError):
        db.index_semantic()
    assert not db.semantic_status()['ready']


def test_router_decisions_are_explainable():
    assert plan('Calculate (42 * 9) / 3').execution == 'single'
    r = plan('Compare the risks and tradeoffs in agent deployments', semantic_ready=True)
    assert r.execution == 'team'
    assert r.retrieval == 'semantic_hybrid'
    assert r.reasons and r.semantic_ready
    assert plan('What do the documents say about tool execution?').retrieval == 'hybrid'


def test_claim_review_citations_and_mismatches(store):
    d = store.add_document('Safeguards', 'Agents use strict tool allowlists for security. They have exactly 4 tools.')
    citation = store.search('tool allowlists')[0]['citation']
    good = review(f'Agents use strict tool allowlists for security [{citation}].', store)
    assert good['claims'][0]['status'] == 'surface_aligned'
    assert good['surface_alignment_rate'] == 1.0
    bad_number = review(f'Agents have exactly 23 tools [{citation}].', store)
    assert bad_number['claims'][0]['status'] == 'numeric_mismatch'
    forged = review('Agents use a strong security mechanism [doc:999#chunk:999].', store)
    assert forged['claims'][0]['status'] == 'invalid_citation'
    assert review('Agents use strict tool allowlists for security.', store)['claims'][0]['status'] == 'unattributed'
    assert store.get_citation(f'doc:{d["id"]}#chunk:999') is None
    assert store.get_citation('x;DELETE FROM documents') is None
    assert split_claims('## Summary\n- A brief heading.\n- Agents use strict tool allowlists.')


def test_injected_nli_does_not_pretend_to_be_truth(store):
    store.add_document('Source', 'The spacecraft orbits Earth at 28,000 kilometers an hour.')
    cite = store.search('spacecraft orbits')[0]['citation']
    report = review(f'The spacecraft orbits Earth at 28000 kilometers an hour [{cite}].',
                    store, nli=lambda premise, hypothesis: 'contradiction')
    assert report['claims'][0]['status'] == 'nli_contradiction'
    assert 'NOT ground-truth' in report['warning']


def test_api_semantic_and_verification(tmp_path):
    db = Store(tmp_path / 'api.db', encoder=TinyEncoder(), embedding_model='fake')
    with TestClient(create_app(db)) as client:
        assert client.get('/api/health').json()['version'] == '0.6.0'
        assert client.get('/api/search', params={'q': 'feline', 'mode': 'semantic'}).status_code == 409
        assert client.post('/api/embeddings/index', json={}).json()['complete']
        doc = client.post('/api/documents', json={'title': 'Pets', 'content': 'Cats are wonderful pets and kittens like to explore.'}).json()
        assert not client.get('/api/embeddings/status').json()['ready']
        assert client.post('/api/embeddings/index', json={}).json()['ready']
        data = client.get('/api/search', params={'q': 'feline kitten', 'mode': 'semantic_hybrid'}).json()
        assert data['results'][0]['doc_id'] == doc['id']
        cid = data['results'][0]['citation']
        verified = client.post('/api/verify', json={'answer': f'Kittens like to explore [{cid}].'}).json()
        assert verified['claims'][0]['status'] == 'surface_aligned'
        assert client.post('/api/verify', json={'answer': 'Kittens like to explore.', 'method': 'nli'}).status_code == 409
        decision = client.post('/api/route', json={'prompt': 'Compare advantages and disadvantages of agent orchestration'}).json()
        assert decision['execution'] == 'team' and decision['retrieval'] == 'semantic_hybrid'
        stream = client.post('/api/auto/stream', json={'prompt': 'What do cats enjoy?', 'provider': 'demo'})
        assert 'event: route' in stream.text
        assert 'semantic_hybrid' in stream.text
        runs = client.get('/api/runs').json()
        assert runs[0]['mode'] == 'auto'
        assert client.post(f'/api/runs/{runs[0]["id"]}/verify').status_code == 200
        assert client.post('/api/runs/does-not-exist/verify').status_code == 404


def test_semantic_index_resource_limits(store):
    with pytest.raises(ValueError):
        store.index_semantic(batch_size=0)
    with TestClient(create_app(store)) as client:
        assert client.post('/api/embeddings/index', json={'batch_size': 0}).status_code == 422
