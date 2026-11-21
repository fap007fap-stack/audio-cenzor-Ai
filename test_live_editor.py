"""Live editor seam auditing against real FFmpeg exports."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from audio_engine import Edit, export_seam_preview, probe_duration, seam_preview_plan


class PreviewPlanning(unittest.TestCase):
    def test_cut_uses_same_margin_as_final_export(self):
        effective, regions, expected = seam_preview_plan(Edit(5, 7), 20, .1, 2)
        self.assertAlmostEqual(effective.start, 4.9)
        self.assertAlmostEqual(effective.end, 7.1)
        self.assertEqual(len(regions), 2)
        self.assertAlmostEqual(expected, 4)

    def test_silence_length_is_added_exactly(self):
        effective, regions, expected = seam_preview_plan(
            Edit(5, 7, 'Wstaw ciszę', 3.25), 20, 0, 1.5)
        self.assertAlmostEqual(expected, 6.25)

    def test_start_boundary_has_only_after_context(self):
        _, regions, expected = seam_preview_plan(Edit(0, 2), 10, .2, 3)
        self.assertEqual(regions, [(2.2, 5.2)])
        self.assertAlmostEqual(expected, 3)

    def test_end_boundary_has_only_before_context(self):
        _, regions, expected = seam_preview_plan(Edit(8, 10), 10, 0, 2)
        self.assertEqual(regions, [(6.0, 8.0)])
        self.assertAlmostEqual(expected, 2)

    def test_all_silence_works_even_without_context(self):
        _, regions, expected = seam_preview_plan(Edit(0, 10, 'Wstaw ciszę', 2.5), 10, 0, 2)
        self.assertEqual(regions, [])
        self.assertAlmostEqual(expected, 2.5)

    def test_rejects_invalid_context(self):
        with self.assertRaises(ValueError):
            seam_preview_plan(Edit(1, 2), 8, context=-1)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Requires FFmpeg')
class RealSeamExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.source = self.folder / 'speech_mock.m4a'
        subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=6:sample_rate=48000',
            '-c:a', 'aac', str(self.source)
        ], check=True)
        self.duration = probe_duration(self.source)

    def tearDown(self):
        self.tmp.cleanup()

    def test_cut_preview_has_two_ends(self):
        out = self.folder / 'cut.mp3'
        expected = export_seam_preview(self.source, out, Edit(2, 4), self.duration, .1, 1.0)
        self.assertAlmostEqual(expected, 2, places=3)
        self.assertAlmostEqual(probe_duration(out), expected, delta=.12)

    def test_silence_preview_contains_real_silence(self):
        out = self.folder / 'silent.mp3'
        expected = export_seam_preview(self.source, out,
                                       Edit(2, 4, 'Wstaw ciszę', 1.5),
                                       self.duration, .1, 1.0)
        self.assertAlmostEqual(expected, 3.5, places=2)
        self.assertAlmostEqual(probe_duration(out), expected, delta=.12)
        # Decode a 0.5s window at the center of the added silence, ensuring
        # the MP3 isn't just a muted player or a fake clip.
        raw = subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-ss', '1.5', '-t', '0.3', '-i', str(out), '-f', 'f32le',
            '-ac', '1', '-ar', '48000', '-'
        ], capture_output=True, check=True).stdout
        import array
        samples = array.array('f')
        samples.frombytes(raw)
        self.assertGreater(len(samples), 100)
        self.assertLess(max(abs(x) for x in samples), 0.0006)

    def test_beginning_and_end_work(self):
        cases = [Edit(0, 2), Edit(4, self.duration),
                 Edit(0, self.duration, 'Wstaw ciszę', 1.0)]
        for idx, edit in enumerate(cases):
            with self.subTest(idx=idx):
                out = self.folder / f'edge{idx}.mp3'
                length = export_seam_preview(self.source, out, edit, self.duration, .0, 1)
                self.assertAlmostEqual(probe_duration(out), length, delta=.12)

    def test_fully_removed_audio_does_not_fake_preview(self):
        with self.assertRaises(ValueError):
            export_seam_preview(self.source, self.folder / 'empty.mp3',
                                Edit(0, self.duration), self.duration, 0, 2)


if __name__ == '__main__':
    unittest.main()
