"""Regression tests for previously missed polish PII + UI/deployment contract."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

from detectors import Token, detect_all, detect_spoken_phones, detect_name_context, CATEGORIES
from speech import ALLOWED_MODELS, transcribe

ROOT = Path(__file__).resolve().parent


def tokens(phrase: str):
    return [Token(w, i * .32, (i + 1) * .32) for i, w in enumerate(phrase.split())]


class RecognitionRegression(unittest.TestCase):
    def test_phone_commas_from_user_recording(self):
        found = detect_spoken_phones(tokens("numer telefonu to 1,2,3,4,5,6,7,8,9."))
        self.assertEqual(len(found), 1)
        self.assertIn('3,4,5', found[0].text)

    def test_phone_spaced_digit_groups(self):
        found = detect_spoken_phones(tokens("numer telefonu to 123 456 789"))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].text, '123 456 789')

    def test_phone_words(self):
        found = detect_spoken_phones(tokens("numer to pięć zero jeden dwa trzy cztery pięć sześć siedem"))
        self.assertEqual(len(found), 1)

    def test_no_false_phone_from_short_sequence(self):
        self.assertEqual(detect_spoken_phones(tokens("pięć trzy jeden")), [])

    def test_name_after_title_is_not_title_included(self):
        _, found = detect_all(tokens('Pani Alicja Testowa z klasy czwartej B'), set(CATEGORIES))
        names = [x.text for x in found if x.category == "Imiona i nazwiska"]
        self.assertIn('Alicja Testowa', names)
        self.assertNotIn('Pani Alicja', names)

    def test_single_inflected_first_name_after_preposition(self):
        candidates = detect_name_context(tokens('rozmawiałem z Janem'))
        self.assertTrue(any('Janem' in x.text for x in candidates))

    def test_address_inflected_ulica(self):
        _, found = detect_all(tokens('mieszkam na ulicę Testowej 18'), set(CATEGORIES))
        self.assertTrue(any(x.category == 'Adresy i e-maile' for x in found))

    def test_all_models_included(self):
        self.assertTrue({'small','medium','large-v3'} <= ALLOWED_MODELS)

    def test_improved_transcription_kwargs(self):
        class DummyModel:
            kwargs = None
            def transcribe(self, audio, **kwargs):
                self.kwargs = kwargs
                return iter([]), SimpleNamespace(language='pl')
        dummy = DummyModel()
        with patch('speech.wav_as_float32', return_value=np.zeros(16000, dtype=np.float32)):
            transcribe(Path('sample.wav'), dummy, preset='Dokładny', vad_filter=False)
        self.assertEqual(dummy.kwargs['beam_size'], 5)
        self.assertEqual(dummy.kwargs['language'], 'pl')
        self.assertEqual(dummy.kwargs['temperature'], 0.0)
        self.assertFalse(dummy.kwargs['vad_filter'])

    def test_dark_ui_and_no_old_api(self):
        code = (ROOT/'app.py').read_text(encoding='utf-8')
        ast.parse(code)
        self.assertNotIn('use_container_width=', code)
        self.assertIn('APP_VERSION = "1.7.2"', code)
        self.assertIn('Popraw pojedyncze słowa', code)
        theme = (ROOT/'.streamlit'/'config.toml').read_text()
        self.assertIn('base = "dark"',theme)
        self.assertIn('#080B11',theme)
        self.assertNotIn('backgroundColor = "#F6F9FC"',theme)

    def test_project_imports_flat(self):
        for f in ('app.py','detectors.py','speech.py','audio_engine.py','quality_checks.py'):
            self.assertTrue((ROOT/f).is_file())


if __name__ == '__main__': unittest.main()

class MediaPreparation(unittest.TestCase):
    @unittest.skipUnless(__import__('shutil').which('ffmpeg'), 'FFmpeg unavailable')
    def test_audio_enhancement_produces_valid_wav(self):
        import subprocess, tempfile, wave
        from audio_engine import extract_audio
        with tempfile.TemporaryDirectory() as td:
            original = Path(td)/'recording.m4a'
            dest = Path(td)/'speech.wav'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                '-f','lavfi','-i','sine=frequency=550:duration=1.6',
                '-c:a','aac',str(original)],check=True)
            extract_audio(original,dest,enhance=True)
            with wave.open(str(dest),'rb') as audio:
                self.assertEqual(audio.getnchannels(),1)
                self.assertEqual(audio.getframerate(),16000)
                self.assertGreater(audio.getnframes(),25000)
