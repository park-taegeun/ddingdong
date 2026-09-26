"""합성 wav 로 보드 배경 조각내기 규칙을 검증한다(실데이터 무관, ffmpeg 불요).

  env -u DDINGDONG_DATA_ROOT python -m ml.curation.tests.test_slice_boardbg
"""

from __future__ import annotations

import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path

from ...pipeline.config import SAMPLE_RATE, source_key
from .. import slice_boardbg as sb
from ..slice_negatives import REPO_ROOT
from .test_slice_direct import PARAMS, POST_N, digests, read, samples, write

UNIT = "bg1"
# stem → samples(...) 인자. 기대 = (status, onset_ms, out_rel_paths)
FIXTURES = {
    "direct_knock_bg1_01": dict(n=POST_N),                    # 조용한 5.12초 → 1조각 @0
    "direct_knock_bg1_02": dict(n=POST_N, onset=2.0),         # 중간에 소리
    "direct_knock_bg1_03": dict(n=POST_N, glitch=1.0),        # 고립 1샘플 32767
    "direct_knock_bg1_04": dict(n=32_768),                    # pre 길이 2.048초
    "direct_doorbell_bg1_06": dict(n=7 * SAMPLE_RATE),        # 7초 → 2조각, 잔여 1초 버림
}
EXPECTED = {
    "direct_knock_bg1_01": ("written", "", "other/boardbg_bg1_01_0000000.wav"),
    "direct_knock_bg1_02": ("rejected_sound", "2000", ""),
    "direct_knock_bg1_03": ("rejected_clamp", "", ""),
    "direct_knock_bg1_04": ("rejected_short", "", ""),
    "direct_knock_bg1_05": ("rejected_format", "", ""),
    "direct_doorbell_bg1_06": ("written", "",
                               "other/boardbg_bg1_06_0000000.wav;other/boardbg_bg1_06_0003000.wav"),
}


def build(rec: Path, unit: str = UNIT) -> None:
    for stem, spec in FIXTURES.items():
        write(rec / "post" / f"{stem.replace(UNIT, unit)}.wav", samples(**spec))
    write(rec / "post" / f"direct_knock_{unit}_05.wav", samples(int(5.12 * 44_100)), rate=44_100)
    (rec / "pre").mkdir()
    (rec / "pre" / f"direct_knock_{unit}_01.wav").write_bytes(b"pre must not be read")


def run(rec: Path, out: Path, *extra: str, unit: str = UNIT) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return sb.main(["--recording-dir", str(rec), "--out-dir", str(out), "--unit", unit,
                        *PARAMS, *extra])


def manifest(out: Path) -> list[dict]:
    with (out / sb.MANIFEST).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class SliceBoardbgTest(unittest.TestCase):
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
        got = {s: (r["status"], r["onset_ms"], r["out_rel_paths"]) for s, r in self.rows.items()}
        self.assertEqual(got, EXPECTED)
        for r in self.rows.values():
            self.assertEqual((r["baseline_ms"], r["onset_ratio"], r["onset_floor"]),
                             ("100", "20.0", "500.0"))
            if r["status"].startswith("rejected_"):
                self.assertTrue(r["reason"], r)

    def test_clamp_and_peak_recorded(self) -> None:
        self.assertEqual((self.rows["direct_knock_bg1_03"]["clamp_count"],
                          self.rows["direct_knock_bg1_03"]["peak"]), ("1", "32767"))
        self.assertEqual((self.rows["direct_knock_bg1_01"]["clamp_count"],
                          self.rows["direct_knock_bg1_01"]["peak"]), ("0", "5"))

    def test_clips_are_original_samples(self) -> None:
        names = {str(p.relative_to(self.out)) for p in self.out.rglob("*.wav")}
        self.assertEqual(names, {p for r in self.rows.values() if r["status"] == "written"
                                 for p in r["out_rel_paths"].split(";")})
        _, src = read(self.rec / "post" / "direct_knock_bg1_01.wav")
        fmt, clip = read(self.out / "other" / "boardbg_bg1_01_0000000.wav")
        self.assertEqual((fmt, clip), ((1, 2, SAMPLE_RATE), src[:sb.CLIP_SAMPLES]))
        _, src = read(self.rec / "post" / "direct_doorbell_bg1_06.wav")
        _, clip = read(self.out / "other" / "boardbg_bg1_06_0003000.wav")
        self.assertEqual(clip, src[sb.CLIP_SAMPLES:2 * sb.CLIP_SAMPLES])

    def test_group_key_is_unit(self) -> None:
        keys = {source_key(p.stem) for p in self.out.rglob("*.wav")}
        self.assertEqual(keys, {"boardbg_bg1"})     # 테이크 2개(01 · 06)가 같은 키

    def test_short_not_padded(self) -> None:
        self.assertFalse(list(self.out.rglob("boardbg_bg1_04_*")))

    def test_mixed_unit_rejected(self) -> None:
        for extra in ("direct_knock_bg2_09", "direct_knock_BG1_09", "noise"):
            rec = self.clone(f"rec_mixed_{extra}", {"direct_knock_bg1_01": dict(n=POST_N),
                                                    extra: dict(n=POST_N)})
            out = self.root / f"mixed_{extra}"
            with self.assertRaises(SystemExit, msg=extra) as cm:
                run(rec, out)
            self.assertIn(extra, str(cm.exception))
            self.assertFalse(out.exists())

    def test_idempotent_and_append(self) -> None:
        out = self.root / "idem"
        run(self.rec, out)
        before = digests(out)
        self.assertEqual(run(self.rec, out), 0)
        self.assertEqual(digests(out), before)
        rows = manifest(out)
        self.assertEqual(len(rows), 2 * len(EXPECTED))
        self.assertEqual({r["status"] for r in rows[len(EXPECTED):] if r["out_rel_paths"]},
                         {"skipped_exists"})

    def test_conflict_keeps_existing(self) -> None:
        out = self.root / "conflict"
        run(self.rec, out)
        before = digests(out)
        rec = self.root / "rec_conflict"
        x = samples(POST_N)
        x[100] = 7
        write(rec / "post" / "direct_knock_bg1_01.wav", x)   # 같은 테이크 · 다른 PCM
        self.assertEqual(run(rec, out), 0)
        self.assertEqual(digests(out), before)
        self.assertEqual(manifest(out)[-1]["status"], "rejected_conflict")

    def test_case_conflict_keeps_existing(self) -> None:
        out = self.root / "case"
        run(self.rec, out)
        before = digests(out)
        rec = self.clone("rec_case", {"direct_knock_BG1_01": dict(n=POST_N)})
        self.assertEqual(run(rec, out, unit="BG1"), 0)
        self.assertEqual(digests(out), before)
        self.assertEqual(manifest(out)[-1]["status"], "rejected_case_conflict")

    def test_same_take_other_label_rejected(self) -> None:
        rec = self.clone("rec_dup", {"direct_knock_bg1_01": dict(n=POST_N),
                                     "direct_doorbell_bg1_01": dict(n=POST_N)})
        out = self.root / "dup"
        self.assertEqual(run(rec, out), 0)
        self.assertEqual([r["status"] for r in manifest(out)], ["rejected_name_conflict"] * 2)
        self.assertFalse(list(out.rglob("*.wav")))

    def test_dry_run_writes_nothing(self) -> None:
        out = self.root / "dry"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(sb.main(["--recording-dir", str(self.rec), "--out-dir", str(out),
                                      "--unit", UNIT, *PARAMS, "--dry-run"]), 0)
        self.assertFalse(out.exists())
        self.assertIn("planned: 2", buf.getvalue())
        self.assertIn("| direct_knock_bg1_02.wav | rejected_sound |", buf.getvalue())

    def test_out_dir_guards(self) -> None:
        for bad in (REPO_ROOT / "ml" / "nc_should_not_exist",
                    self.root / "ds" / "01_clips" / "x",
                    self.rec / "clips"):
            with self.assertRaises(SystemExit, msg=str(bad)):
                run(self.rec, bad, "--dry-run")
            self.assertFalse(bad.exists())

    def test_unit_format(self) -> None:
        for bad in ("bg_1", "", "bg-1"):
            with self.assertRaises(SystemExit, msg=bad):
                run(self.rec, self.root / "u", "--dry-run", unit=bad)
        self.assertFalse((self.root / "u").exists())

    def test_required_args(self) -> None:
        full = ["--recording-dir", str(self.rec), "--out-dir", str(self.root / "y"),
                "--unit", UNIT, *PARAMS]
        for i in range(0, len(full), 2):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                sb.main(full[:i] + full[i + 2:])
        self.assertFalse((self.root / "y").exists())


if __name__ == "__main__":
    unittest.main()
