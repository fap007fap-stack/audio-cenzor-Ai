"""Lokalna transkrypcja z czasami słów: faster-whisper."""
from pathlib import Path
from detectors import Token


def load_model(size: str):
    from faster_whisper import WhisperModel
    if size not in {"tiny", "base", "small"}:
        raise ValueError("Nieznany model mowy.")
    return WhisperModel(size, device="cpu", compute_type="int8", cpu_threads=2)


def transcribe(wav_path: Path, model) -> list[Token]:
    segments, _ = model.transcribe(str(wav_path), language="pl", word_timestamps=True,
                                   beam_size=3, vad_filter=True, condition_on_previous_text=False)
    tokens: list[Token] = []
    for segment in segments:
        if not segment.words:
            # W przypadku braku znaczników słów: jeden fragment do kontroli ręcznej.
            tokens.append(Token(segment.text.strip(), float(segment.start), float(segment.end)))
            continue
        for word in segment.words:
            if word.start is not None and word.end is not None and word.word.strip():
                tokens.append(Token(word.word.strip(), float(word.start), float(word.end)))
    return tokens
