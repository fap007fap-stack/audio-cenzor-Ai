"""Regression: saved sample boundaries must be identical in the exported audio.

Uses synthetic test signals only; no customer recordings or personal information.
These tests would catch a subtle drift that a mere duration assertion would miss.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np

from audio_engine import Edit, export_audio, make_timeline, probe_duration

SR = 48000


def ffmpeg(*args: str) -> bytes:
    result = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *map(str, args)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode()[-1500:])
    return result.stdout


def decode_pcm(source: Path) -> np.ndarray:
    return np.frombuffer(ffmpeg('-i', source, '-vn', '-map', '0:a:0', '-ar', str(SR),
                               '-ac', '1', '-f', 's16le', 'pipe:1'), dtype='<i2')


class ExactSamplesTest(unittest.TestCase):
    def test_multiple_saved_cuts_and_silence_match_original_sample_positions(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            rng = np.random.default_rng(4723)
            signal = (rng.normal(0, .08, 11 * SR)).clip(-1, 1).astype('<f4')
            raw = directory/'input.raw'
            raw.write_bytes(signal.tobytes())
            wav = directory/'input.wav'
            ffmpeg('-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', raw,
                   '-c:a', 'pcm_s16le', wav)
            encodings = {'wav': wav}
            for suffix, codec in [('m4a', 'aac'), ('mp3', 'libmp3lame')]:
                encoded = directory/f'input.{suffix}'
                ffmpeg('-i', wav, '-c:a', codec, '-b:a', '160k', encoded)
                encodings[suffix] = encoded
            edits = [Edit(1.13, 2.29, 'Wytnij'),
                     Edit(4.21, 4.85, 'Wstaw ciszę', 0.91),
                     Edit(7.06, 8.01, 'Wytnij'),
                     Edit(9.21, 9.63, 'Wstaw ciszę', 0.35)]
            for ext, source in encodings.items():
                with self.subTest(input=ext):
                    plan = make_timeline(edits, probe_duration(source), padding=0.0)
                    output = directory/f'out_from_{ext}.wav'
                    export_audio(source, output, edits, probe_duration(source), padding=0.0)
                    original = decode_pcm(source)
                    rendered = decode_pcm(output)
                    cursor = 0
                    for piece in plan:
                        if piece.kind == 'keep':
                            lo, hi = round(piece.start*SR), round(piece.end*SR)
                            match = original[lo:min(hi,len(original))]
                        else:
                            match = np.zeros(round(piece.duration*SR), dtype='<i2')
                        segment = rendered[cursor:cursor+len(match)]
                        self.assertEqual(len(segment), len(match))
                        difference = np.max(np.abs(segment.astype('int32')-match.astype('int32')))
                        self.assertLessEqual(difference, 1, msg=f'{ext} {piece}: sample drift {difference}')
                        cursor += len(match)
                    self.assertLessEqual(abs(len(rendered)-cursor), 2)


    def test_mp3_and_m4a_outputs_do_not_shift_late_cuts(self):
        """Check *content position*, not just the total file duration."""
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            rng = np.random.default_rng(5150)
            (folder/'random.raw').write_bytes((rng.normal(0, .06, 12*SR).clip(-1, 1).astype('<f4')).tobytes())
            source = folder/'source.m4a'
            ffmpeg('-f','f32le','-ar',str(SR),'-ac','1','-i',folder/'random.raw',
                   '-c:a','aac','-b:a','160k',source)
            decoded_original = decode_pcm(source).astype(np.float32)
            edits = [Edit(1.37,2.11), Edit(4.18,4.96,'Wstaw ciszę',.52),
                     Edit(7.45,8.89)]
            plan = make_timeline(edits,probe_duration(source),0)
            anchors = []
            cursor=0.0
            for part in plan:
                if part.kind == 'keep':
                    if part.end - part.start > .6:
                        anchors.append((cursor+.20,part.start+.20))
                    cursor += part.end-part.start
                else:
                    cursor += part.duration
            for fmt in ('mp3','m4a'):
                with self.subTest(output=fmt):
                    exported=folder/f'export.{fmt}'
                    export_audio(source,exported,edits,probe_duration(source),0)
                    rendered=decode_pcm(exported).astype(np.float32)
                    # Correlate each late output anchor with a narrow search band
                    # in the original. An accumulated cut offset would fail.
                    for target_at, source_at in anchors:
                        win = rendered[round(target_at*SR):round((target_at+.07)*SR)]
                        a=max(0,round((source_at-.08)*SR))
                        b=min(len(decoded_original),round((source_at+.15)*SR))
                        signal=decoded_original[a:b]
                        size=1 << ((len(signal)+len(win)-2).bit_length())
                        corr=np.fft.irfft(np.fft.rfft(signal,size)*np.conj(np.fft.rfft(win,size)),size)
                        offset=(a+int(np.argmax(corr[:len(signal)-len(win)+1])))/SR-source_at
                        self.assertLess(abs(offset),.008, msg=f'{fmt}: drift {offset:.4f}s at {source_at}s')

    def test_padding_is_explicit_and_not_an_invisible_extra_cut(self):
        region = Edit(3.5, 3.95, 'Wytnij')
        self.assertEqual([(p.kind, p.start, p.end) for p in make_timeline([region], 10, 0)],
                         [('keep', 0.0, 3.5), ('keep', 3.95, 10)])
        widened = make_timeline([region], 10, .2)
        self.assertAlmostEqual(widened[0].end, 3.3)
        self.assertAlmostEqual(widened[1].start, 4.15)

    def test_editor_and_export_require_saved_state(self):
        app = (Path(__file__).parent/'app.py').read_text(encoding='utf8')
        frontend = (Path(__file__).parent/'components/waveform/index.html').read_text(encoding='utf8')
        self.assertIn("event == 'dirty'", app)
        self.assertIn("st.session_state.get('timeline_dirty')", app)
        self.assertIn("table_unsaved", app)
        self.assertIn('notifyDirty()', frontend)
        self.assertIn("action:dirty?'dirty':'clean'", frontend)
        self.assertIn("event == 'save'", app)

if __name__ == '__main__':
    unittest.main()
