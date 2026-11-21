"""Pure utilities for editor verification and deterministic export reports."""
from __future__ import annotations
import hashlib
import json
from typing import Sequence
from audio_engine import Edit, normalize_edits


def overlapping_pairs(edits: Sequence[Edit], duration: float, padding: float = 0) -> int:
    """Number of overlapping pairs after padding, before normalization."""
    ranges = sorted((max(0, e.start - padding), min(duration, e.end + padding)) for e in edits)
    return sum(1 for i in range(1, len(ranges)) if ranges[i][0] < ranges[i - 1][1] - 0.00001)


def redaction_report(edits: Sequence[Edit], duration: float, padding: float, *, output_duration: float, format_name: str) -> bytes:
    """JSON report WITHOUT source snippets, transcript, or original filename."""
    clean = normalize_edits(edits, duration, padding)
    payload = {
        'version': 1,
        'duration_source_s': round(duration, 3),
        'duration_result_s_estimate': round(output_duration, 3),
        'format': format_name,
        'reviewed_by_human': 'not_verified_by_software',
        'applied_intervals': [
            {'start_s': round(e.start, 3), 'end_s': round(e.end, 3),
             'action': e.action, 'silence_s': e.silence if e.action == 'Wstaw ciszę' else 0}
            for e in clean
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')


def fingerprint(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode('utf8')).hexdigest()
