"""합성 wav 로 직접녹음 조각내기 규칙을 검증한다(실데이터 무관, ffmpeg 불요).

  env -u DDINGDONG_DATA_ROOT python -m ml.curation.tests.test_slice_direct
"""

from __future__ import annotations

import ast
import contextlib
import csv
import hashlib
import io
import math
import re
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

from ...pipeline import config
from ...pipeline.config import SAMPLE_RATE, source_key
from .. import slice_boardbg as sb
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
    "direct_knock_B_05": dict(n=POST_N, onset=1.0, clamp_sine=True),     # 큰 소리 연속 클램프(마스크 안 함)
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

    def judge_one(self, name: str, x: list[int]) -> tuple[dict, bytes | None]:
        src = self.root / f"mask_{name}" / "direct_knock_M_01.wav"
        write(src, x)
        return sd.judge(src, {"baseline_ms": 100, "onset_ratio": 20, "onset_floor": 500})

    def test_glitch_spike_masked(self) -> None:           # (i) +18 두 번째 스파이크는 onset 아님
        x = samples(POST_N, onset=1.5, glitch=1.0)
        x[SAMPLE_RATE + 18] = 2000
        row, pcm = self.judge_one("spike", x)
        self.assertIsNotNone(pcm)
        self.assertEqual(row["onset_ms"], 1500)                # 스파이크(1001ms)가 아니라 버스트

    def test_burst_before_glitch_unchanged(self) -> None:  # (j) 버스트가 먼저면 마스크 전후 같다
        x = samples(POST_N, onset=0.8)
        x[SAMPLE_RATE] = 32767
        a = [abs(v) for v in x]
        args = (100 * sd.MS, 20, 500)
        before = a[:]
        self.assertEqual(sd.find_onset(sd.mask_glitch_clamps(a), *args), sd.find_onset(a, *args))
        self.assertEqual(a, before)                            # 헬퍼는 원본 목록을 바꾸지 않는다
        row, _ = self.judge_one("before", x)
        self.assertEqual(row["onset_ms"], 800)

    def test_mask_not_in_output(self) -> None:           # (k) 마스크는 판정용 — 출력 PCM 원본 그대로
        x = samples(POST_N, onset=1.5, glitch=1.0)
        x[SAMPLE_RATE + 18] = 2000
        x[SAMPLE_RATE + 1_600] = -32768                      # 창 안 글리치(1.6초)
        row, pcm = self.judge_one("pcm", x)
        start = row["start_ms"] * sd.MS
        self.assertEqual(pcm, array("h", x[start:start + sd.CLIP_SAMPLES]).tobytes())
        self.assertEqual(row["clip_clamp_count"], 2)

    def test_run2_glitch_masked(self) -> None:           # (l) 결정 2026-09-30 ② — 2샘플 런도 글리치
        x = samples(POST_N, onset=1.5)
        x[SAMPLE_RATE:SAMPLE_RATE + 2] = [32767, -32768]
        x[SAMPLE_RATE + 1 + 17] = 2000                       # 런 끝 +17 두 번째 튐
        a = [abs(v) for v in x]
        m = sd.mask_glitch_clamps(a)
        lo, hi = SAMPLE_RATE - sd.CLAMP_MASK_HALF_WIDTH, SAMPLE_RATE + 2 + sd.CLAMP_MASK_HALF_WIDTH
        self.assertEqual(m[lo:hi], [sd.CLAMP] * (hi - lo))   # 런 전체 + 앞 32 + 뒤 32
        self.assertEqual((m[lo - 1], m[hi]), (a[lo - 1], a[hi]))
        row, pcm = self.judge_one("run2", x)
        self.assertEqual(row["onset_ms"], 1500)                # 튐(1001ms)이 아니라 버스트
        start = row["start_ms"] * sd.MS
        self.assertEqual(pcm, array("h", x[start:start + sd.CLIP_SAMPLES]).tobytes())

    def test_run3_not_masked(self) -> None:              # (m) 3샘플 이상 = 진짜 잘림 — 가리지 않는다
        x = samples(POST_N, onset=1.5)
        x[SAMPLE_RATE:SAMPLE_RATE + 3] = [32767] * 3
        x[SAMPLE_RATE + 2 + 17] = 2000
        a = [abs(v) for v in x]
        self.assertEqual(sd.mask_glitch_clamps(a), a)
        row, _ = self.judge_one("run3", x)
        self.assertEqual(row["onset_ms"], 1001)                # 런 옆 튐이 그대로 onset

    def test_required_args(self) -> None:
        full = ["--recording-dir", str(self.rec), "--out-dir", str(self.root / "y"), *PARAMS]
        for i in range(0, len(full), 2):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                sd.main(full[:i] + full[i + 2:])
        self.assertFalse((self.root / "y").exists())


RECEIVER = REPO_ROOT / "server" / "tools" / "record_receiver.py"


def receiver_name_rules() -> tuple[tuple[str, ...], str, ast.FunctionDef]:
    """수신기 원문(import 안 함)에서 (LABELS, UNIT_RE 패턴, take_name 정의). 각각 정확히 1곳이 아니면 AssertionError."""
    tree = ast.parse(RECEIVER.read_text(encoding="utf-8"))
    assigns = {name: [n.value for n in tree.body if isinstance(n, ast.Assign)
                      and [getattr(t, "id", None) for t in n.targets] == [name]]
               for name in ("LABELS", "UNIT_RE")}
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "take_name"]
    for name, found in (*assigns.items(), ("take_name", funcs)):
        assert len(found) == 1, f"record_receiver.py {name} 정의 {len(found)}건 — 정확히 1건이어야 한다"
    labels = ast.literal_eval(assigns["LABELS"][0])
    call = assigns["UNIT_RE"][0]
    assert (isinstance(call, ast.Call) and ast.unparse(call.func) == "re.compile" and call.args
            and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)), \
        f"record_receiver.py UNIT_RE 해석 불가: {ast.unparse(call)}"
    return labels, call.args[0].value, funcs[0]


def receiver_take_name(fn: ast.FunctionDef):
    """take_name 의 반환 f-string 을 그대로 평가하는 함수 — 형식을 손으로 다시 쓰지 않는다."""
    args = [a.arg for a in fn.args.args]
    body = fn.body
    assert (len(args) == 3 and len(body) == 1 and isinstance(body[0], ast.Return)
            and isinstance(body[0].value, ast.JoinedStr)), \
        f"record_receiver.py take_name 구조 해석 불가: {ast.unparse(fn)}"
    code = compile(ast.Expression(body[0].value), str(RECEIVER), "eval")
    return lambda label, unit, take: eval(code, {"__builtins__": {}}, dict(zip(args, (label, unit, take))))


class ReceiverNameContractTest(unittest.TestCase):
    """녹음 수신기 파일 이름 규칙 ↔ ML 규칙(slice_direct.NAME_RE · slice_boardbg.UNIT_RE · source_key) 대조.

    한쪽만 바뀌면 FAIL. ML 쪽은 모듈 속성을 실행 시점에 읽는다. 근거 = decisions.md 5.3 · 33.12 · 33.16(e)(g).
    """

    UNITS = ("a", "A", "B2", "7", "1234567", "aB3")   # 소문자 · 대문자 · 숫자만 · 섞임 · 7자리 숫자
    TAKES = (1, 9, 10, 99, 100)
    PIECE_MS = (0, 1000, 2120)                         # post 5.12초 안 3초 조각 시작점

    def setUp(self) -> None:
        self.labels, self.unit_pat, fn = receiver_name_rules()
        self.take_name = receiver_take_name(fn)

    def test_unit_re_matches_boardbg_copy(self) -> None:
        self.assertEqual(self.unit_pat, sb.UNIT_RE.pattern,
                         "수신기 UNIT_RE ≠ slice_boardbg.UNIT_RE — server/tools/record_receiver.py 와 같이 고친다")

    def test_labels_are_ml_classes(self) -> None:
        self.assertLessEqual(set(self.labels), set(config.CLASSES),
                             f"수신기 LABELS {self.labels} ⊄ ml CLASSES {config.CLASSES}")

    def test_receiver_names_parse_back_in_ml(self) -> None:
        unit_re = re.compile(self.unit_pat)
        for label in self.labels:
            for unit in self.UNITS:
                self.assertTrue(unit_re.match(unit), f"수신기 UNIT_RE 가 유닛 {unit!r} 을 거부 — 이 표를 다시 본다")
                for take in self.TAKES:
                    name = self.take_name(label, unit, take)
                    with self.subTest(name=name):
                        self.assertTrue(name.endswith(".wav"), f"수신기 이름 {name} 이 .wav 가 아니다")
                        stem = name[:-len(".wav")]
                        m = sd.NAME_RE.match(stem)
                        self.assertIsNotNone(m, f"slice_direct.NAME_RE 가 수신기 이름 {stem} 을 못 읽는다")
                        self.assertEqual((m.group(1), m.group(2), int(m.group(3))), (label, unit, take),
                                         f"slice_direct.NAME_RE 가 {stem} 을 다르게 읽는다")
                        key = f"direct_{label}_{unit}"
                        for s in (stem, *(f"{stem}_{ms:07d}" for ms in self.PIECE_MS)):
                            self.assertEqual(config.source_key(s), key, f"source_key({s}) ≠ {key}")

    def test_underscore_unit_is_rejected_because_name_re_misreads_it(self) -> None:
        self.assertIsNone(re.match(self.unit_pat, "a_1"), "수신기 UNIT_RE 가 밑줄 유닛을 허용한다")
        m = sd.NAME_RE.match(self.take_name("knock", "a_1", 1)[:-len(".wav")])
        self.assertTrue(m is None or (m.group(1), m.group(2)) != ("knock", "a_1"))   # 라벨이 knock_a 로 읽힌다


if __name__ == "__main__":
    unittest.main()
