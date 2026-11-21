"""Streamlit waveform-editor backend: preview, peak extraction and safe edits.

The browser audition is fast; the authoritative sample-based export is FFmpeg.
No sound data or PII is written to source control.
"""
from __future__ import annotations

import base64
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

MAX_REGIONS = 250


def _ffmpeg(args: list[str]) -> bytes:
    result = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', *args],
                            capture_output=True, check=False, timeout=240)
    if result.returncode != 0:
        raise RuntimeError('FFmpeg: nie udało się przygotować podglądu audio.')
    return result.stdout


def waveform_peaks(source: Path, bins: int = 2300) -> list[float]:
    """Lightweight mono waveform, sampled at 1 kHz to keep CPU/memory reasonable."""
    if not 300 <= bins <= 6000:
        raise ValueError('Nieprawidłowa rozdzielczość waveform.')
    data = _ffmpeg(['-i', str(source), '-map', '0:a:0', '-vn', '-ac', '1', '-ar', '1000',
                    '-f', 'f32le', 'pipe:1'])
    samples = np.frombuffer(data, dtype='<f4')
    if not samples.size:
        raise ValueError('W pliku nie znaleziono próbek audio.')
    # Each output sample represents an evenly distributed non-overlapping slice.
    edges = np.linspace(0, len(samples), min(bins, len(samples)) + 1, dtype=np.int64)
    abs_samples = np.abs(samples)
    peaks = np.empty(len(edges)-1, dtype=np.float32)
    for i in range(len(peaks)):
        peaks[i] = float(np.max(abs_samples[edges[i]:max(edges[i]+1, edges[i+1])]))
    ref = max(float(np.quantile(peaks, 0.98)), 0.03)
    return np.clip(peaks / (ref * 1.2), 0.015, 1).round(3).tolist()


def browser_preview(source: Path, max_bytes: int = 25_000_000) -> str:
    """Mono 32k MP3 preview only, for client audition; original used for export."""
    data = _ffmpeg(['-i', str(source), '-map', '0:a:0', '-vn', '-ac', '1', '-ar', '24000',
                    '-c:a', 'libmp3lame', '-b:a', '32k', '-f', 'mp3', 'pipe:1'])
    if not data or len(data) > max_bytes:
        raise ValueError('Nagranie jest za długie do podglądu przeglądarkowego (25 MB). '
                         'Zrób krótszy plik; standardowy eksport nadal działa.')
    return 'data:audio/mpeg;base64,' + base64.b64encode(data).decode('ascii')


def valid_timeline_rows(payload: Any, previous: list[dict], duration: float,
                        revision: int) -> list[dict]:
    """Validate all values from untrusted browser component; never trust its metadata."""
    if not isinstance(payload, dict) or payload.get('action') != 'save':
        raise ValueError('Nieprawidłowe żądanie edytora.')
    if payload.get('revision') != revision:
        raise ValueError('Widok edytora jest nieaktualny. Odśwież stronę przed zapisem.')
    incoming = payload.get('rows')
    if not isinstance(incoming, list) or len(incoming) > MAX_REGIONS:
        raise ValueError('Przekroczono limit zaznaczeń.')
    baseline = {int(r['ID']): r for r in previous}
    output: list[dict] = []
    used: set[int] = set()
    for r in incoming:
        if not isinstance(r, dict):
            raise ValueError('Nieprawidłowy wiersz edycji.')
        rid_raw = r.get('ID')
        if type(rid_raw) is not int or rid_raw <= 0 or rid_raw in used:
            raise ValueError('Niepoprawny lub powtórzony identyfikator zaznaczenia.')
        rid = rid_raw
        used.add(rid)
        start, end, silence = float(r.get('start')), float(r.get('end')), float(r.get('silence', 0))
        if not all(math.isfinite(v) for v in (start, end, silence)):
            raise ValueError('Czasy muszą być skończonymi liczbami.')
        if not (0 <= start < end <= duration + 0.02 and 0 <= silence <= 30):
            raise ValueError(f'Zakres #{rid} wykracza poza nagranie lub cisza jest za długa.')
        action = r.get('action_type')
        if action not in ('Wytnij', 'Wstaw ciszę'):
            raise ValueError('Nieobsługiwana metoda montażu.')
        active = r.get('enabled')
        if type(active) is not bool:
            raise ValueError('Zaznaczenie musi być aktywne lub wyłączone.')
        if rid in baseline:
            original = dict(baseline[rid])
        else:
            # Browser can add new regions. Do not accept its label or source metadata.
            original = {'ID': rid, 'Kategoria': 'Ręczne', 'Wykryty fragment': 'Ręczna korekta',
                        'Źródło': 'Użytkownik', 'Pewność': 1.0}
        original.update({'Zastosuj': active, 'Od (s)': round(start, 3),
                         'Do (s)': round(min(end, duration), 3), 'Metoda': action,
                         'Cisza (s)': round(silence, 2)})
        output.append(original)
    return sorted(output, key=lambda r: (r['Od (s)'], r['ID']))
