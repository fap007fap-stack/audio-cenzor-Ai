"""Regression for real-world M4A/AAC recordings with non-contiguous PTS.

Only synthesized sine-wave audio appears in the repository. No private user
recordings, names, phone numbers, or transcripts are committed to GitHub.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np

from audio_engine import Edit, canonicalize_audio, extract_audio, export_audio, make_timeline, probe_duration, result_duration
from timeline_editor import browser_preview, waveform_peaks


def ffmpeg(*args: object):
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + list(map(str, args))
    proc = subprocess.run(command, capture_output=True, text=True, timeout=50)
    if proc.returncode:
        raise RuntimeError(proc.stderr[-1000:])


def decoded_samples(path: Path, sample_rate: int) -> int:
    result = subprocess.run(
        ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(path),
         '-map', '0:a:0', '-ac', '1', '-ar', str(sample_rate), '-f', 's16le', 'pipe:1'],
        capture_output=True, timeout=50, check=True)
    return len(result.stdout) // 2


class TimestampRepairTests(unittest.TestCase):
    def test_timestamp_skew_does_not_shrink_or_shift_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Encoder sees 5 seconds of actual PCM but AAC timestamps will
            # announce ~5.5 seconds; this reproduces a real-world failure mode.
            raw = root / 'synthetic.wav'
            broken = root / 'skewed.m4a'
            ffmpeg('-f', 'lavfi', '-i',
                   'sine=frequency=509:sample_rate=16000:duration=5',
                   '-c:a', 'pcm_s16le', raw)
            ffmpeg('-i', raw, '-af', 'asetpts=PTS*1.10',
                   '-c:a', 'aac', '-b:a', '64k', broken)
            duration = probe_duration(broken)
            self.assertGreater(duration, 5.35)
            self.assertLess(decoded_samples(broken, 16000) / 16000, duration - .20)

            canonical = root / 'timeline_48k.flac'
            actual = canonicalize_audio(broken, canonical, duration)
            self.assertAlmostEqual(actual, duration, places=2)
            self.assertLess(abs(decoded_samples(canonical, 48000)/48000 - duration), 0.005)

            # A redaction near the end would be outside the decoded raw sample
            # range if the flawed pipeline dropped presentation-time gaps.
            edits = [Edit(0.65, 1.02, 'Wytnij'),
                     Edit(2.06, 2.66, 'Wstaw ciszę', 0.81),
                     Edit(3.76, 4.30, 'Wytnij')]
            planned = result_duration(make_timeline(edits, duration))
            for fmt in ['wav', 'mp3', 'm4a']:
                with self.subTest(output=fmt):
                    dest = root / f'cleaned.{fmt}'
                    exported = export_audio(canonical, dest, edits, duration)
                    self.assertAlmostEqual(exported, planned, places=2)
                    self.assertLess(abs(probe_duration(dest) - planned), .05)

            # Transcription wav and the browser's waveform see the SAME length.
            asr = root / 'speech.wav'
            extract_audio(canonical, asr)
            self.assertLess(abs(probe_duration(asr)-duration), .02)
            peaks = waveform_peaks(canonical, bins=400)
            self.assertEqual(len(peaks), 400)
            preview = browser_preview(canonical)
            self.assertTrue(preview.startswith('data:audio/mpeg;base64,'))

    def test_original_wav_timeline_is_not_altered(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            source=p/'source.wav'
            ffmpeg('-f','lavfi','-i','sine=frequency=433:duration=2:sample_rate=48000',
                   '-c:a','pcm_s16le',source)
            canonical=p/'timeline_48k.flac'
            duration = probe_duration(source)
            canonicalize_audio(source,canonical,duration)
            self.assertLess(abs(decoded_samples(canonical,48000)/48000-duration),.002)


if __name__ == '__main__':
    unittest.main()
