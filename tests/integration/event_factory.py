"""Factory for creating verifiable ECS-compliant test events.

Provides deterministic event generation with embedded verification metadata,
enabling end-to-end integrity checks across output plugin integration tests.
"""

from __future__ import annotations

import hashlib
import json
import random
import string
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4


class EventSize(Enum):
    """Target event sizes for testing output plugin behavior under varying payloads."""

    SMALL = 'small'  # ~200B
    MEDIUM = 'medium'  # ~2KB
    LARGE = 'large'  # ~50KB
    HUGE = 'huge'  # ~1MB+


# Approximate target byte sizes for the generated message field.
# The full event includes ECS metadata overhead, so the message is sized
# slightly below the target to keep the total payload near the goal.
_MESSAGE_TARGET_BYTES: dict[EventSize, int] = {
    EventSize.SMALL: 80,
    EventSize.MEDIUM: 1_600,
    EventSize.LARGE: 49_000,
    EventSize.HUGE: 1_000_000,
}

_LOG_PREFIXES = [
    'INFO',
    'WARN',
    'ERROR',
    'DEBUG',
    'NOTICE',
    'CRITICAL',
    'ALERT',
]

_LOG_COMPONENTS = [
    'auth.session',
    'http.request',
    'db.query',
    'cache.evict',
    'queue.consumer',
    'scheduler.task',
    'api.gateway',
    'storage.io',
    'network.dns',
    'tls.handshake',
]

_LOG_MESSAGES = [
    'Connection established from {ip} to port {port}',
    'Request processed in {duration}ms with status {status}',
    'User {user} authenticated via {method} from {ip}',
    'Cache miss for key {key}, fetching from origin',
    'Query completed: {rows} rows affected in {duration}ms',
    'Rate limit exceeded for client {ip}: {count} requests in {window}s',
    'Certificate validation passed for {domain}, expires in {days} days',
    'DNS resolution for {domain} returned {ip} in {duration}ms',
    'Task {task_id} scheduled for execution at {timestamp}',
    'Retry attempt {attempt}/3 for operation {op_id} after {error}',
    'Health check passed: latency={duration}ms, connections={count}',
    'Payload received: {bytes} bytes from {ip}:{port}',
    'Session {session_id} expired after {duration}s of inactivity',
    'Index rebuild completed: {rows} documents in {duration}ms',
    'Outbound connection to {domain}:{port} timed out after {duration}ms',
]

_HOSTNAMES = [
    'web-prod-01.us-east-1.internal',
    'api-prod-03.eu-west-1.internal',
    'worker-batch-07.us-west-2.internal',
    'db-replica-02.ap-south-1.internal',
    'cache-node-05.eu-central-1.internal',
]

_AGENT_TYPES = ['filebeat', 'metricbeat', 'packetbeat', 'auditbeat']

_EVENT_CATEGORIES = [
    ['network'],
    ['authentication'],
    ['database'],
    ['process'],
    ['web'],
    ['host'],
]

_EVENT_KINDS = ['event', 'alert', 'metric', 'signal']

_SOURCE_IPS = [
    '10.0.1.42',
    '10.0.2.87',
    '172.16.0.15',
    '192.168.1.100',
    '10.10.5.201',
]


@dataclass(frozen=True)
class VerifiableEvent:
    """An event carrying embedded test metadata for end-to-end verification.

    Attributes:
        sequence_id: Monotonically increasing ID within a batch.
        batch_id: UUID grouping events created by the same factory instance.
        content_hash: SHA-256 hex digest of the canonical payload (excluding
            the ``_test`` metadata field).
        raw_json: The complete JSON-serialized event including ``_test`` metadata.
    """

    sequence_id: int
    batch_id: str
    content_hash: str
    raw_json: str


class EventFactory:
    """Creates verifiable ECS-compliant events for integration testing.

    Each factory instance maintains an auto-incrementing sequence counter
    and a shared batch ID so that events can be traced back to a specific
    test run.

    Usage::

        factory = EventFactory()
        event = factory.create(EventSize.MEDIUM)
        # Send event.raw_json through the output plugin, then verify
        # the persisted document still contains the original content_hash.
    """

    def __init__(self, batch_id: str | None = None) -> None:
        self._batch_id = batch_id or uuid4().hex
        self._sequence = 0

    @property
    def batch_id(self) -> str:
        """The UUID identifying this factory's batch of events."""
        return self._batch_id

    def create(
        self,
        size: EventSize = EventSize.MEDIUM,
        *,
        extra_fields: dict | None = None,
    ) -> VerifiableEvent:
        """Create a single verifiable event.

        Args:
            size: Target payload size category.
            extra_fields: Additional top-level fields merged into the ECS
                payload before hashing.

        Returns:
            A ``VerifiableEvent`` containing the JSON payload and its
            content hash for later verification.
        """
        self._sequence += 1
        sequence_id = self._sequence

        payload = self._build_ecs_payload(size, extra_fields)

        # Compute hash over the canonical payload (without test metadata).
        canonical = json.dumps(payload, sort_keys=True).encode()
        content_hash = hashlib.sha256(canonical).hexdigest()

        # Embed test metadata for downstream verification.
        payload['_test'] = {
            'sequence_id': sequence_id,
            'batch_id': self._batch_id,
            'content_hash': content_hash,
            'size_category': size.value,
        }

        raw_json = json.dumps(payload, sort_keys=True)

        return VerifiableEvent(
            sequence_id=sequence_id,
            batch_id=self._batch_id,
            content_hash=content_hash,
            raw_json=raw_json,
        )

    def create_batch(
        self,
        count: int,
        size: EventSize = EventSize.MEDIUM,
    ) -> list[VerifiableEvent]:
        """Create a batch of verifiable events.

        Args:
            count: Number of events to generate.
            size: Target payload size category applied to all events.

        Returns:
            A list of ``VerifiableEvent`` instances sharing this factory's
            batch ID, with contiguous sequence IDs.
        """
        return [self.create(size) for _ in range(count)]

    def _build_ecs_payload(
        self,
        size: EventSize,
        extra_fields: dict | None,
    ) -> dict:
        """Build a realistic ECS-compliant event payload.

        The structure mirrors real Elastic Common Schema documents as used
        by Eventum content packs (filebeat-style agents, standard field
        hierarchy).
        """
        now = datetime.now(UTC)
        hostname = random.choice(_HOSTNAMES)
        agent_id = uuid4().hex
        agent_type = random.choice(_AGENT_TYPES)

        payload: dict = {
            '@timestamp': now.isoformat(),
            'agent': {
                'ephemeral_id': uuid4().hex,
                'id': agent_id,
                'name': hostname,
                'type': agent_type,
                'version': '8.17.0',
            },
            'ecs': {
                'version': '8.17.0',
            },
            'event': {
                'category': random.choice(_EVENT_CATEGORIES),
                'created': now.isoformat(),
                'dataset': 'eventum.test',
                'kind': random.choice(_EVENT_KINDS),
                'module': 'eventum',
                'original': '',
            },
            'host': {
                'architecture': 'x86_64',
                'hostname': hostname,
                'name': hostname,
                'os': {
                    'family': 'linux',
                    'kernel': '6.6.87-generic',
                    'name': 'Ubuntu',
                    'platform': 'ubuntu',
                    'version': '24.04',
                },
            },
            'message': self._generate_message(size),
            'source': {
                'address': random.choice(_SOURCE_IPS),
            },
            'tags': ['eventum', 'test', f'size:{size.value}'],
        }

        if extra_fields:
            payload.update(extra_fields)

        return payload

    def _generate_message(self, size: EventSize) -> str:
        """Generate a realistic log message of the appropriate size.

        For SMALL events, produces a single log line. For larger sizes,
        concatenates multiple varied log lines separated by newlines until
        the target byte count is reached, simulating multi-line log output
        or verbose payloads.
        """
        target_bytes = _MESSAGE_TARGET_BYTES[size]

        if size is EventSize.SMALL:
            return self._single_log_line()

        lines: list[str] = []
        current_bytes = 0

        while current_bytes < target_bytes:
            line = self._single_log_line()
            lines.append(line)
            # +1 for the newline separator
            current_bytes += len(line.encode()) + 1

        return '\n'.join(lines)

    @staticmethod
    def _single_log_line() -> str:
        """Generate a single realistic log line with randomized fields."""
        prefix = random.choice(_LOG_PREFIXES)
        component = random.choice(_LOG_COMPONENTS)
        template = random.choice(_LOG_MESSAGES)

        message = template.format(
            ip=random.choice(_SOURCE_IPS),
            port=random.randint(1024, 65535),
            duration=random.randint(1, 9999),
            status=random.choice(
                [200, 201, 204, 301, 400, 401, 403, 404, 500, 502, 503]
            ),
            user=f'user-{random.randint(1000, 9999)}',
            method=random.choice(
                ['password', 'api_key', 'oauth2', 'saml', 'certificate']
            ),
            key=f'cache:{"".join(random.choices(string.ascii_lowercase, k=8))}',
            rows=random.randint(0, 100_000),
            count=random.randint(1, 10_000),
            window=random.choice([1, 5, 10, 30, 60]),
            domain=random.choice(
                ['api.example.com', 'cdn.internal.net', 'db.prod.local']
            ),
            days=random.randint(1, 365),
            task_id=uuid4().hex[:12],
            timestamp=datetime.now(UTC).isoformat(),
            attempt=random.randint(1, 3),
            op_id=uuid4().hex[:8],
            error=random.choice(
                ['timeout', 'connection_reset', 'dns_failure', 'tls_error']
            ),
            bytes=random.randint(64, 1_048_576),
            session_id=uuid4().hex[:16],
        )

        return f'[{prefix}] [{component}] {message}'
