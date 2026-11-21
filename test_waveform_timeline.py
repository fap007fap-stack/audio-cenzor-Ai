"""Regression tests for waveform assembly, multi-region validation and export."""
from __future__ import annotations
import base64
import subprocess
import tempfile
import unittest
from pathlib import Path

from audio_engine import Edit, export_audio, probe_duration
from timeline_editor import browser_preview, valid_timeline_rows, waveform_peaks

BASE = [{'ID': 4, 'Zastosuj': True, 'Od (s)': 2.0, 'Do (s)': 2.8,
         'Kategoria': 'Imiona i nazwiska', 'Wykryty fragment': 'Fikcyjne dane',
         'Metoda': 'Wytnij', 'Cisza (s)': 0.0, 'Źródło': 'AI', 'Pewność': 0.6}]


class WaveformEditing(unittest.TestCase):
    def make_payload(self, rows=None):
        if rows is None:
            rows = [{'ID': 4, 'start': 2.15, 'end': 3.0,
                     'action_type': 'Wytnij', 'silence': 0, 'enabled': True},
                    {'ID': 9, 'start': 5.0, 'end': 6.0,
                     'action_type': 'Wstaw ciszę', 'silence': 1.45, 'enabled': True}]
        return {'action': 'save', 'revision': 5, 'rows': rows}

    def test_saves_all_regions_at_once(self):
        output = valid_timeline_rows(self.make_payload(), BASE, 12, revision=5)
        self.assertEqual(len(output), 2)
        self.assertEqual(output[0]['Od (s)'], 2.15)
        self.assertEqual(output[0]['Źródło'], 'AI')
        self.assertEqual(output[1]['Kategoria'], 'Ręczne')
        self.assertEqual(output[1]['Cisza (s)'], 1.45)

    def test_can_disable_and_remove_old_region(self):
        payload = self.make_payload([{'ID': 9, 'start': 3, 'end': 4,
                                      'action_type': 'Wytnij', 'silence': 0,
                                      'enabled': False}])
        result = valid_timeline_rows(payload, BASE, 12, revision=5)
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]['Zastosuj'])

    def test_stale_revisions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'nieaktualny'):
            valid_timeline_rows(self.make_payload(), BASE, 12, revision=6)

    def test_rejects_duplicate_ids(self):
        row = self.make_payload()['rows'][0]
        with self.assertRaisesRegex(ValueError, 'identyfikator'):
            valid_timeline_rows(self.make_payload([row, row]), BASE, 12, revision=5)

    def test_rejects_negative_or_out_of_bounds(self):
        for start, end in [(-.01, 1), (8, 12.5), (7, 7)]:
            row = {**self.make_payload()['rows'][0], 'start': start, 'end': end}
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    valid_timeline_rows(self.make_payload([row]), BASE, 12, revision=5)

    def test_rejects_bad_silence_or_action(self):
        for silence, action in [(30.01, 'Wstaw ciszę'), (1, 'Usuń wszystko')]:
            row = {**self.make_payload()['rows'][0], 'silence': silence, 'action_type': action}
            with self.assertRaises(ValueError):
                valid_timeline_rows(self.make_payload([row]), BASE, 12, revision=5)

    def test_rejects_bad_bool(self):
        row = {**self.make_payload()['rows'][0], 'enabled': 'true'}
        with self.assertRaisesRegex(ValueError, 'aktywne'):
            valid_timeline_rows(self.make_payload([row]), BASE, 12, revision=5)

    def test_waveform_and_preview_are_real_audio(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'test.wav'
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                            '-f', 'lavfi', '-i', 'sine=frequency=310:duration=7',
                            '-ar', '48000', str(src)], check=True)
            peaks = waveform_peaks(src, bins=900)
            self.assertEqual(len(peaks), 900)
            self.assertGreater(max(peaks), .35)
            self.assertTrue(all(0 <= p <= 1 for p in peaks))
            uri = browser_preview(src)
            self.assertTrue(uri.startswith('data:audio/mpeg;base64,'))
            self.assertGreater(len(base64.b64decode(uri.split(',', 1)[1])), 5000)

    def test_export_after_batch_update(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'input.wav'
            dest = Path(td) / 'output.wav'
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=10',
                            str(src)], check=True)
            rows = valid_timeline_rows(self.make_payload(), BASE, 10, 5)
            edits = [Edit(r['Od (s)'], r['Do (s)'], r['Metoda'], r['Cisza (s)'])
                     for r in rows if r['Zastosuj']]
            expected = export_audio(src, dest, edits, 10, padding=0)
            self.assertTrue(dest.exists())
            self.assertAlmostEqual(expected, 10 - .85 - 1.0 + 1.45, delta=.02)
            self.assertAlmostEqual(probe_duration(dest), expected, delta=.1)


if __name__ == '__main__':
    unittest.main()
