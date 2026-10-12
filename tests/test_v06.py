"""v0.6 static public demo packaging and backend/private split checks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_static_site_is_self_contained():
    html = (ROOT / 'docs/index.html').read_text(encoding='utf-8')
    assert '<title>ATLAS — Public Research Demo</title>' in html
    assert 'not a live LLM' in html
    for asset in ('corpus.js', 'engine.js', 'app.js', 'styles.css', 'favicon.svg'):
        assert (ROOT / f'docs/demo/{asset}').is_file()
        assert './demo/' + asset in html
    assert (ROOT / 'docs/.nojekyll').is_file()


def test_public_browser_files_do_not_contain_secret_placeholders_or_private_api_calls():
    public = '\n'.join((ROOT / f'docs/demo/{asset}').read_text(encoding='utf-8')
                       for asset in ('corpus.js', 'engine.js', 'app.js'))
    assert 'OPENAI_API_KEY' not in public
    assert 'ANTHROPIC_API_KEY' not in public
    assert 'GEMINI_API_KEY' not in public
    assert 'ATLAS_SESSION_SECRET' not in public
    assert 'fetch(' not in public
    assert 'localStorage' not in public
    assert '/api/jobs' not in public


def test_private_v05_workspace_retained_with_public_demo():
    assert (ROOT / '.devcontainer/devcontainer.json').is_file()
    assert (ROOT / 'src/atlas/web_auth.py').is_file()
    assert (ROOT / 'render.yaml').is_file()
    assert (ROOT / 'static/login.html').is_file()


def test_ci_includes_python_and_browser_suite():
    workflow = (ROOT / '.github/workflows/ci.yml').read_text()
    assert 'pytest -q' in workflow
    assert 'node --test tests/browser/*.test.cjs' in workflow
    assert '3.11' in workflow and '3.12' in workflow and '3.13' in workflow
