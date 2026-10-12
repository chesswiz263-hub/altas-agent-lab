"""v0.4 durable job queue, cancellation, migration, access control, memory and calibration."""
import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from atlas.api import create_app
from atlas.calibration import calibrate
from atlas.jobs import Jobs, LocalWorker
from atlas.store import Store


VALID = {'prompt': 'What are reliable agent safety safeguards?', 'provider': 'demo',
         'model': None, 'max_steps': 3, 'max_cost_usd': None, 'use_memory': False}


def wait_job(client, ident, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.get(f'/api/jobs/{ident}').json()['status']
        if status in {'completed', 'budget_exhausted', 'failed', 'cancelled', 'interrupted'}:
            return status
        time.sleep(.015)
    raise AssertionError('Background job did not finish')


def test_queue_job_replay_and_event_cursor(store):
    store.add_document('Safety', 'Agents enforce strict tool allowlists and bounded execution steps.')
    with TestClient(create_app(store)) as client:
        r = client.post('/api/jobs', json={**VALID, 'mode': 'single'})
        assert r.status_code == 202
        ident = r.json()['id']
        assert wait_job(client, ident) == 'completed'
        run = client.get(f'/api/runs/{ident}').json()
        assert run['answer'] and run['status'] == 'completed'
        events = client.get(f'/api/jobs/{ident}/events', params={'after': 0}).json()['events']
        assert any(x['type'] == 'tool_call' for x in events)
        assert any(x['type'] == 'final' for x in events)
        later = client.get(f'/api/jobs/{ident}/events', params={'after': events[2]['cursor']}).json()['events']
        assert later and all(x['cursor'] > events[2]['cursor'] for x in later)
        assert client.post(f'/api/jobs/{ident}/cancel').json()['status'] == 'completed'
        assert client.get('/api/jobs/does-not-exist').status_code == 404


def test_queue_survives_and_in_flight_runs_do_not_replay(tmp_path):
    path = tmp_path / 'queue.db'
    store = Store(path)
    jobs = Jobs(store)
    queued = jobs.enqueue(VALID, 'single')
    running = jobs.enqueue(VALID, 'single')
    job = jobs.claim()
    assert job['id'] == queued['id']
    store.start_run(job['id'], VALID['prompt'], 'demo', 'atlas-demo-v1')
    assert jobs.recover() == 1
    assert jobs.get(queued['id'])['status'] == 'interrupted'
    assert store.get_run(queued['id'])['status'] == 'interrupted'
    assert jobs.get(running['id'])['status'] == 'queued'
    assert Jobs(Store(path)).get(running['id'])['status'] == 'queued'


def test_cancel_queued_prevents_claim(tmp_path):
    jobs = Jobs(Store(tmp_path / 'jobs.db'))
    first = jobs.enqueue(VALID, 'single')
    assert jobs.cancel(first['id'])['status'] == 'cancelled'
    assert jobs.claim() is None
    assert jobs.cancel('nonexistent') is None


@pytest.mark.asyncio
async def test_cancel_running_task_during_model_call(monkeypatch, tmp_path):
    import atlas.jobs as module

    class SlowAgent:
        def __init__(self, *args, **kwargs):
            pass

        async def stream(self, *args, **kwargs):
            yield {'type': 'start', 'model': 'slow'}
            await asyncio.sleep(10)
            yield {'type': 'final', 'answer': 'Should never return', 'steps': 1,
                   'input_tokens': 0, 'output_tokens': 0}

    monkeypatch.setattr(module, 'Agent', SlowAgent)
    store = Store(tmp_path / 'cancel.db')
    jobs = Jobs(store)
    worker = LocalWorker(jobs, interval=.005)
    await worker.start()
    try:
        ident = jobs.enqueue(VALID, 'single')['id']
        for _ in range(100):
            if jobs.get(ident)['status'] == 'running':
                break
            await asyncio.sleep(.01)
        assert jobs.get(ident)['status'] == 'running'
        assert jobs.cancel(ident)['cancel_requested']
        for _ in range(100):
            if jobs.get(ident)['status'] == 'cancelled':
                break
            await asyncio.sleep(.01)
        assert jobs.get(ident)['status'] == 'cancelled'
        assert store.get_run(ident)['status'] == 'cancelled'
        assert any(e['type'] == 'cancelled' for e in jobs.events(ident))
    finally:
        await worker.stop()


def test_optional_bearer_auth_and_health(monkeypatch, store):
    monkeypatch.setenv('ATLAS_API_TOKEN', 'this-is-only-a-test-value')
    with TestClient(create_app(store)) as client:
        assert client.get('/api/health').status_code == 200
        assert client.get('/api/status').status_code == 401
        assert client.post('/api/jobs', json={**VALID, 'mode': 'single'}).status_code == 401
        assert client.get('/api/status', headers={'X-Atlas-Token': 'wrong'}).status_code == 401
        hdr = {'Authorization': 'Bearer this-is-only-a-test-value'}
        assert client.get('/api/status', headers=hdr).status_code == 200
        assert client.get('/api/status', headers={'X-Atlas-Token': 'this-is-only-a-test-value'}).status_code == 200
        assert client.get('/').status_code == 200  # static UI is not secret


def test_memory_is_explicit_editable_and_opt_in(store):
    with TestClient(create_app(store)) as client:
        assert client.get('/api/memories').json() == []
        memo = client.post('/api/memories', json={'title': 'Safety focus', 'content': 'Prioritize agent safety.'})
        assert memo.status_code == 201
        note = memo.json()
        assert store.search_memories('agent safety')[0]['id'] == note['id']
        assert client.post('/api/jobs', json={**VALID, 'use_memory': True, 'mode': 'single'}).status_code == 202
        assert client.get('/api/memories').json()[0]['id'] == note['id']
        assert client.delete(f'/api/memories/{note["id"]}').status_code == 200
        assert store.search_memories('agent safety') == []
        assert client.delete(f'/api/memories/{note["id"]}').status_code == 404


def test_calibrated_fixture_does_not_modify_user_documents(store):
    with TestClient(create_app(store)) as client:
        assert client.get('/api/documents').json() == []
        response = client.get('/api/evaluations/calibration')
        assert response.status_code == 200
        report = response.json()
        assert report['cases'] == 10 and report['accuracy'] == 1.0
        assert set(report['per_label']) == {'surface_aligned', 'numeric_mismatch',
                                          'invalid_citation', 'weak_alignment', 'unattributed'}
        assert client.get('/api/documents').json() == []
    assert calibrate()['cases'] == 10


def test_provider_and_run_validations(store):
    with TestClient(create_app(store)) as client:
        assert client.post('/api/jobs', json={**VALID, 'mode': 'auto', 'max_steps': 6}).status_code == 400
        assert client.post('/api/jobs', json={**VALID, 'mode': 'invalid'}).status_code == 422
        assert client.post('/api/jobs', json={**VALID, 'mode': 'single', 'provider': 'openai'}).status_code == 400
        assert client.get('/api/jobs/nonsense/events').status_code == 404


def test_memory_context_only_on_explicit_queued_opt_in(store):
    store.add_memory('Agent safety', 'Agent safety prioritizes test coverage and audit traces.')
    store.add_document('Audit trace policy', 'Test coverage and audit traces improve engineering verification.')
    with TestClient(create_app(store)) as client:
        for allowed in (False, True):
            body = {**VALID, 'mode': 'single', 'use_memory': allowed}
            response = client.post('/api/jobs', json=body)
            assert response.status_code == 202
            ident = response.json()['id']
            assert wait_job(client, ident) == 'completed'
            events = client.get(f'/api/jobs/{ident}/events').json()['events']
            memory_context = [e for e in events if e['type'] == 'memory_context']
            assert bool(memory_context) == allowed
            if allowed:
                assert len(memory_context[0]['note_ids']) == 1
                assert 'content' not in memory_context[0]


def test_job_summary_counts_across_completed_runs(store):
    with TestClient(create_app(store)) as client:
        for _ in range(2):
            ident = client.post('/api/jobs', json={**VALID, 'mode': 'single'}).json()['id']
            assert wait_job(client, ident) == 'completed'
        totals = client.get('/api/status').json()['jobs']
        assert totals.get('completed') == 2
        assert totals.get('running', 0) == 0
