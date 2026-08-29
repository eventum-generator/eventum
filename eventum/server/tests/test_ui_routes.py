"""Tests for UI SPA routes."""

from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.server.services.ui.cache import (
    ASSET_CACHE_CONTROL,
    SHELL_CACHE_CONTROL,
    ImmutableStaticFiles,
)
from eventum.server.services.ui.routes import router

MODULE = 'eventum.server.services.ui.routes'


def build_app(www_dir: Path) -> FastAPI:
    """Build app wired the way the UI service injector wires it."""
    app = FastAPI()
    app.mount(
        path='/assets',
        app=ImmutableStaticFiles(directory=www_dir / 'assets'),
        name='Web UI assets',
    )
    app.include_router(router)

    return app


def build_www(www_dir: Path) -> None:
    """Fill directory with a shell, a plain file and a hashed asset."""
    (www_dir / 'index.html').write_text('<html>SPA</html>')
    (www_dir / 'logo.svg').write_text('<svg>logo</svg>')

    assets_dir = www_dir / 'assets'
    assets_dir.mkdir()
    (assets_dir / 'index-DB-tz65q.css').write_text('body{color:red}')


def test_spa_returns_index_for_unknown_path(tmp_path):
    index = tmp_path / 'index.html'
    index.write_text('<html>SPA</html>')

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client, patch(f'{MODULE}.WWW_DIR', tmp_path):
        response = client.get('/some/page')
    assert response.status_code == 200
    assert 'SPA' in response.text


def test_api_prefix_returns_404(tmp_path):
    index = tmp_path / 'index.html'
    index.write_text('<html>SPA</html>')

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client, patch(f'{MODULE}.WWW_DIR', tmp_path):
        response = client.get('/api/something')
    assert response.status_code == 404


def test_existing_file_served_directly(tmp_path):
    index = tmp_path / 'index.html'
    index.write_text('<html>SPA</html>')
    logo = tmp_path / 'logo.svg'
    logo.write_text('<svg>logo</svg>')

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client, patch(f'{MODULE}.WWW_DIR', tmp_path):
        response = client.get('/logo.svg')
    assert response.status_code == 200
    assert 'logo' in response.text


def test_shell_is_revalidated(tmp_path):
    build_www(tmp_path)

    app = build_app(tmp_path)
    with TestClient(app) as client, patch(f'{MODULE}.WWW_DIR', tmp_path):
        response = client.get('/some/page')
    assert response.headers['cache-control'] == SHELL_CACHE_CONTROL


def test_plain_file_is_revalidated(tmp_path):
    build_www(tmp_path)

    app = build_app(tmp_path)
    with TestClient(app) as client, patch(f'{MODULE}.WWW_DIR', tmp_path):
        response = client.get('/logo.svg')
    assert response.headers['cache-control'] == SHELL_CACHE_CONTROL


def test_asset_is_cached_immutably(tmp_path):
    build_www(tmp_path)

    app = build_app(tmp_path)
    with TestClient(app) as client, patch(f'{MODULE}.WWW_DIR', tmp_path):
        response = client.get('/assets/index-DB-tz65q.css')
    assert response.status_code == 200
    assert response.text == 'body{color:red}'
    assert response.headers['cache-control'] == ASSET_CACHE_CONTROL


def test_unchanged_asset_keeps_cache_control(tmp_path):
    build_www(tmp_path)

    app = build_app(tmp_path)
    with TestClient(app) as client, patch(f'{MODULE}.WWW_DIR', tmp_path):
        etag = client.get('/assets/index-DB-tz65q.css').headers['etag']
        response = client.get(
            '/assets/index-DB-tz65q.css',
            headers={'if-none-match': etag},
        )
    assert response.status_code == 304
    assert response.headers['cache-control'] == ASSET_CACHE_CONTROL


def test_missing_asset_does_not_fall_back_to_shell(tmp_path):
    build_www(tmp_path)

    app = build_app(tmp_path)
    with TestClient(app) as client, patch(f'{MODULE}.WWW_DIR', tmp_path):
        response = client.get('/assets/index-gone.css')
    assert response.status_code == 404
    assert 'SPA' not in response.text
