"""v0.5 hosted browser boundaries, no credential leakage, private workspace access."""
import base64
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from atlas.api import create_app
from atlas.store import Store
from atlas.web_auth import WebAuth

PASSWORD = 'correct-horse-battery-staple-2026'
SECRET = 'test-secret-keep-this-out-of-a-public-repository-0123456789'
ORIGIN = 'https://atlas.example.test'


@pytest.fixture
def hosted(monkeypatch, tmp_path):
    monkeypatch.setenv('ATLAS_HOSTED_MODE', '1')
    monkeypatch.setenv('ATLAS_ADMIN_PASSWORD', PASSWORD)
    monkeypatch.setenv('ATLAS_SESSION_SECRET', SECRET)
    monkeypatch.setenv('ATLAS_PUBLIC_ORIGIN', ORIGIN)
    monkeypatch.delenv('ATLAS_API_TOKEN', raising=False)
    with TestClient(create_app(Store(tmp_path / 'app.db')), base_url=ORIGIN) as client:
        yield client


def sign_in(client):
    result = client.post('/auth/login', headers={'Origin': ORIGIN}, json={'password': PASSWORD})
    assert result.status_code == 200, result.text
    assert 'httponly' in result.headers['set-cookie'].lower()
    assert 'secure' in result.headers['set-cookie'].lower()
    assert 'samesite=strict' in result.headers['set-cookie'].lower()
    return result.json()['csrf']


def test_fails_closed_without_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv('ATLAS_HOSTED_MODE', '1')
    monkeypatch.delenv('ATLAS_ADMIN_PASSWORD', raising=False)
    monkeypatch.delenv('ATLAS_SESSION_SECRET', raising=False)
    with pytest.raises(RuntimeError, match='ATLAS_ADMIN_PASSWORD'):
        create_app(Store(tmp_path / 'store.db'))
    monkeypatch.setenv('ATLAS_ADMIN_PASSWORD', PASSWORD)
    monkeypatch.setenv('ATLAS_SESSION_SECRET', 'short')
    with pytest.raises(RuntimeError):
        create_app(Store(tmp_path / 'store.db'))


def test_hosted_blocks_dashboard_api_and_docs_without_login(hosted):
    assert hosted.get('/api/health').status_code == 200
    assert hosted.get('/api/health').json()['version'] == '1.0.0'
    for path in ('/', '/static/app.js', '/docs', '/openapi.json', '/api/status', '/api/memories'):
        resp = hosted.get(path, follow_redirects=False)
        assert resp.status_code in (303, 401), (path, resp.status_code)
    assert hosted.get('/login').status_code == 200
    assert hosted.get('/auth/login.js').status_code == 200
    assert hosted.get('/auth/login.css').status_code == 200
    assert hosted.get('/auth/session').status_code == 401
    assert 'ATLAS' in hosted.get('/login').text


def test_hosted_login_session_csrf_and_logout(hosted):
    assert hosted.post('/auth/login', headers={'Origin': ORIGIN}, json={'password': 'wrong'}).status_code == 401
    assert hosted.post('/auth/login', headers={'Origin':'https://evil.example'}, json={'password': PASSWORD}).status_code == 403
    csrf = sign_in(hosted)
    assert hosted.get('/').status_code == 200
    assert hosted.get('/static/app.js').status_code == 200
    assert hosted.get('/docs').status_code == 200
    assert hosted.get('/api/status').status_code == 200
    assert hosted.get('/auth/session').json()['csrf'] == csrf
    assert hosted.post('/api/documents', json={'title':'Sample','content':'A sufficiently long document'}).status_code == 403
    assert hosted.post('/api/documents', headers={'X-Atlas-CSRF':'false'}, json={'title':'Sample','content':'A sufficiently long document'}).status_code == 403
    assert hosted.post('/api/documents', headers={'X-Atlas-CSRF':csrf,'Origin':'https://evil.example'},json={'title':'Sample','content':'A sufficiently long document'}).status_code == 403
    assert hosted.post('/api/documents', headers={'X-Atlas-CSRF':csrf,'Origin':ORIGIN},json={'title':'Sample','content':'A sufficiently long document'}).status_code == 201
    assert hosted.post('/auth/logout', headers={'X-Atlas-CSRF':csrf,'Origin':ORIGIN}).status_code == 200
    assert hosted.get('/api/status').status_code == 401


def test_hosted_provider_run_stays_private(hosted):
    csrf = sign_in(hosted)
    resp = hosted.post('/api/jobs',headers={'X-Atlas-CSRF':csrf,'Origin':ORIGIN},json={
        'prompt':'Summarize agent safety best practices','provider':'demo','mode':'single','max_steps':2})
    assert resp.status_code == 202
    ident = resp.json()['id']
    assert hosted.get('/api/jobs/'+ident).status_code == 200
    assert hosted.get('/api/jobs/'+ident+'/events').status_code == 200


def test_session_expiry_and_tampering(monkeypatch):
    monkeypatch.setenv('ATLAS_HOSTED_MODE','1')
    monkeypatch.setenv('ATLAS_ADMIN_PASSWORD',PASSWORD)
    monkeypatch.setenv('ATLAS_SESSION_SECRET',SECRET)
    auth=WebAuth.from_environment()
    cookie=auth.session()
    assert auth.valid_session(cookie)
    assert not auth.valid_session(cookie[:-3]+'abc')
    assert not auth.valid_session('')
    payload=base64.urlsafe_b64encode(f'{int(time.time())-36000}:nonceatleast24characterslong'.encode()).decode().rstrip('=')
    expired=payload+'.'+auth._sign(payload)
    assert not auth.valid_session(expired)


def test_login_rate_limits_attempts(hosted):
    for _ in range(10):
        assert hosted.post('/auth/login',headers={'Origin':ORIGIN},json={'password':'not-it'}).status_code==401
    assert hosted.post('/auth/login',headers={'Origin':ORIGIN},json={'password':PASSWORD}).status_code==429


def test_unprotected_local_defaults(monkeypatch, tmp_path):
    monkeypatch.delenv('ATLAS_HOSTED_MODE',raising=False)
    with TestClient(create_app(Store(tmp_path/'local.db'))) as client:
        assert client.get('/').status_code==200
        assert client.get('/auth/session').json()=={'authenticated':True,'hosted':False,'csrf':None}
        assert client.get('/api/status').status_code==200
        assert client.post('/api/documents',json={'title':'Title','content':'A complete example document'}).status_code==201


def test_codespace_and_render_configs_present():
    root=Path(__file__).resolve().parents[1]
    config=json.loads((root/'.devcontainer/devcontainer.json').read_text())
    assert 8000 in config['forwardPorts']
    assert config['portsAttributes']['8000']['visibility']=='private'
    blueprint=(root/'render.yaml').read_text()
    assert 'ATLAS_HOSTED_MODE' in blueprint and 'ATLAS_ADMIN_PASSWORD' in blueprint
    assert 'sync: false' in blueprint and 'mountPath: /app/data' in blueprint
