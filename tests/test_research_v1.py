from atlas.research import check_arithmetic, create_dossier
from atlas.store import Store


def test_exact_arithmetic_and_nonsymbolic_abstention():
    checks = check_arithmetic(['1/3 + 1/6 = 1/2', '2*3 = 7', 'E = m*c*c', '__import__("os") = 0'])
    assert [c['status'] for c in checks] == ['EQUAL', 'NOT_EQUAL', 'NOT_CHECKED', 'NOT_CHECKED']


def test_local_research_provenance_and_unknown_theories(tmp_path):
    store = Store(tmp_path/'research.db')
    store.add_document('MCP tooling', 'MCP tools require explicit permissions and execution budgets. ' * 3)
    report = create_dossier('How do MCP tools require permissions and execution budgets?', store)
    assert report['status'] == 'EXCERPTS_AVAILABLE'
    assert all(c['exact_excerpt_from_index'] for c in report['citations'])
    unknown = create_dossier('Explain dark matter galactic rotation curves and MOND physics', store,
        ['Lambda CDM', 'MOND'], ['1/3 + 1/6 = 1/2'])
    assert unknown['status'] == 'INSUFFICIENT_EVIDENCE'
    assert all(h['status'] == 'NOT_EVALUATED' for h in unknown['hypotheses'])
    assert unknown['math_checks'][0]['status'] == 'EQUAL'


def test_api_dossier(tmp_path):
    from fastapi.testclient import TestClient
    from atlas.api import create_app
    client = TestClient(create_app(Store(tmp_path / "api.db")))
    result = client.post('/api/research/dossier',json={
      'question':'How does quantum wavefunction magnetic flux relate to dark matter?',
      'hypotheses':['MOND'],'equations':['1 + 1 = 2']})
    assert result.status_code == 200
    assert result.json()['status'] == 'INSUFFICIENT_EVIDENCE'
    assert result.json()['math_checks'][0]['status'] == 'EQUAL'
