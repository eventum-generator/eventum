"""Script event plugin for producing verifiable test events.

Used by scale and longevity tests to generate events through the full
Generator pipeline (Input → Event → Output). Each event carries
``_test`` metadata with a content hash for end-to-end verification.
"""

import hashlib
import json
import os
import random
import string
import threading
from datetime import UTC, datetime
from uuid import uuid4

# Global counter protected by a lock for thread safety
_counter_lock = threading.Lock()
_counter = 0

# Batch ID from environment or auto-generated
_BATCH_ID = os.environ.get('EVENTUM_TEST_BATCH_ID', uuid4().hex)

_HOSTNAMES = [
    'web-prod-01.us-east-1.internal',
    'api-prod-03.eu-west-1.internal',
    'worker-batch-07.us-west-2.internal',
]

_LOG_MESSAGES = [
    'Connection established from {ip} to port {port}',
    'Request processed in {duration}ms with status {status}',
    'Cache miss for key {key}, fetching from origin',
    'Query completed: {rows} rows affected in {duration}ms',
    'Health check passed: latency={duration}ms',
]


def produce(params: dict) -> str:
    """Produce a single verifiable ECS-compatible event.

    Parameters
    ----------
    params : dict
        Contains ``timestamp`` (datetime) and ``tags`` (tuple[str, ...]).

    Returns
    -------
    str
        JSON-serialized event with embedded ``_test`` verification metadata.
    """
    global _counter

    with _counter_lock:
        _counter += 1
        sequence_id = _counter

    timestamp = params['timestamp']
    hostname = random.choice(_HOSTNAMES)
    template = random.choice(_LOG_MESSAGES)

    message = template.format(
        ip=f'10.0.{random.randint(0, 255)}.{random.randint(1, 254)}',
        port=random.randint(1024, 65535),
        duration=random.randint(1, 9999),
        status=random.choice([200, 201, 400, 404, 500]),
        key=f"cache:{''.join(random.choices(string.ascii_lowercase, k=8))}",
        rows=random.randint(0, 100000),
    )

    payload = {
        '@timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
        'agent': {
            'id': uuid4().hex,
            'name': hostname,
            'type': 'eventum',
            'version': '2.2.0',
        },
        'ecs': {'version': '8.17.0'},
        'event': {
            'category': ['process'],
            'created': datetime.now(UTC).isoformat(),
            'dataset': 'eventum.scale_test',
            'kind': 'event',
            'module': 'eventum',
        },
        'host': {
            'hostname': hostname,
            'name': hostname,
        },
        'message': message,
        'tags': ['eventum', 'scale-test'],
    }

    # Compute hash before adding _test metadata
    canonical = json.dumps(payload, sort_keys=True).encode()
    content_hash = hashlib.sha256(canonical).hexdigest()

    payload['_test'] = {
        'sequence_id': sequence_id,
        'batch_id': _BATCH_ID,
        'content_hash': content_hash,
    }

    return json.dumps(payload, sort_keys=True)
