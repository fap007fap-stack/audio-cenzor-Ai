"""Polska transkrypcja offline na serwerze z niezależnym dekoderem WAV.

Pliki wejściowe MP4/MP3/M4A/WAV itd. są najpierw zamieniane za pomocą FFmpeg
na mono PCM 16 kHz/16-bit. Do faster-whisper przekazujemy tablicę NumPy,
a NIE ścieżkę — dzięki temu omijamy dekoder PyAV i jego kwarg metadata_errors.
Nie znosi to obowiązku odsłuchania i sprawdzenia całego nagrania.
"""
from __future__ import annotations

from pathlib import Path
import wave

import numpy as np
from detectors import Token


ALLOWED_MODELS = {"tiny", "base", "small"}


def load_model(size: str):
    """Załaduj Whisper CPU-friendly, bez płatnego API."""
    if size not in ALLOWED_MODELS:
        raise ValueError("Nieobsługiwany model mowy.")
    from faster_whisper import WhisperModel
    return WhisperModel(size, device="cpu", compute_type="int8", cpu_threads=2)


def wav_as_float32(wav_path: Path) -> np.ndarray:
    """Odczytuje bez PyAV WAV 16 kHz / mono / PCM16 jako float32 [-1,1]."""
    with wave.open(str(wav_path), "rb") as stream:
        if (stream.getnchannels() != 1 or stream.getframerate() != 16000
                or stream.getsampwidth() != 2 or stream.getcomptype() != "NONE"):
            raise ValueError("Plik roboczy WAV musi być mono 16 kHz PCM16. Sprawdź FFmpeg.")
        frames = stream.readframes(stream.getnframes())
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32)
    return samples / 32768.0


def transcribe(wav_path: Path, model) -> list[Token]:
    """Transkrypcja słowo-po-słowie z czasami; bez wywołania av.open()."""
    audio = wav_as_float32(wav_path)
    if audio.size == 0:
        raise ValueError("Brak próbek dźwięku w pliku.")
    segments, _ = model.transcribe(
        audio, language="pl", word_timestamps=True, beam_size=3,
        vad_filter=True, condition_on_previous_text=False,
    )
    tokens: list[Token] = []
    for segment in segments:
        words = getattr(segment, "words", None)
        if not words:
            text = (getattr(segment, "text", "") or "").strip()
            if text:
                tokens.append(Token(text, float(segment.start), float(segment.end)))
            continue
        for word in words:
            if word.start is not None and word.end is not None and word.word.strip():
                tokens.append(Token(word.word.strip(), float(word.start), float(word.end)))
    return tokens
