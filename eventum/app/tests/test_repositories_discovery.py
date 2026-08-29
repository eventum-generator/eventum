"""Tests of searching the repositories published in the open."""

import json
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

from eventum.app.repositories import (
    DISCOVERY_TOPIC,
    Repositories,
    Repository,
    RepositoryDiscoveryError,
    RepositoryDiscoveryLimitError,
)
from eventum.app.repositories import discovery as discovery_module
from eventum.app.repositories.discovery import (
    normalize_query,
    search_repositories,
)
from eventum.app.repositories.service import DISCOVERY_CACHE_LIMIT

CONFIG_FILENAME = 'generator.yml'

ITEM = {
    'name': 'content-packs',
    'full_name': 'eventum-generator/content-packs',
    'clone_url': 'https://github.com/eventum-generator/content-packs.git',
    'html_url': 'https://github.com/eventum-generator/content-packs',
    'owner': {'login': 'eventum-generator'},
    'description': 'Ready-made generators for Eventum',
    'topics': [DISCOVERY_TOPIC, 'synthetic-data'],
    'stargazers_count': 42,
    'pushed_at': '2026-07-31T12:24:16Z',
    'license': {'spdx_id': 'Apache-2.0'},
    'archived': False,
}

OTHER_ITEM = {
    **ITEM,
    'name': 'my-packs',
    'full_name': 'someone/my-packs',
    'clone_url': 'https://github.com/someone/my-packs.git',
    'html_url': 'https://github.com/someone/my-packs',
    'owner': {'login': 'someone'},
    'description': None,
    'stargazers_count': 512,
    'license': None,
}


class _QuietHandler(WSGIRequestHandler):
    """Request handler that keeps the test output clean."""

    def log_message(self, *args: object) -> None:
        pass


class _Github:
    """Stand-in for the GitHub search endpoint.

    Records what was asked and answers what a test set, so the whole
    request - its parameters, its headers and the answer it receives -
    is exercised over a real connection.
    """

    def __init__(self) -> None:
        self.requests: list[dict[str, str]] = []
        self.answer: Callable[[], tuple[int, dict[str, str], object]] = (
            lambda: (200, {}, {'total_count': 1, 'items': [ITEM]})
        )

    def __call__(self, environ: dict, start_response: Callable) -> list[bytes]:
        self.requests.append(
            {
                'query': environ.get('QUERY_STRING', ''),
                'accept': environ.get('HTTP_ACCEPT', ''),
                'version': environ.get('HTTP_X_GITHUB_API_VERSION', ''),
                'agent': environ.get('HTTP_USER_AGENT', ''),
                'etag': environ.get('HTTP_IF_NONE_MATCH', ''),
            },
        )
        status, headers, payload = self.answer()
        body = (
            b''
            if payload is None
            else json.dumps(payload).encode()
            if not isinstance(payload, bytes)
            else payload
        )
        start_response(
            f'{status} X',
            [('Content-Type', 'application/json'), *headers.items()],
        )

        return [body]


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Github]:
    """Serve the search endpoint locally and point the code at it."""
    app = _Github()
    server = make_server('127.0.0.1', 0, app, handler_class=_QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    monkeypatch.setattr(
        discovery_module,
        'SEARCH_URL',
        f'http://127.0.0.1:{server.server_port}/search/repositories',
    )

    try:
        yield app
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _service(tmp_path: Path, **kwargs: float) -> Repositories:
    return Repositories(
        file_path=tmp_path / 'repositories.yml',
        generators_dir=tmp_path / 'generators',
        config_filename=CONFIG_FILENAME,
        **kwargs,  # type: ignore[arg-type]
    )


# --- the request ---


def test_search_asks_for_the_topic(github: _Github) -> None:
    search_repositories()

    query = github.requests[0]['query']
    assert f'q=topic%3A{DISCOVERY_TOPIC}' in query
    assert 'sort=stars' in query
    assert 'page=1' in query


def test_search_identifies_itself(github: _Github) -> None:
    search_repositories()

    request = github.requests[0]
    assert request['accept'] == 'application/vnd.github+json'
    assert request['version'] == discovery_module.API_VERSION
    assert request['agent'].startswith('Eventum/')


def test_search_narrows_by_words(github: _Github) -> None:
    search_repositories(query='nginx access')

    assert 'nginx+access' in github.requests[0]['query']


def test_search_drops_qualifiers_of_a_query(github: _Github) -> None:
    # A qualifier typed into the box would replace what defines the
    # list, so only words survive.
    search_repositories(query='nginx topic:other "quoted"')

    query = github.requests[0]['query']
    assert 'topic%3Aother' not in query
    assert f'topic%3A{DISCOVERY_TOPIC}' in query


def test_search_clamps_the_page(github: _Github) -> None:
    search_repositories(page=999)

    assert (
        f'page={discovery_module.MAX_DISCOVERY_PAGE}'
        in (github.requests[0]['query'])
    )


def test_search_revalidates_with_the_entity_tag(github: _Github) -> None:
    search_repositories(etag='"abc"')

    assert github.requests[0]['etag'] == '"abc"'


def test_normalize_query_keeps_words_only() -> None:
    assert normalize_query(' nginx  topic:other ') == 'nginx topic other'
    assert normalize_query(None) == ''
    assert len(normalize_query('x' * 500)) == (
        discovery_module.MAX_DISCOVERY_QUERY_LENGTH
    )


# --- the answer ---


def test_search_reads_what_a_repository_says(github: _Github) -> None:
    result = search_repositories()

    assert result.modified is True
    assert result.total_count == 1

    entry = result.entries[0]
    assert entry.full_name == 'eventum-generator/content-packs'
    assert entry.url == ITEM['clone_url']
    assert entry.stars == 42
    assert entry.license == 'Apache-2.0'
    assert entry.official is True
    assert entry.connected is False


def test_search_marks_what_is_published_by_others(github: _Github) -> None:
    github.answer = lambda: (
        200,
        {},
        {'total_count': 1, 'items': [OTHER_ITEM]},
    )

    entry = search_repositories().entries[0]

    assert entry.official is False
    assert entry.license is None
    assert entry.description is None


def test_search_reads_the_quota_left(github: _Github) -> None:
    github.answer = lambda: (
        200,
        {'X-RateLimit-Remaining': '7', 'X-RateLimit-Reset': '1785000000'},
        {'total_count': 0, 'items': []},
    )

    rate = search_repositories().rate

    assert rate.remaining == 7
    assert rate.reset_at is not None


def test_search_keeps_what_it_holds_when_nothing_changed(
    github: _Github,
) -> None:
    github.answer = lambda: (304, {}, None)

    result = search_repositories(etag='"abc"')

    assert result.modified is False
    assert result.etag == '"abc"'


def test_search_skips_a_repository_it_cannot_read(github: _Github) -> None:
    github.answer = lambda: (
        200,
        {},
        {'total_count': 2, 'items': [{'name': 'broken'}, ITEM]},
    )

    result = search_repositories()

    assert [entry.name for entry in result.entries] == ['content-packs']


def test_search_reports_a_spent_quota(github: _Github) -> None:
    github.answer = lambda: (
        403,
        {'Retry-After': '31'},
        {'message': 'API rate limit exceeded'},
    )

    with pytest.raises(RepositoryDiscoveryLimitError) as info:
        search_repositories()

    assert info.value.context['seconds'] == 31
    assert 'rate limit' in info.value.context['reason']


def test_search_reports_a_refused_request(github: _Github) -> None:
    github.answer = lambda: (500, {}, {'message': 'boom'})

    with pytest.raises(RepositoryDiscoveryError) as info:
        search_repositories()

    assert info.value.context['http_status'] == 500
    assert info.value.context['reason'] == 'boom'


def test_search_reports_an_unreadable_answer(github: _Github) -> None:
    github.answer = lambda: (200, {}, b'not json')

    with pytest.raises(RepositoryDiscoveryError):
        search_repositories()


def test_search_reports_a_host_that_does_not_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        discovery_module,
        'SEARCH_URL',
        'http://127.0.0.1:1/search/repositories',
    )

    with pytest.raises(RepositoryDiscoveryError) as info:
        search_repositories(timeout=1.0)

    assert 'hint' in info.value.context


# --- the service ---


def test_discover_lists_what_was_found(
    tmp_path: Path,
    github: _Github,
) -> None:
    result = _service(tmp_path).discover()

    assert result.topic == DISCOVERY_TOPIC
    assert result.total_count == 1
    assert [entry.full_name for entry in result.entries] == [
        'eventum-generator/content-packs',
    ]


def test_discover_puts_the_official_repositories_first(
    tmp_path: Path,
    github: _Github,
) -> None:
    github.answer = lambda: (
        200,
        {},
        {'total_count': 2, 'items': [OTHER_ITEM, ITEM]},
    )

    result = _service(tmp_path).discover()

    assert [entry.official for entry in result.entries] == [True, False]


def test_discover_marks_what_is_already_connected(
    tmp_path: Path,
    github: _Github,
) -> None:
    service = _service(tmp_path)
    service.add(
        Repository(
            name='packs',
            # The same repository named without the ".git" suffix is
            # the same repository.
            url='https://github.com/eventum-generator/content-packs',
        ),
        verify=False,
    )

    assert service.discover().entries[0].connected is True


def test_discover_answers_from_what_it_read(
    tmp_path: Path,
    github: _Github,
) -> None:
    service = _service(tmp_path)

    service.discover()
    service.discover()

    assert len(github.requests) == 1


def test_discover_reads_again_once_what_it_holds_is_old(
    tmp_path: Path,
    github: _Github,
) -> None:
    service = _service(tmp_path, discovery_ttl=0.0)

    service.discover()
    service.discover()

    assert len(github.requests) == 2


def test_discover_revalidates_what_it_holds(
    tmp_path: Path,
    github: _Github,
) -> None:
    github.answer = lambda: (
        200,
        {'ETag': '"abc"'},
        {'total_count': 1, 'items': [ITEM]},
    )
    service = _service(tmp_path, discovery_ttl=0.0)
    service.discover()

    github.answer = lambda: (304, {}, None)
    result = service.discover()

    assert github.requests[1]['etag'] == '"abc"'
    assert [entry.name for entry in result.entries] == ['content-packs']


def test_discover_searches_each_query_of_its_own(
    tmp_path: Path,
    github: _Github,
) -> None:
    service = _service(tmp_path)

    service.discover()
    service.discover(query='nginx')

    assert len(github.requests) == 2


def test_discover_reports_a_spent_quota(
    tmp_path: Path,
    github: _Github,
) -> None:
    github.answer = lambda: (429, {}, {'message': 'too many requests'})

    with pytest.raises(RepositoryDiscoveryLimitError):
        _service(tmp_path).discover()


def test_discover_forgets_the_oldest_searches(
    tmp_path: Path,
    github: _Github,
) -> None:
    # Every word typed into the search box is a search of its own, so
    # what is held is capped: the oldest of it is searched again while
    # the newest is still answered from.
    service = _service(tmp_path)

    for number in range(DISCOVERY_CACHE_LIMIT + 1):
        service.discover(query=f'word{number}')

    searched = len(github.requests)
    service.discover(query=f'word{DISCOVERY_CACHE_LIMIT}')
    service.discover(query='word0')

    assert len(github.requests) == searched + 1
