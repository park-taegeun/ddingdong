"""합성 wav 로 네거티브 조각내기 규칙을 검증한다(실데이터 무관, ffmpeg 필요).

  env -u DDINGDONG_DATA_ROOT python -m ml.curation.tests.test_slice_negatives
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from ...pipeline.config import source_key
from .. import slice_negatives as sn
from ..select_negatives import CANDIDATE_FIELDS

# fsd_id → (샘플레이트, 채널, 초). None = 0바이트, "garbage" = 헤더 없는 쓰레기.
FIXTURES = {
    "101": (44_100, 2, 7.5),    # 2클립(0 · 3000), 잔여 1.5초 버림
    "102": (44_100, 1, 1.2),    # pad 1클립
    "103": (16_000, 1, 3.0),    # 정확히 3초 → 1클립, pad 없음
    "104": (44_100, 1, 12.0),   # 4조각 중 cap=2 → 0 · 9000
    "105": None,
    "106": (16_000, 1, 0.05),   # MIN_DURATION_SEC 미만
    "107": "garbage",
}
CAP = 2
EXPECTED = {"101_0000000.wav", "101_0003000.wav", "102_0000000.wav",
            "103_0000000.wav", "104_0000000.wav", "104_0009000.wav"}


def _tone(path: Path, rate: int, channels: int, seconds: float) -> None:
    frame = lambda i: struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate)))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"".join(frame(i) * channels for i in range(int(rate * seconds))))


def build(root: Path) -> tuple[Path, Path]:
    audio = root / "audio"
    audio.mkdir()
    for fid, spec in FIXTURES.items():
        path = audio / f"{fid}.wav"
        if spec is None:
            path.write_bytes(b"")
        elif spec == "garbage":
            path.write_bytes(b"not a wav at all" * 64)
        else:
            _tone(path, *spec)
    cands = root / "candidates.csv"
    with cands.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CANDIDATE_FIELDS)
        writer.writeheader()
        writer.writerows({"fsd_id": fid} for fid in FIXTURES)
    return cands, audio


def run(cands: Path, audio: Path, out: Path, *extra: str) -> int:
    argv = ["--candidates", str(cands), "--audio-root", str(audio), "--out-dir", str(out),
            "--max-clips-per-source", str(CAP), *extra]
    with contextlib.redirect_stdout(io.StringIO()):
        return sn.main(argv)


def manifest(out: Path) -> list[dict]:
    with (out / "slice_manifest.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def digests(folder: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.glob("*.wav"))}


class SliceNegativesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.cands, cls.audio = build(cls.root)
        cls.out = cls.root / "out"
        cls.rc = run(cls.cands, cls.audio, cls.out)
        cls.rows = manifest(cls.out)
        cls.clips = cls.out / sn.CLASS_DIR

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def status(self, fid: str) -> list[str]:
        return [r["status"] for r in self.rows if r["group"] == fid]

    def test_names_and_counts(self) -> None:
        self.assertEqual(self.rc, 0)
        self.assertEqual({p.name for p in self.clips.glob("*.wav")}, EXPECTED)

    def test_output_format(self) -> None:
        for path in self.clips.glob("*.wav"):
            with wave.open(str(path), "rb") as wf:
                self.assertEqual((wf.getnchannels(), wf.getsampwidth(), wf.getframerate()),
                                 (1, 2, 16_000), path.name)
                self.assertEqual(wf.getnframes(), sn.CLIP_SAMPLES, path.name)

    def test_pad_tail_is_zero(self) -> None:
        with wave.open(str(self.clips / "102_0000000.wav"), "rb") as wf:
            pcm = wf.readframes(wf.getnframes())
        samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
        self.assertTrue(any(samples[:16_000]), "앞 1초는 소리가 있어야 한다")
        self.assertFalse(any(samples[int(1.3 * 16_000):]), "1.2초 뒤는 0 이어야 한다")
        padded = {r["out_rel_path"]: r["padded"] for r in self.rows if r["out_rel_path"]}
        self.assertEqual(padded["other/102_0000000.wav"], "1")
        self.assertEqual(padded["other/103_0000000.wav"], "0")

    def test_cap_even_spacing(self) -> None:
        self.assertEqual(sn.pick_indices(4, 2), [0, 3])
        self.assertEqual(sn.pick_indices(10, 1), [0])
        self.assertEqual(sn.pick_indices(3, 5), [0, 1, 2])
        for fid in FIXTURES:
            self.assertLessEqual(self.status(fid).count("written"), CAP)
        dropped = sorted(int(r["start_ms"]) for r in self.rows if r["status"] == "dropped_cap")
        self.assertEqual(dropped, [3000, 6000])

    def test_source_key_invariant(self) -> None:
        for path in self.clips.glob("*.wav"):
            self.assertEqual(source_key(path.stem), path.stem.split("_")[0])

    def test_rejections_recorded(self) -> None:
        self.assertEqual(self.status("105"), ["rejected_empty"])
        self.assertEqual(self.status("106"), ["rejected_too_short"])
        self.assertEqual(self.status("107"), ["rejected_decode"])
        for row in self.rows:
            self.assertTrue(row["ffmpeg_version"].startswith("ffmpeg version"))

    def test_idempotent(self) -> None:
        out = self.root / "idem"
        run(self.cands, self.audio, out)
        victim = out / sn.CLASS_DIR / "101_0000000.wav"
        victim.write_bytes(b"sentinel")              # 덮어쓰면 사라진다
        before = digests(out / sn.CLASS_DIR)
        self.assertEqual(run(self.cands, self.audio, out), 0)
        self.assertEqual(digests(out / sn.CLASS_DIR), before)
        statuses = {r["status"] for r in manifest(out) if r["out_rel_path"]}
        self.assertEqual(statuses, {"skipped_exists"})

    def test_dry_run_writes_nothing(self) -> None:
        out = self.root / "dry"
        run(self.cands, self.audio, out, "--dry-run")
        self.assertFalse(out.exists())

    def test_out_dir_guards(self) -> None:
        for bad in (sn.REPO_ROOT / "ml" / "nc_should_not_exist",
                    self.root / "ds" / "01_clips" / "x"):
            with self.assertRaises(SystemExit, msg=str(bad)):
                run(self.cands, self.audio, bad, "--dry-run")
            self.assertFalse(bad.exists())

    def test_required_args(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            sn.main(["--candidates", str(self.cands), "--audio-root", str(self.audio),
                     "--out-dir", str(self.root / "x")])


if __name__ == "__main__":
    unittest.main()
