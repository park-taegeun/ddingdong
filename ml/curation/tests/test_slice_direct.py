"""합성 wav 로 직접녹음 조각내기 규칙을 검증한다(실데이터 무관, ffmpeg 불요).

  env -u DDINGDONG_DATA_ROOT python -m ml.curation.tests.test_slice_direct
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import math
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

from ...pipeline.config import SAMPLE_RATE, source_key
from .. import slice_direct as sd
from ..slice_negatives import REPO_ROOT

POST_N = 81_920          # 수신기 post = 5.12초
LOUD = 8000
PARAMS = ("--baseline-ms", "100", "--onset-ratio", "20", "--onset-floor", "500")


def samples(n: int, onset: float | None = None, glitch: float | None = None,
            clamp_sine: bool = False, amp: int = LOUD) -> list[int]:
    """±5 잡음 위에 onset 초부터 ±amp 사각파(또는 40000 진폭 사인을 클램프한 큰 소리)."""
    x = [5 if i % 2 else -5 for i in range(n)]
    if glitch is not None:
        x[int(glitch * SAMPLE_RATE)] = 32767
    if onset is not None:
        s = int(onset * SAMPLE_RATE)
        for i in range(s, n):
            k = i - s
            x[i] = (max(-32768, min(32767, int(40000 * math.sin(2 * math.pi * 440 * k / SAMPLE_RATE))))
                    if clamp_sine else (amp if (k // 18) % 2 == 0 else -amp))
    return x


def write(path: Path, x: list[int], rate: int = SAMPLE_RATE, channels: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = array("h", [v for v in x for _ in range(channels)])
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


# stem → samples(...) 인자. 기대 = (status, onset_ms, start_ms, shifted)
FIXTURES = {
    "direct_doorbell_A_01": dict(n=POST_N, onset=1.0),
    "direct_doorbell_A_02": dict(n=POST_N, onset=3.5),                   # 늦은 onset → 당김
    "direct_doorbell_A_03": dict(n=POST_N),                              # 조용함
    "direct_knock_B_04": dict(n=POST_N, onset=1.2, glitch=0.5),          # 소리 앞 고립 클램프
    "direct_knock_B_05": dict(n=POST_N, onset=1.0, clamp_sine=True),     # 큰 소리 연속 클램프
    "direct_knock_B_123": dict(n=POST_N, onset=0.25),                    # 3자리 테이크
    "direct_fire_alarm_A_01": dict(n=POST_N, onset=1.0),
    "direct_knock_C_03": dict(n=32_768, onset=0.5),                      # pre 길이 2.048초
    "direct_knock_C": dict(n=POST_N, onset=1.0),                         # 테이크 없음
}
LATE_START = (POST_N - sd.CLIP_SAMPLES) // sd.MS                         # 2120
EXPECTED = {
    "direct_doorbell_A_01": ("written", "1000", "1000", "0"),
    "direct_doorbell_A_02": ("written", "3500", str(LATE_START), "1"),
    "direct_doorbell_A_03": ("rejected_no_onset", "", "", ""),
    "direct_knock_B_04": ("written", "1200", "1200", "0"),
    "direct_knock_B_05": ("written", "1000", "1000", "0"),
    "direct_knock_B_123": ("written", "250", "250", "0"),
    "direct_fire_alarm_A_01": ("rejected_label", "", "", ""),
    "direct_knock_C_01": ("rejected_format", "", "", ""),
    "direct_knock_C_02": ("rejected_format", "", "", ""),
    "direct_knock_C_03": ("rejected_too_short", "", "", ""),
    "direct_knock_C": ("rejected_name", "", "", ""),
}


def build(rec: Path) -> None:
    for stem, spec in FIXTURES.items():
        write(rec / "post" / f"{stem}.wav", samples(**spec))
    write(rec / "post" / "direct_knock_C_01.wav", samples(int(5.12 * 44_100)), rate=44_100)
    write(rec / "post" / "direct_knock_C_02.wav", samples(POST_N, onset=1.0), channels=2)
    (rec / "pre").mkdir()
    (rec / "pre" / "direct_doorbell_A_01.wav").write_bytes(b"pre must not be read")
    with (rec / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        fh.write("take,status\n" + "".join(f"{i},post_saved\n" for i in range(len(EXPECTED))))


def run(rec: Path, out: Path, *extra: str) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return sd.main(["--recording-dir", str(rec), "--out-dir", str(out), *PARAMS, *extra])


def manifest(out: Path) -> list[dict]:
    with (out / sd.MANIFEST).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def digests(out: Path) -> dict[str, str]:
    return {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(out.rglob("*.wav"))}


def read(path: Path) -> tuple[tuple[int, int, int], array]:
    with wave.open(str(path), "rb") as wf:
        return ((wf.getnchannels(), wf.getsampwidth(), wf.getframerate()),
                array("h", wf.readframes(wf.getnframes())))


class SliceDirectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.rec = cls.root / "rec"
        build(cls.rec)
        cls.out = cls.root / "out"
        cls.rc = run(cls.rec, cls.out)
        cls.rows = {Path(r["source_path"]).stem: r for r in manifest(cls.out)}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def clone(self, name: str, stems: dict[str, dict]) -> Path:
        rec = self.root / name
        for stem, spec in stems.items():
            write(rec / "post" / f"{stem}.wav", samples(**spec))
        return rec

    def test_statuses(self) -> None:
        self.assertEqual(self.rc, 0)
        got = {s: (r["status"], r["onset_ms"], r["start_ms"], r["shifted"])
               for s, r in self.rows.items()}
        self.assertEqual(got, EXPECTED)
        for r in self.rows.values():
            self.assertEqual(r["recording_dir"], str(self.rec.resolve()))
            if r["status"].startswith("rejected_"):
                self.assertTrue(r["reason"], r)
                self.assertEqual(r["out_rel_path"], "")

    def test_files_and_format(self) -> None:
        names = {str(p.relative_to(self.out)) for p in self.out.rglob("*.wav")}
        self.assertEqual(names, {r["out_rel_path"] for r in self.rows.values()
                                 if r["status"] == "written"})
        for path in self.out.rglob("*.wav"):
            fmt, x = read(path)
            self.assertEqual((fmt, len(x)), ((1, 2, SAMPLE_RATE), sd.CLIP_SAMPLES), path.name)
            label, unit, _ = sd.NAME_RE.match(path.stem.rsplit("_", 1)[0]).groups()
            self.assertEqual(path.parent.name, label)
            self.assertEqual(source_key(path.stem), f"direct_{label}_{unit}")   # D3 유닛 키

    def test_clip_is_original_samples(self) -> None:
        _, src = read(self.rec / "post" / "direct_doorbell_A_02.wav")
        _, clip = read(self.out / "doorbell" / f"direct_doorbell_A_02_{LATE_START:07d}.wav")
        self.assertEqual(clip, src[-sd.CLIP_SAMPLES:])        # 창이 파일 끝에서 끝난다
        _, src = read(self.rec / "post" / "direct_doorbell_A_01.wav")
        _, clip = read(self.out / "doorbell" / "direct_doorbell_A_01_0001000.wav")
        self.assertEqual(clip, src[16_000:16_000 + sd.CLIP_SAMPLES])

    def test_no_onset_reason(self) -> None:
        row = self.rows["direct_doorbell_A_03"]
        self.assertIn("임계 500", row["reason"])
        self.assertIn("최대 |x| 5", row["reason"])
        self.assertFalse(list(self.out.rglob("direct_doorbell_A_03_*")))

    def test_clamp_count(self) -> None:
        self.assertEqual(self.rows["direct_knock_B_04"]["clip_clamp_count"], "1")
        self.assertGreater(int(self.rows["direct_knock_B_05"]["clip_clamp_count"]), 100)
        self.assertEqual(self.rows["direct_doorbell_A_01"]["clip_clamp_count"], "0")

    def test_summary_and_receiver_check(self) -> None:
        text = (self.out / sd.SUMMARY).read_text(encoding="utf-8")
        self.assertIn(f"post_saved {len(EXPECTED)} ↔ post/ wav {len(EXPECTED)} — 일치", text)
        self.assertNotIn("pre must", text)

    def test_idempotent_and_append(self) -> None:
        out = self.root / "idem"
        run(self.rec, out)
        before = digests(out)
        self.assertEqual(run(self.rec, out), 0)
        self.assertEqual(digests(out), before)
        rows = manifest(out)
        self.assertEqual(len(rows), 2 * len(EXPECTED))            # append, 헤더 1회
        self.assertEqual((out / sd.MANIFEST).read_text(encoding="utf-8").count("recording_dir,"), 1)
        second = {r["status"] for r in rows[len(EXPECTED):] if r["out_rel_path"]}
        self.assertEqual(second, {"skipped_exists"})

    def test_conflict_keeps_existing(self) -> None:
        out = self.root / "conflict"
        run(self.rec, out)
        before = digests(out)
        # 다른 start(같은 테이크) · 같은 start 다른 PCM
        rec = self.clone("rec_conflict", {"direct_doorbell_A_01": dict(n=POST_N, onset=1.5),
                                          "direct_knock_B_04": dict(n=POST_N, onset=1.2, amp=9000)})
        self.assertEqual(run(rec, out), 0)
        self.assertEqual(digests(out), before)
        self.assertEqual([r["status"] for r in manifest(out)[-2:]], ["rejected_conflict"] * 2)

    def test_case_conflict_keeps_existing(self) -> None:
        out = self.root / "case"
        run(self.rec, out)
        before = digests(out)
        rec = self.clone("rec_case", {"direct_doorbell_a_01": dict(n=POST_N, onset=1.0, amp=9000)})
        self.assertEqual(run(rec, out), 0)
        self.assertEqual(digests(out), before)
        self.assertEqual(manifest(out)[-1]["status"], "rejected_case_conflict")

    def test_dry_run_writes_nothing(self) -> None:
        out = self.root / "dry"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(sd.main(["--recording-dir", str(self.rec), "--out-dir", str(out),
                                      *PARAMS, "--dry-run"]), 0)
        self.assertFalse(out.exists())
        self.assertIn("planned: 5", buf.getvalue())

    def test_out_dir_guards(self) -> None:
        for bad in (REPO_ROOT / "ml" / "nc_should_not_exist",
                    self.root / "ds" / "01_clips" / "x",
                    self.rec / "clips"):
            with self.assertRaises(SystemExit, msg=str(bad)):
                run(self.rec, bad, "--dry-run")
            self.assertFalse(bad.exists())

    def test_post_dir_required(self) -> None:
        with self.assertRaises(SystemExit):
            run(self.rec / "post", self.root / "x", "--dry-run")
        self.assertFalse((self.root / "x").exists())

    def test_required_args(self) -> None:
        full = ["--recording-dir", str(self.rec), "--out-dir", str(self.root / "y"), *PARAMS]
        for i in range(0, len(full), 2):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                sd.main(full[:i] + full[i + 2:])
        self.assertFalse((self.root / "y").exists())


if __name__ == "__main__":
    unittest.main()
