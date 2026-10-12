"""Deployment configuration and response header checks."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from atlas.api import create_app
from atlas.store import Store
from atlas.web_auth import WebAuth


def test_render_domain_is_auto_inferred(monkeypatch):
    monkeypatch.setenv('ATLAS_HOSTED_MODE', '1')
    monkeypatch.setenv('ATLAS_ADMIN_PASSWORD', 'a-correct-private-password-123456')
    monkeypatch.setenv('ATLAS_SESSION_SECRET', 'a-different-random-test-secret-1234567890123456')
    monkeypatch.delenv('ATLAS_PUBLIC_ORIGIN', raising=False)
    monkeypatch.setenv('RENDER_EXTERNAL_HOSTNAME', 'example.onrender.com')
    assert WebAuth.from_environment().public_origin == 'https://example.onrender.com'


def test_security_headers_on_local_health(monkeypatch,tmp_path):
    monkeypatch.delenv('ATLAS_HOSTED_MODE', raising=False)
    with TestClient(create_app(Store(tmp_path/'s.db'))) as client:
        headers=client.get('/api/health').headers
        assert headers['x-frame-options']=='DENY'
        assert "script-src 'self'" in headers['content-security-policy']
        assert headers['x-content-type-options']=='nosniff'


def test_browser_assets_ship_with_source():
    root = Path(__file__).resolve().parents[1]
    assert (root/'static/login.html').is_file()
    assert (root/'static/login.js').is_file()
    assert (root/'static/login.css').is_file()
    assert (root/'.devcontainer/start-atlas.sh').is_file()
    assert '8000' in (root/'.devcontainer/devcontainer.json').read_text()
    assert 'atlas' in (root/'render.yaml').read_text()
