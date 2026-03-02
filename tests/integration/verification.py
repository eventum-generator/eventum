"""Event verification for integration tests.

Parses consumed events, validates content hashes, checks sequencing,
and reports mismatches, duplicates, and corruption.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class VerificationResult:
    """Aggregated result of verifying consumed events against expectations."""

    total_received: int = 0
    total_expected: int = 0
    hash_mismatches: int = 0
    duplicates: int = 0
    missing_sequence_ids: list[int] = field(default_factory=list)
    out_of_order_count: int = 0
    duplicate_sequence_ids: list[int] = field(default_factory=list)
    corrupted_events: list[dict] = field(default_factory=list)

    @property
    def is_perfect(self) -> bool:
        """Return ``True`` when every check passes with zero anomalies."""
        return (
            self.total_received == self.total_expected
            and self.hash_mismatches == 0
            and self.duplicates == 0
            and len(self.missing_sequence_ids) == 0
            and self.out_of_order_count == 0
            and len(self.duplicate_sequence_ids) == 0
            and len(self.corrupted_events) == 0
        )

    def summary(self) -> str:
        """Return a human-readable multi-line summary."""
        lines = [
            f'received={self.total_received} expected={self.total_expected}',
            f'hash_mismatches={self.hash_mismatches}',
            f'duplicates={self.duplicates}',
            f'missing_sequence_ids={len(self.missing_sequence_ids)}',
            f'out_of_order={self.out_of_order_count}',
            f'duplicate_sequence_ids={len(self.duplicate_sequence_ids)}',
            f'corrupted_events={len(self.corrupted_events)}',
            f'is_perfect={self.is_perfect}',
        ]
        return '\n'.join(lines)


def _compute_content_hash(payload: dict) -> str:
    """Compute SHA-256 hex digest of the payload without the ``_test`` field."""
    clean = {k: v for k, v in payload.items() if k != '_test'}
    serialized = json.dumps(clean, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


class EventVerifier:
    """Verify consumed events against expected batch metadata.

    Each consumed event is expected to be a JSON string containing a
    ``_test`` field with the following structure::

        {
            "_test": {
                "batch_id": "<uuid>",
                "sequence_id": <int>,
                "content_hash": "<sha256-hex>"
            },
            ...  # actual event payload
        }

    Parameters
    ----------
    expected_batch_id:
        Only events whose ``_test.batch_id`` matches are considered.
    expected_count:
        The number of events expected (sequence_ids ``1..expected_count``).
    """

    def __init__(self, expected_batch_id: str, expected_count: int) -> None:
        self._expected_batch_id = expected_batch_id
        self._expected_count = expected_count

    def verify(
        self,
        consumed_events: list[str],
        *,
        check_order: bool = False,
    ) -> VerificationResult:
        """Verify a list of raw JSON strings consumed from the output.

        Parameters
        ----------
        consumed_events:
            Raw JSON strings, each representing one event.
        check_order:
            When ``True``, count how many times a sequence_id is smaller
            than its predecessor (out-of-order transitions).

        Returns
        -------
        VerificationResult
            Aggregated verification outcome.
        """
        result = VerificationResult(total_expected=self._expected_count)

        matched_events: list[dict] = []

        # Phase 1: parse and filter by batch_id
        for raw in consumed_events:
            try:
                event = json.loads(raw)
            except (json.JSONDecodeError, TypeError) as exc:
                result.corrupted_events.append(
                    {'raw': raw[:500], 'error': f'JSON parse error: {exc}'}
                )
                continue

            test_meta = event.get('_test')
            if not isinstance(test_meta, dict):
                # Not a test-instrumented event — skip silently
                continue

            if test_meta.get('batch_id') != self._expected_batch_id:
                continue

            matched_events.append(event)

        result.total_received = len(matched_events)

        # Phase 2: content-hash verification
        sequence_ids: list[int] = []

        for event in matched_events:
            test_meta = event['_test']
            expected_hash = test_meta.get('content_hash', '')

            actual_hash = _compute_content_hash(event)
            if actual_hash != expected_hash:
                result.hash_mismatches += 1
                result.corrupted_events.append(
                    {
                        'sequence_id': test_meta.get('sequence_id'),
                        'expected_hash': expected_hash,
                        'actual_hash': actual_hash,
                        'error': 'content hash mismatch',
                    }
                )

            seq_id = test_meta.get('sequence_id')
            if isinstance(seq_id, int):
                sequence_ids.append(seq_id)

        # Phase 3: duplicate detection
        id_counts = Counter(sequence_ids)
        for seq_id, count in sorted(id_counts.items()):
            if count > 1:
                result.duplicate_sequence_ids.append(seq_id)
                result.duplicates += count - 1

        # Phase 4: missing sequence_ids (expected 1..expected_count)
        expected_ids = set(range(1, self._expected_count + 1))
        received_ids = set(sequence_ids)
        result.missing_sequence_ids = sorted(expected_ids - received_ids)

        # Phase 5: ordering check
        if check_order and len(sequence_ids) > 1:
            for i in range(1, len(sequence_ids)):
                if sequence_ids[i] < sequence_ids[i - 1]:
                    result.out_of_order_count += 1

        return result
