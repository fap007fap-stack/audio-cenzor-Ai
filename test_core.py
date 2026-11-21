import math
from pathlib import Path
import subprocess
import tempfile
import unittest

from audio_engine import Edit, make_timeline, normalize_edits, export_audio, probe_duration, result_duration
from detectors import Token, detect_patterns, text_with_offsets


class TimelineTests(unittest.TestCase):
    def test_cut_reduces_duration(self):
        plan = make_timeline([Edit(2, 4)], 10, padding=0)
        self.assertEqual([(p.kind, p.start, p.end) for p in plan], [("keep", 0, 2), ("keep", 4, 10)])
        self.assertAlmostEqual(result_duration(plan), 8)

    def test_silence_replaces_audio_with_exact_duration(self):
        plan = make_timeline([Edit(2, 4, "Wstaw ciszę", 1.75)], 10)
        self.assertEqual([p.kind for p in plan], ["keep", "silence", "keep"])
        self.assertAlmostEqual(result_duration(plan), 9.75)

    def test_overlap_cut_precedence(self):
        intervals = normalize_edits([Edit(2, 4, "Wstaw ciszę", 1), Edit(3, 5, "Wytnij")], 10)
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0].action, "Wytnij")
        self.assertEqual(intervals[0].end, 5)

    def test_padding(self):
        intervals = normalize_edits([Edit(2, 3)], 10, padding=0.2)
        self.assertAlmostEqual(intervals[0].start, 1.8)
        self.assertAlmostEqual(intervals[0].end, 3.2)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            make_timeline([Edit(7, 3)], 10)
        with self.assertRaises(ValueError):
            make_timeline([Edit(1, math.nan)], 10)
        with self.assertRaises(ValueError):
            make_timeline([Edit(1, 3, "Wstaw ciszę", 60)], 10)


class DetectionTests(unittest.TestCase):
    def test_detects_phone_and_profanity(self):
        words = ["Telefon", "to", "501", "234", "567", "kurwa"]
        tokens = [Token(w, i * 0.5, (i + 1) * 0.5) for i, w in enumerate(words)]
        text, found = detect_patterns(tokens, {"Numery telefonów", "Wulgaryzmy"})
        self.assertIn("501 234 567", text)
        self.assertTrue(any(f.category == "Numery telefonów" and f.start == 1.0 and f.end == 2.5 for f in found))
        self.assertTrue(any(f.category == "Wulgaryzmy" and f.start == 2.5 for f in found))

    def test_detects_name_pair(self):
        words = ["Rozmawiałem", "z", "Janem", "Kowalskim", "wczoraj"]
        tokens = [Token(w, i, i + 0.9) for i, w in enumerate(words)]
        _, found = detect_patterns(tokens, {"Imiona i nazwiska"})
        self.assertTrue(any("Janem Kowalskim" in f.text for f in found))


class FfmpegExportTests(unittest.TestCase):
    def test_export_silence_and_cut(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.m4a"
            dest = Path(tmp) / "output.wav"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                            "-i", "sine=frequency=440:duration=3:sample_rate=48000",
                            "-c:a", "aac", str(source)], check=True)
            d = probe_duration(source)
            outcome = export_audio(source, dest, [Edit(0.5, 1, "Wytnij"),
                                                  Edit(1.5, 2, "Wstaw ciszę", 1.25)], d)
            self.assertTrue(dest.exists())
            self.assertAlmostEqual(outcome, d - 0.5 - 0.5 + 1.25, places=1)
            self.assertAlmostEqual(probe_duration(dest), outcome, delta=0.08)


if __name__ == "__main__":
    unittest.main()
