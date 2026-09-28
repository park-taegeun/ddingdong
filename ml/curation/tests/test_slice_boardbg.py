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
    # 결정 2026-09-27 ①: 고립 1샘플 클램프(ToF 글리치)는 통과 — 옛 기대 rejected_clamp 에서 갱신.
    "direct_knock_bg1_03": ("written", "", "other/boardbg_bg1_03_0000000.wav"),
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
                          self.rows["direct_knock_bg1_03"]["clamp_max_run"],
                          self.rows["direct_knock_bg1_03"]["peak"]), ("1", "1", "32767"))
        self.assertEqual((self.rows["direct_knock_bg1_01"]["clamp_count"],
                          self.rows["direct_knock_bg1_01"]["clamp_max_run"],
                          self.rows["direct_knock_bg1_01"]["peak"]), ("0", "0", "5"))

    def one(self, name: str, x: list[int]) -> dict:
        """테이크 1개 폴더 → manifest 행."""
        rec, out = self.root / f"rec_{name}", self.root / f"out_{name}"
        write(rec / "post" / "direct_knock_bg1_01.wav", x)
        self.assertEqual(run(rec, out), 0)
        return manifest(out)[-1]

    def test_isolated_clamps_pass(self) -> None:          # (a) 결정 ① — 글리치 여러 개도 통과
        x = samples(POST_N)
        for t in (0.5, 1.5, 2.5, 3.5, 4.5):
            x[int(t * SAMPLE_RATE)] = 32767
        r = self.one("iso", x)
        self.assertEqual((r["status"], r["clamp_count"], r["clamp_max_run"]), ("written", "5", "1"))
        _, clip = read(self.root / "out_iso" / "other" / "boardbg_bg1_01_0000000.wav")
        self.assertEqual(list(clip), x[:sb.CLIP_SAMPLES])     # 글리치 샘플 수정 0

    def test_run_of_two_rejected(self) -> None:           # (b)
        x = samples(POST_N)
        x[SAMPLE_RATE] = x[SAMPLE_RATE + 1] = 32767
        r = self.one("run2", x)
        self.assertEqual((r["status"], r["clamp_count"], r["clamp_max_run"]),
                         ("rejected_clamp", "2", "2"))

    def test_loud_single_clamp_caught_by_sound(self) -> None:   # (c) 안전장치 — 5.3(d) 11번 모양
        x = samples(POST_N)
        s = 2 * SAMPLE_RATE
        # 실측 11번처럼 소리가 클램프 앞뒤로 이어진다(앞 기준 |x| 1,061~7,054) — ±2ms 마스크 밖에서 걸림.
        x[s - 800:s + 800] = [3000 if i % 2 else -3000 for i in range(1600)]
        x[s - 2:s + 3] = [11_876, 23_371, 32_767, 29_472, 7_528]   # 클램프는 고립 1샘플
        r = self.one("loud", x)
        self.assertEqual((r["status"], r["clamp_max_run"], r["onset_ms"]),
                         ("rejected_sound", "1", "1950"))

    def glitch_then(self, name: str, at: int, vals: list[int]) -> tuple[dict, list[int]]:
        """1초 지점 고립 클램프 + 그 +at샘플부터 vals."""
        x = samples(POST_N)
        x[SAMPLE_RATE] = 32767
        x[SAMPLE_RATE + at:SAMPLE_RATE + at + len(vals)] = vals
        return self.one(name, x), x

    def test_glitch_spike_masked(self) -> None:           # (e) +18 두 번째 스파이크는 소리 아님
        r, x = self.glitch_then("spike18", 18, [2000])
        self.assertEqual((r["status"], r["clamp_max_run"]), ("written", "1"))
        _, clip = read(self.root / "out_spike18" / "other" / "boardbg_bg1_01_0000000.wav")
        self.assertEqual(list(clip), x[:sb.CLIP_SAMPLES])     # 마스크는 판정용 — 출력 PCM 원본 그대로

    def test_burst_after_glitch_caught(self) -> None:     # (f) 마스크 밖으로 이어지는 50ms 버스트
        r, _ = self.glitch_then("burst", 18, [2000 if i % 2 else -2000 for i in range(800)])
        self.assertEqual((r["status"], r["onset_ms"]), ("rejected_sound", "1002"))   # +33 = 마스크 다음

    def test_spike_outside_mask_caught(self) -> None:     # (g) 마스크 경계(+32) 밖 한 점
        r, _ = self.glitch_then("spike40", 40, [2000])
        self.assertEqual((r["status"], r["onset_ms"]), ("rejected_sound", "1002"))

    def test_sign_boundary(self) -> None:                 # (d) −32768 · +32767 모두 클램프
        for name, at, vals, want in (("neg", SAMPLE_RATE, [-32768], ("written", "1")),
                                     ("pos", SAMPLE_RATE, [32767], ("written", "1")),
                                     ("pn", SAMPLE_RATE, [32767, -32768], ("rejected_clamp", "2"))):
            x = samples(POST_N)
            x[at:at + len(vals)] = vals
            r = self.one(name, x)
            self.assertEqual((r["status"], r["clamp_max_run"]), want, name)

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
        self.assertEqual(keys, {"boardbg_bg1"})     # 테이크 3개(01 · 03 · 06)가 같은 키

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
        self.assertIn("planned: 3", buf.getvalue())   # 03(고립 1샘플 클램프)이 결정 ①로 통과
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
