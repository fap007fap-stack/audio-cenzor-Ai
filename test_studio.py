"""Additional coverage for AI Cenzor Studio quality gates."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import wave
import struct

from audio_engine import Edit, audio_info, export_audio, export_excerpt, probe_duration
from detectors import (Token, detect_all, detect_custom_phrases, detect_spoken_phones,
                           gliner2_for_tokens)
from quality_checks import fingerprint, overlapping_pairs, redaction_report


class DetectionQuality(unittest.TestCase):
    def tokens(self, words):
        return [Token(w, i * .4, (i + 1) * .4) for i, w in enumerate(words)]

    def test_spoken_nine_digit_phone(self):
        tokens = self.tokens('mój numer to pięć zero jeden dwa trzy cztery pięć sześć siedem'.split())
        results = detect_spoken_phones(tokens)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].start, 3 * .4)
        self.assertEqual(results[0].category, 'Numery telefonów')

    def test_spoken_short_digits_not_phone(self):
        self.assertFalse(detect_spoken_phones(self.tokens('jeden dwa trzy cztery'.split())))

    def test_custom_phrase_casefold(self):
        tokens = self.tokens('rozmawiałem z janem kowalskim wczoraj'.split())
        found = detect_custom_phrases(tokens, ['Janem Kowalskim'])
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0].start, .8)

    def test_custom_phrase_metacharacters_are_literal(self):
        tokens = self.tokens(['Kontakt:', 'A.B', 'koniec'])
        found = detect_custom_phrases(tokens, ['A.B'])
        self.assertEqual(len(found), 1)

    def test_detect_all_only_requested(self):
        tokens = self.tokens(['kurwa', 'Jan', 'Kowalski'])
        _, found = detect_all(tokens, {'Imiona i nazwiska'}, [])
        self.assertFalse(any(f.category == 'Wulgaryzmy' for f in found))

    def test_model_spans_across_chunks(self):
        class FakeModel:
            def extract_entities(self, text, *args, **kwargs):
                start = text.find('Jan Kowalski')
                return {'entities': {'person': ([{'text':'Jan Kowalski','start':start,
                                                 'end':start + 12,'confidence':.9}] if start >= 0 else [])}}
        words = ['wypełniacz'] * 22 + ['Jan', 'Kowalski'] + ['wypełniacz'] * 22
        found = gliner2_for_tokens(self.tokens(words), FakeModel(), {'Imiona i nazwiska'},
                                   chunk_size=25, overlap=8)
        self.assertTrue(any(f.start <= 22*.4 and f.end >= 24*.4 for f in found))


class ReportQuality(unittest.TestCase):
    def test_report_excludes_raw_pii(self):
        data = redaction_report([Edit(2, 3, 'Wstaw ciszę', 1.25)], 10, .1,
                                output_duration=10.25, format_name='MP3')
        report = json.loads(data)
        self.assertEqual(report['applied_intervals'][0]['silence_s'], 1.25)
        self.assertNotIn('transcript', data.decode().lower())
        self.assertNotIn('filename', data.decode().lower())

    def test_overlaps(self):
        edits = [Edit(2,3),Edit(3.1,4)]
        self.assertEqual(overlapping_pairs(edits, 10, padding=.1), 1)
        self.assertEqual(overlapping_pairs(edits, 10, padding=0), 0)

    def test_fingerprint_stable(self):
        self.assertEqual(fingerprint({'b':2,'a':1}), fingerprint({'a':1,'b':2}))


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg unavailable')
class AudioIntegration(unittest.TestCase):
    def test_actual_silent_samples_and_reencoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'src.mp4'
            destination = Path(tmp)/'dest.wav'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
                            '-i','sine=frequency=440:duration=3:sample_rate=48000',
                            '-c:a','aac',str(source)], check=True)
            length = audio_info(source)['duration']
            self.assertTrue(length >= 2.99)
            result = export_audio(source, destination,
                                  [Edit(.5, 1, 'Wytnij'), Edit(1.5, 2, 'Wstaw ciszę', 1.)],
                                  length)
            self.assertAlmostEqual(result, length, delta=.05)
            self.assertAlmostEqual(probe_duration(destination), result, delta=.08)
            with wave.open(str(destination), 'rb') as stream:
                self.assertEqual(stream.getframerate(), 48000)
                stream.setpos(int(1.02 * 48000))
                samples = stream.readframes(4800)
                values = struct.unpack(f'<{len(samples)//2}h', samples)
                self.assertTrue(all(abs(x) < 2 for x in values), 'Insertion must be actual digital silence')
                stream.setpos(0)
                start_values = struct.unpack('<400h', stream.readframes(400))
                self.assertGreater(max(abs(x) for x in start_values), 10, 'Kept audio must not be muted')

    def test_excerpt(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp)/'tone.wav', Path(tmp)/'short.mp3'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
                            '-i','sine=frequency=250:duration=4','-c:a','pcm_s16le',str(src)], check=True)
            export_excerpt(src, dest, 1.0, 2.25, 4.0)
            self.assertAlmostEqual(probe_duration(dest), 1.25, delta=.06)
            with self.assertRaises(ValueError):
                export_excerpt(src, dest, 2.5, 2.0, 4)


if __name__ == '__main__':
    unittest.main()

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg unavailable')
class ExportFormatTests(unittest.TestCase):
    def test_all_output_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp)/'src.wav'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
                            '-i','sine=frequency=280:duration=2:sample_rate=48000',
                            str(src)], check=True)
            for suffix in ('.mp3', '.m4a', '.mp4', '.wav'):
                with self.subTest(format=suffix):
                    target = Path(tmp)/('clean'+suffix)
                    estimate = export_audio(src, target, [Edit(.25,.6,'Wstaw ciszę',.75)], 2)
                    self.assertTrue(target.stat().st_size > 100)
                    self.assertAlmostEqual(probe_duration(target), estimate, delta=.20)

    def test_full_replacement_with_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'src.wav', Path(tmp)/'result.wav'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
                            '-i','sine=frequency=280:duration=2:sample_rate=48000',
                            str(source)], check=True)
            length = export_audio(source, output, [Edit(0, 2, 'Wstaw ciszę', 1.4)], 2)
            self.assertAlmostEqual(length, 1.4)
            self.assertAlmostEqual(probe_duration(output), 1.4, delta=.03)
