"""Regression test for the PyAV 19 / faster-whisper metadata_errors incompatibility."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import wave


class AudioDecoderCompatibilityTests(unittest.TestCase):
    def test_requirements_restrict_pyav_to_compatible_major(self):
        req = (Path(__file__).parent / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("av==18.1.0", req)

    @unittest.skipUnless(importlib.util.find_spec("faster_whisper") and importlib.util.find_spec("av"),
                         "PyAV i faster-whisper niedostępne w środowisku testowym")
    def test_actual_wav_decode_with_faster_whisper(self):
        # Exercises decode_audio() itself; no model weights or network access required.
        from faster_whisper.audio import decode_audio
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.wav"
            with wave.open(str(path), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(16000)
                stream.writeframes(struct.pack("<" + "h" * 1600, *([0] * 1600)))
            audio = decode_audio(str(path), sampling_rate=16000)
            self.assertEqual(audio.shape, (1600,))
