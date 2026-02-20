"""Tests for UI SPA routes."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.server.services.ui.routes import router

MODULE = 'eventum.server.services.ui.routes'


def test_spa_returns_index_for_unknown_path(tmp_path):
    index = tmp_path / 'index.html'
    index.write_text('<html>SPA</html>')

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    with patch(f'{MODULE}.WWW_DIR', tmp_path):
        response = client.get('/some/page')
    assert response.status_code == 200
    assert 'SPA' in response.text


def test_api_prefix_returns_404(tmp_path):
    index = tmp_path / 'index.html'
    index.write_text('<html>SPA</html>')

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    with patch(f'{MODULE}.WWW_DIR', tmp_path):
        response = client.get('/api/something')
    assert response.status_code == 404


def test_existing_file_served_directly(tmp_path):
    index = tmp_path / 'index.html'
    index.write_text('<html>SPA</html>')
    logo = tmp_path / 'logo.svg'
    logo.write_text('<svg>logo</svg>')

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    with patch(f'{MODULE}.WWW_DIR', tmp_path):
        response = client.get('/logo.svg')
    assert response.status_code == 200
    assert 'logo' in response.text
