"""Regresja: Whisper otrzymuje NumPy, nigdy ścieżkę obsługiwaną przez PyAV."""
from __future__ import annotations
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from speech import transcribe, wav_as_float32


class SpeechRegressionTests(unittest.TestCase):
    def make_wav(self, file: Path):
        with wave.open(str(file), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(struct.pack('<8h', 0, 100, -100, 400, -400, 0, 0, 100))

    def test_pcm_wav_as_float32(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'test.wav'
            self.make_wav(src)
            samples = wav_as_float32(src)
            self.assertEqual(samples.dtype, np.float32)
            self.assertEqual(samples.shape, (8,))
            self.assertAlmostEqual(float(samples[1]), 100 / 32768.)

    def test_transcribe_uses_numpy_not_av_open(self):
        class Model:
            def transcribe(self, audio, **kwargs):
                if not isinstance(audio, np.ndarray):
                    raise AssertionError('Whisper must receive numpy audio, not a file path')
                assert audio.dtype == np.float32
                assert kwargs['language'] == 'pl'
                word = SimpleNamespace(start=.12, end=.42, word=' Kowalski')
                segment = SimpleNamespace(words=[word], text='Kowalski', start=.1, end=.5)
                return iter([segment]), {}
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'audio.wav'
            self.make_wav(src)
            tokens = transcribe(src, Model())
            self.assertEqual(len(tokens), 1)
            self.assertEqual(tokens[0].text, 'Kowalski')
            self.assertAlmostEqual(tokens[0].start, .12)

    def test_rejects_wrong_wave_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'wrong.wav'
            with wave.open(str(src),'wb') as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b'\0'*40)
            with self.assertRaises(ValueError):
                wav_as_float32(src)

if __name__ == '__main__':
    unittest.main()
