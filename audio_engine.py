"""FFprobe/FFmpeg: strumieniowe, fizyczne usuwanie lub zastępowanie fragmentów ciszą."""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Edit:
    start: float
    end: float
    action: str = "Wytnij"
    silence: float = 0.5


@dataclass(frozen=True)
class Part:
    kind: str  # keep / silence
    start: float = 0.0
    end: float = 0.0
    duration: float = 0.0


def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, check=True,
                              timeout=30 if args[0] == "ffprobe" else 900)
    except FileNotFoundError as exc:
        raise RuntimeError("Brak FFmpeg/ffprobe. Zainstaluj ffmpeg (na chmurze: packages.txt).") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Przekroczono limit czasu pracy FFmpeg/FFprobe. Podziel plik na krótsze części.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError((exc.stderr or exc.stdout or "Błąd FFmpeg")[-2000:]) from exc


def probe_duration(source: Path) -> float:
    info = json.loads(_run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(source)]).stdout)
    streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if not streams:
        raise ValueError("Nie znaleziono ścieżki dźwiękowej w pliku.")
    duration = info.get("format", {}).get("duration") or streams[0].get("duration")
    if duration is None or float(duration) <= 0:
        raise ValueError("Nie udało się odczytać długości nagrania.")
    return float(duration)


def extract_audio(source: Path, destination: Path, enhance: bool = False) -> None:
    """WAV 16 kHz mono, opcjonalne łagodne oczyszczenie tylko do ASR.

    Nigdy nie modyfikujemy oryginału, z którego powstaje eksport końcowy.
    Wstępne filtrowanie może pogorszyć niektóre nagrania; użytkownik może
    je wyłączyć. Domyślny tor bez filtrów pozostaje bezstratny względem treści.
    """
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-map", "0:a:0", "-vn"]
    if enhance:
        command.extend(["-af", "highpass=f=75,lowpass=f=7500,loudnorm=I=-19:TP=-2:LRA=11"])
    command.extend(["-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(destination)])
    _run(command)


def normalize_edits(edits: Iterable[Edit], duration: float, padding: float = 0) -> list[Edit]:
    """Walidacja, margines czasowy i scalanie nakładających się fragmentów.

    Konflikt działań w obrębie nakładających się przedziałów: 'Wytnij' ma
    pierwszeństwo, żeby usuwany dźwięk nigdy przypadkowo nie pozostał.
    """
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Niepoprawna długość nagrania.")
    if not math.isfinite(padding) or not (0 <= padding <= 2):
        raise ValueError("Margines cięcia musi wynosić od 0 do 2 sekund.")
    clean: list[Edit] = []
    for edit in edits:
        if edit.action not in {"Wytnij", "Wstaw ciszę"}:
            raise ValueError("Nieobsługiwany tryb edycji.")
        nums = (edit.start, edit.end, edit.silence)
        if any(not math.isfinite(float(v)) for v in nums):
            raise ValueError("Czasy edycji muszą być liczbami skończonymi.")
        if edit.start < 0 or edit.start >= duration or edit.end <= edit.start or edit.end > duration + 0.02:
            raise ValueError(f"Niepoprawny przedział {edit.start:.2f}–{edit.end:.2f} s (czas pliku: {duration:.2f} s).")
        if not (0 <= edit.silence <= 30):
            raise ValueError("Długość ciszy musi wynosić od 0 do 30 sekund.")
        s, e = max(0, float(edit.start) - padding), min(duration, float(edit.end) + padding)
        clean.append(Edit(s, e, edit.action, float(edit.silence)))
    clean.sort(key=lambda e: (e.start, e.end))
    merged: list[Edit] = []
    for e in clean:
        if merged and e.start <= merged[-1].end + 0.00001:
            last = merged[-1]
            merged[-1] = Edit(last.start, max(last.end, e.end),
                              "Wytnij" if "Wytnij" in (last.action, e.action) else "Wstaw ciszę",
                              max(last.silence, e.silence))
        else:
            merged.append(e)
    return merged


def make_timeline(edits: Iterable[Edit], duration: float, padding: float = 0) -> list[Part]:
    intervals = normalize_edits(edits, duration, padding)
    parts: list[Part] = []
    cursor = 0.0
    for e in intervals:
        if e.start > cursor + 0.00001:
            parts.append(Part(kind="keep", start=cursor, end=e.start))
        if e.action == "Wstaw ciszę" and e.silence >= 0.001:
            parts.append(Part(kind="silence", duration=e.silence))
        cursor = e.end
    if cursor < duration - 0.00001:
        parts.append(Part(kind="keep", start=cursor, end=duration))
    return parts


def result_duration(parts: list[Part]) -> float:
    return sum((p.end - p.start) if p.kind == "keep" else p.duration for p in parts)


def export_audio(source: Path, destination: Path, edits: Iterable[Edit], duration: float,
                 padding: float = 0) -> float:
    """FFmpeg filtruje oryginalny dźwięk; nie przetwarza obrazu nawet w MP4."""
    parts = make_timeline(edits, duration, padding)
    if not parts:
        raise ValueError("Edycja usunęłaby całe nagranie. Pozostaw co najmniej jeden fragment dźwięku lub ciszy.")
    keep_count = sum(p.kind == "keep" for p in parts)
    chains: list[str] = []
    if keep_count:
        input_labels = [f"src{i}" for i in range(keep_count)]
        base = "[0:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono"
        if keep_count == 1:
            chains.append(f"{base}[{input_labels[0]}]")
        else:
            splits = "".join(f"[{label}]" for label in input_labels)
            chains.append(f"{base},asplit={keep_count}{splits}")
    output_labels: list[str] = []
    keep_index = 0
    for i, p in enumerate(parts):
        label = f"chunk{i}"
        output_labels.append(label)
        if p.kind == "keep":
            chains.append(f"[src{keep_index}]atrim=start={p.start:.6f}:end={p.end:.6f},asetpts=PTS-STARTPTS[{label}]")
            keep_index += 1
        else:
            chains.append(f"anullsrc=r=48000:cl=mono,atrim=duration={p.duration:.6f},asetpts=PTS-STARTPTS[{label}]")
    joined = "".join(f"[{x}]" for x in output_labels)
    if len(parts) == 1:
        chains.append(f"{joined}anull[out]")
    else:
        chains.append(f"{joined}concat=n={len(parts)}:v=0:a=1[out]")
    suffix = destination.suffix.lower()
    encoding = {
        ".mp3": ["-c:a", "libmp3lame", "-b:a", "160k"],
        ".m4a": ["-c:a", "aac", "-b:a", "160k"],
        ".mp4": ["-c:a", "aac", "-b:a", "160k"],
        ".wav": ["-c:a", "pcm_s16le"],
    }
    if suffix not in encoding:
        raise ValueError("Dozwolone formaty wyjściowe: MP3, M4A, MP4 (sam dźwięk), WAV.")
    filter_path = destination.parent / f"{destination.stem}.filters.txt"
    try:
        filter_path.write_text(";\n".join(chains), encoding="utf-8")
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
              "-filter_complex_script", str(filter_path), "-map", "[out]", "-vn", *encoding[suffix], str(destination)])
    finally:
        filter_path.unlink(missing_ok=True)
    expected = result_duration(parts)
    if not destination.is_file() or destination.stat().st_size <= 32:
        raise RuntimeError("FFmpeg nie wygenerował poprawnego pliku wyjściowego.")
    measured = probe_duration(destination)
    if abs(measured - expected) > 0.35:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Czas wynikowy nie zgadza się z planem ({measured:.2f} s zamiast {expected:.2f} s).")
    return expected


def export_excerpt(source: Path, destination: Path, start: float, end: float, duration: float) -> None:
    """Podgląd tylko określonego odcinka, umożliwia sprawdzenie precyzji znaczników czasu."""
    if not all(math.isfinite(x) for x in (start, end, duration)) or start < 0 or end <= start or end > duration + 0.05:
        raise ValueError('Nieprawidłowy zakres odsłuchu.')
    if end - start > 45:
        raise ValueError('Podgląd może mieć maksymalnie 45 sekund.')
    _run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{start:.6f}', '-i',
          str(source), '-map', '0:a:0', '-vn', '-t', f'{end-start:.6f}', '-c:a',
          'libmp3lame', '-b:a', '128k', str(destination)])


def audio_info(source: Path) -> dict:
    """Zwraca podstawowe informacje o pliku (bez ujawniania metadanych użytkownika)."""
    raw = json.loads(_run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(source)]).stdout)
    audio = next((s for s in raw.get('streams', []) if s.get('codec_type') == 'audio'), None)
    if audio is None:
        raise ValueError('Plik nie zawiera ścieżki dźwiękowej.')
    duration = raw.get('format', {}).get('duration') or audio.get('duration')
    if duration is None or not math.isfinite(float(duration)) or float(duration) <= 0:
        raise ValueError('Nie udało się ustalić długości nagrania.')
    if float(duration) > 7200:
        raise ValueError('Na razie obsługujemy nagrania maksymalnie 120-minutowe.')
    return {'duration': float(duration), 'codec': audio.get('codec_name', 'nieznany'),
            'sample_rate': int(audio.get('sample_rate') or 0),
            'channels': int(audio.get('channels') or 1),
            'has_video': any(s.get('codec_type') == 'video' for s in raw.get('streams', []))}
