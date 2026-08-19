"""Discovery of repositories that publish generators in the open.

A repository joins the list by carrying the `eventum-generators` topic
on GitHub - nothing is registered here and nothing is reviewed, so what
the search returns is what the authors of those repositories published
about themselves.

Requests are anonymous: an instance asks GitHub the same way a browser
would, without a token to configure. That buys a small quota - ten
searches a minute per address - so the service caches what it read and
revalidates it with the entity tag GitHub returns.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from eventum import __version__
from eventum.app.repositories.exceptions import (
    RepositoryDiscoveryError,
    RepositoryDiscoveryLimitError,
)
from eventum.app.repositories.models import (
    DiscoveredRepository,
    DiscoveryRate,
)

# Topic a repository carries to appear in the list. It names what the
# repository holds rather than the product alone, so an author reading
# it in the settings of their repository knows what is expected inside.
DISCOVERY_TOPIC = 'eventum-generators'

# Organization the Eventum repositories are published by, marked apart
# from what the community publishes.
OFFICIAL_OWNER = 'eventum-generator'

SEARCH_URL = 'https://api.github.com/search/repositories'

# Version of the REST API this code is written against. GitHub asks
# every caller to name one, so a later default cannot change what an
# already released Eventum receives.
API_VERSION = '2022-11-28'

DEFAULT_DISCOVERY_TIMEOUT = 10.0
RESULTS_PER_PAGE = 30
MAX_DISCOVERY_PAGE = 10
MAX_DISCOVERY_QUERY_LENGTH = 100

_SEARCH_LIMIT_STATUSES = frozenset({403, 429})

# Everything a search qualifier is written with is taken out of what
# the user types, so the words narrow the list rather than replace the
# topic that defines it.
_QUERY_ALLOWED = re.compile(r'[^\w \-./]', re.UNICODE)

_USER_AGENT = f'Eventum/{__version__} (+https://eventum.run)'

_LIMIT_HINT = (
    'GitHub limits anonymous searches to ten a minute per address; '
    'the list is read again once the limit resets'
)
_UNREACHABLE_HINT = 'GitHub cannot be reached from this instance'


@dataclass(frozen=True)
class DiscoverySearch:
    """Answer of one search request.

    Attributes
    ----------
    modified : bool
        Whether GitHub returned a new answer. False when the entity tag
        the request carried still describes the current one, in which
        case the entries are empty and what the caller holds stands.

    entries : tuple[DiscoveredRepository, ...]
        Repositories the search returned.

    total_count : int
        Number of repositories the search matched in total.

    etag : str | None
        Entity tag of the answer, to revalidate it with later.

    rate : DiscoveryRate
        What GitHub reported of the quota left for this address.

    """

    modified: bool
    entries: tuple[DiscoveredRepository, ...]
    total_count: int
    etag: str | None
    rate: DiscoveryRate


def normalize_query(query: str | None) -> str:
    """Return the words of a query, without search qualifiers.

    Parameters
    ----------
    query : str | None
        Text the user typed.

    Returns
    -------
    str
        Words to narrow the search with, empty when nothing is left of
        the query.

    """
    if not query:
        return ''

    cleaned = _QUERY_ALLOWED.sub(' ', query)

    return ' '.join(cleaned.split())[:MAX_DISCOVERY_QUERY_LENGTH].strip()


def search_repositories(
    *,
    query: str | None = None,
    page: int = 1,
    etag: str | None = None,
    timeout: float = DEFAULT_DISCOVERY_TIMEOUT,
) -> DiscoverySearch:
    """Search the repositories that publish generators in the open.

    Parameters
    ----------
    query : str | None, default=None
        Words to narrow the search with. Search qualifiers are taken
        out of it, so the topic defining the list always applies.

    page : int, default=1
        Page of the results, counted from one.

    etag : str | None, default=None
        Entity tag of the answer held for this search, to revalidate
        it instead of transferring the same answer again.

    timeout : float, default=DEFAULT_DISCOVERY_TIMEOUT
        Timeout of the request, in seconds.

    Returns
    -------
    DiscoverySearch
        What the search returned, or the note that what the caller
        holds still stands.

    Raises
    ------
    RepositoryDiscoveryLimitError
        If GitHub refused the request because the quota of this
        address is spent.

    RepositoryDiscoveryError
        If GitHub cannot be reached or answered with something this
        code cannot read.

    """
    words = normalize_query(query)
    params = {
        'q': f'topic:{DISCOVERY_TOPIC} {words}'.strip(),
        'sort': 'stars',
        'order': 'desc',
        'per_page': str(RESULTS_PER_PAGE),
        'page': str(max(1, min(page, MAX_DISCOVERY_PAGE))),
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                SEARCH_URL,
                params=params,
                headers=_headers(etag),
            )
    except httpx.HTTPError as e:
        msg = 'Failed to search the published repositories'
        raise RepositoryDiscoveryError(
            msg,
            context={'reason': str(e), 'hint': _UNREACHABLE_HINT},
        ) from None

    rate = _read_rate(response.headers)

    if response.status_code == httpx.codes.NOT_MODIFIED:
        return DiscoverySearch(
            modified=False,
            entries=(),
            total_count=0,
            etag=etag,
            rate=rate,
        )

    _raise_for_status(response, rate)

    return _read_answer(response, rate)


def _headers(etag: str | None) -> dict[str, str]:
    """Build the headers of a search request."""
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': API_VERSION,
        'User-Agent': _USER_AGENT,
    }

    if etag is not None:
        headers['If-None-Match'] = etag

    return headers


def _raise_for_status(response: httpx.Response, rate: DiscoveryRate) -> None:
    """Translate a refused search into the error it stands for.

    Raises
    ------
    RepositoryDiscoveryLimitError
        If the quota of this address is spent.

    RepositoryDiscoveryError
        If GitHub refused the request for any other reason.

    """
    if response.status_code == httpx.codes.OK:
        return

    reason = _read_message(response)

    if response.status_code in _SEARCH_LIMIT_STATUSES:
        msg = 'Searching the published repositories is rate limited'
        raise RepositoryDiscoveryLimitError(
            msg,
            context={
                'reason': reason,
                'hint': _LIMIT_HINT,
                'seconds': _retry_after(response, rate),
            },
        )

    msg = 'Failed to search the published repositories'
    raise RepositoryDiscoveryError(
        msg,
        context={'reason': reason, 'http_status': response.status_code},
    )


def _read_message(response: httpx.Response) -> str:
    """Return what GitHub said about a refused request."""
    try:
        payload = response.json()
    except ValueError:
        return f'GitHub answered with status {response.status_code}'

    message = payload.get('message') if isinstance(payload, dict) else None

    return str(
        message or f'GitHub answered with status {response.status_code}'
    )


def _read_answer(
    response: httpx.Response,
    rate: DiscoveryRate,
) -> DiscoverySearch:
    """Read the repositories a successful search returned.

    Raises
    ------
    RepositoryDiscoveryError
        If the answer is not the document this code reads.

    """
    try:
        payload = response.json()
        items = payload['items']
        total = int(payload.get('total_count', len(items)))
    except (ValueError, KeyError, TypeError) as e:
        msg = 'Failed to read what GitHub answered'
        raise RepositoryDiscoveryError(
            msg,
            context={'reason': str(e)},
        ) from None

    return DiscoverySearch(
        modified=True,
        entries=tuple(_read_entries(items)),
        total_count=total,
        etag=response.headers.get('etag'),
        rate=rate,
    )


def _read_entries(items: Any) -> list[DiscoveredRepository]:
    """Read the repositories of an answer, skipping what cannot be read.

    A repository GitHub describes in a way this version does not
    understand is left out rather than failing the whole list, since
    one odd entry must not hide the rest of what is published.
    """
    entries: list[DiscoveredRepository] = []

    for item in items if isinstance(items, list) else []:
        entry = _read_entry(item)

        if entry is not None:
            entries.append(entry)

    return entries


def _read_entry(item: Any) -> DiscoveredRepository | None:
    """Read one repository of an answer, or None when it cannot be read."""
    if not isinstance(item, dict):
        return None

    owner = item.get('owner') or {}
    owner_name = owner.get('login') if isinstance(owner, dict) else None
    license_of = item.get('license') or {}
    license_name = (
        license_of.get('spdx_id') if isinstance(license_of, dict) else None
    )

    try:
        return DiscoveredRepository(
            name=item['name'],
            full_name=item['full_name'],
            url=item['clone_url'],
            page_url=item['html_url'],
            owner=str(owner_name or ''),
            description=item.get('description'),
            topics=tuple(item.get('topics') or ()),
            stars=int(item.get('stargazers_count', 0)),
            updated_at=_read_moment(item.get('pushed_at')),
            license=None if license_name == 'NOASSERTION' else license_name,
            archived=bool(item.get('archived', False)),
            official=str(owner_name or '').lower() == OFFICIAL_OWNER,
        )
    except KeyError, TypeError, ValueError, ValidationError:
        return None


def _read_moment(value: Any) -> datetime | None:
    """Read a moment GitHub reports, or None when there is none."""
    if not isinstance(value, str):
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _read_rate(headers: httpx.Headers) -> DiscoveryRate:
    """Read what the answer reports of the quota left for this address."""
    return DiscoveryRate(
        remaining=_read_int(headers.get('x-ratelimit-remaining')),
        reset_at=_read_reset(headers.get('x-ratelimit-reset')),
    )


def _read_int(value: str | None) -> int | None:
    """Read a header holding a number, or None when it holds none."""
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _read_reset(value: str | None) -> datetime | None:
    """Read the moment a spent quota is restored at."""
    seconds = _read_int(value)

    if seconds is None:
        return None

    try:
        return datetime.fromtimestamp(seconds, tz=UTC)
    except OverflowError, OSError, ValueError:
        return None


def _retry_after(response: httpx.Response, rate: DiscoveryRate) -> int | None:
    """Return the seconds to wait before searching again.

    GitHub answers a refused request either with the delay to keep, or
    with the moment the quota is restored at.
    """
    delay = _read_int(response.headers.get('retry-after'))

    if delay is not None:
        return max(0, delay)

    if rate.reset_at is None:
        return None

    return max(0, int((rate.reset_at - datetime.now(tz=UTC)).total_seconds()))
