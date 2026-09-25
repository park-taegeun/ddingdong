"""합성 flac · 가짜 AUDIO_INFO 로 Zeroth 선별 · 조각내기 규칙을 검증한다(실데이터 무관, ffmpeg 필요).

  env -u DDINGDONG_DATA_ROOT python -m ml.curation.tests.test_zeroth_negatives
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from ...pipeline.config import source_key
from .. import zeroth_negatives as zn
from ..slice_negatives import REPO_ROOT

# 가짜 이름 — 산출 어디에도 나오면 안 된다(NAME 미출력 불변식).
FAKE_NAMES = {"201": "가짜이름갑", "202": "가짜이름을", "203": "가짜이름병", "204": "가짜이름정"}
SEX = {"201": "f", "202": "m", "203": "f", "204": "m"}
SETS = {"201": "train_data_01", "202": "train_data_01", "203": "test_data_01", "204": "test_data_01"}
# 화자 → [(발화번호, 초)]. 204 는 AUDIO_INFO 에만 있다.
UTTS = {
    "201": [("0001", 1.2), ("0002", 7.5), ("0003", 3.5), ("0004", 4.0)],
    "202": [("0011", 3.2), ("0012", 3.3), ("0013", 3.4), ("0014", 3.6)],
    "203": [("0021", 6.1)],
}
N = 2
SCRIPT = "003"


def _flac(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=440:duration={seconds}", "-ar", "16000", "-ac", "1",
                    str(path)], check=True)


def build(root: Path) -> tuple[Path, Path]:
    corpus = root / "zeroth"
    info = corpus / "AUDIO_INFO"
    corpus.mkdir()
    info.write_text("SPEAKERID|NAME|SEX|SCRIPTID|DATASET\n" + "".join(
        f"{s}|{FAKE_NAMES[s]}|{SEX[s]}|{SCRIPT}|{SETS[s]}\n" for s in FAKE_NAMES), encoding="utf-8")
    for spk, utts in UTTS.items():
        folder = corpus / SETS[spk] / SCRIPT / spk
        lines = []
        for num, sec in utts:
            _flac(folder / f"{spk}_{SCRIPT}_{num}.flac", sec)
            lines.append(f"{spk}_{SCRIPT}_{num} 가짜 문장 {num}\n")
        (folder / f"{spk}_{SCRIPT}.trans.txt").write_text("".join(lines), encoding="utf-8")
    # 폴더와 파일명 화자가 다른 파일 → 거부 기록
    _flac(corpus / "train_data_01" / SCRIPT / "201" / f"202_{SCRIPT}_0099.flac", 3.5)
    return info, corpus


def run(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = zn.main(list(argv))
    return rc, buf.getvalue()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def wavs(folder: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.glob("*.wav"))}


class ZerothNegativesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.info, cls.corpus = build(cls.root)
        cls.stdout = []

        def select(out: Path, n: int) -> Path:
            rc, text = run("select", "--audio-info", str(cls.info), "--corpus-root",
                           str(cls.corpus), "--out-dir", str(out), "--per-speaker", str(n))
            assert rc == 0
            cls.stdout.append(text)
            return out / zn.CANDIDATES_NAME

        def slice_(cands: Path, out: Path, cap: int) -> list[dict]:
            rc, text = run("slice", "--candidates", str(cands), "--corpus-root", str(cls.corpus),
                           "--out-dir", str(out), "--max-clips-per-utterance", str(cap))
            assert rc == 0
            cls.stdout.append(text)
            return read_csv(out / zn.MANIFEST_NAME)

        cls.sel1 = select(cls.root / "sel1", N)
        cls.sel2 = select(cls.root / "sel2", N)
        cls.all = select(cls.root / "all", 99)
        cls.slice_ = staticmethod(slice_)
        cls.cap1 = slice_(cls.all, cls.root / "cap1", 1)
        cls.cap2 = slice_(cls.all, cls.root / "cap2", 2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def written(self, rows: list[dict], utt: str) -> list[int]:
        return sorted(int(r["start_ms"]) for r in rows
                      if r["status"] == "written" and f"_{utt}_" in r["out_rel_path"])

    def test_per_speaker_n_deterministic(self) -> None:
        self.assertEqual(self.sel1.read_bytes(), self.sel2.read_bytes())
        rows = read_csv(self.sel1)
        for spk, utts in UTTS.items():
            ids = [f"{spk}_{SCRIPT}_{num}" for num, _ in utts]
            want = sorted(ids, key=lambda u: hashlib.sha256(
                f"{zn.SALT}|{u}".encode()).hexdigest())[:N]
            self.assertEqual([r["utt_id"] for r in rows if r["speaker_id"] == spk], want, spk)
        summary = (self.root / "sel1" / zn.SELECT_SUMMARY_NAME).read_text(encoding="utf-8")
        self.assertIn("- 203: 1", summary)                   # N 미만 화자 기록
        self.assertIn("202_003_0099.flac: 파일명의 화자·대본이 폴더와 다름", summary)
        self.assertIn("## AUDIO_INFO 에만 있고 발화가 없는 화자", summary)

    def test_candidate_columns(self) -> None:
        with self.all.open(encoding="utf-8") as fh:
            self.assertEqual(tuple(next(csv.reader(fh))), zn.CANDIDATE_FIELDS)
        row = next(r for r in read_csv(self.all) if r["utt_id"] == "203_003_0021")
        self.assertEqual((row["sex"], row["zeroth_set"], row["text"]),
                         ("f", "test_data_01", "가짜 문장 0021"))
        self.assertAlmostEqual(float(row["duration_sec"]), 6.1, places=1)
        self.assertEqual(len(read_csv(self.all)), sum(len(v) for v in UTTS.values()))

    def test_no_name_in_outputs(self) -> None:
        blobs = [p.read_text(encoding="utf-8") for p in self.root.rglob("*")
                 if p.suffix in (".csv", ".md") and p.parent != self.corpus]
        self.assertGreaterEqual(len(blobs), 8)
        for name in FAKE_NAMES.values():
            for blob in blobs + self.stdout:
                self.assertNotIn(name, blob)

    def test_short_utterance_padded(self) -> None:
        self.assertEqual(self.written(self.cap2, "0001"), [0])
        path = self.root / "cap2" / zn.CLASS_DIR / f"zeroth_201_{SCRIPT}_0001_0000000.wav"
        with wave.open(str(path), "rb") as wf:
            pcm = wf.readframes(wf.getnframes())
        samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
        self.assertEqual(len(samples), zn.CLIP_SEC * 16_000)
        self.assertTrue(any(samples[:16_000]))
        self.assertFalse(any(samples[int(1.3 * 16_000):]))

    def test_cap(self) -> None:
        self.assertEqual(self.written(self.cap2, "0002"), [0, 3000])
        self.assertEqual(self.written(self.cap1, "0002"), [0])
        dropped = [r["start_ms"] for r in self.cap1
                   if r["status"] == "dropped_cap" and r["reason"].startswith(f"201_{SCRIPT}_0002:")]
        self.assertEqual(dropped, ["3000"])

    def test_speaker_group_key(self) -> None:
        keys: dict[str, set[str]] = {}
        for path in (self.root / "cap2" / zn.CLASS_DIR).glob("*.wav"):
            spk = path.stem.split("_")[1]
            self.assertEqual(source_key(path.stem), f"zeroth_{spk}", path.name)
            keys.setdefault(source_key(path.stem), set()).add(path.stem.split("_")[3])
        self.assertEqual(set(keys), {"zeroth_201", "zeroth_202", "zeroth_203"})
        self.assertEqual(len(keys["zeroth_201"]), 4)          # 발화 4개 → 그룹 1개

    def test_output_format(self) -> None:
        for path in (self.root / "cap2" / zn.CLASS_DIR).glob("*.wav"):
            with wave.open(str(path), "rb") as wf:
                self.assertEqual((wf.getnchannels(), wf.getsampwidth(), wf.getframerate(),
                                  wf.getnframes()), (1, 2, 16_000, zn.CLIP_SEC * 16_000), path.name)

    def test_idempotent(self) -> None:
        out = self.root / "idem"
        self.slice_(self.all, out, 1)
        victim = out / zn.CLASS_DIR / f"zeroth_202_{SCRIPT}_0011_0000000.wav"
        victim.write_bytes(b"sentinel")
        before = wavs(out / zn.CLASS_DIR)
        rows = self.slice_(self.all, out, 1)
        self.assertEqual(wavs(out / zn.CLASS_DIR), before)
        self.assertEqual({r["status"] for r in rows if r["out_rel_path"]}, {"skipped_exists"})

    def test_dry_run_writes_nothing(self) -> None:
        out = self.root / "dry"
        rc, text = run("slice", "--candidates", str(self.all), "--corpus-root", str(self.corpus),
                       "--out-dir", str(out), "--max-clips-per-utterance", "1", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("planned", text)
        self.assertFalse(out.exists())

    def test_bad_rows_rejected(self) -> None:
        good = read_csv(self.all)[0]
        bad = self.root / "bad.csv"
        with bad.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=zn.CANDIDATE_FIELDS)
            writer.writeheader()
            writer.writerow({**good, "rel_path": "../outside.flac"})
            writer.writerow({**good, "utt_id": "999_003_0001"})      # 화자 불일치
        rc, text = run("slice", "--candidates", str(bad), "--corpus-root", str(self.corpus),
                       "--out-dir", str(self.root / "badout"), "--max-clips-per-utterance", "1",
                       "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("- rejected_path: 1", text)
        self.assertIn("- rejected_id: 1", text)

    def test_out_dir_guards(self) -> None:
        for bad in (REPO_ROOT / "ml" / "nc_should_not_exist",
                    self.root / "ds" / "01_clips" / "x"):
            with self.assertRaises(SystemExit, msg=str(bad)):
                run("select", "--audio-info", str(self.info), "--corpus-root", str(self.corpus),
                    "--out-dir", str(bad), "--per-speaker", "1")
            with self.assertRaises(SystemExit, msg=str(bad)):
                run("slice", "--candidates", str(self.all), "--corpus-root", str(self.corpus),
                    "--out-dir", str(bad), "--max-clips-per-utterance", "1")
            self.assertFalse(bad.exists())

    def test_required_args(self) -> None:
        full_sel = ["select", "--audio-info", str(self.info), "--corpus-root", str(self.corpus),
                    "--out-dir", str(self.root / "x"), "--per-speaker", "1"]
        full_sl = ["slice", "--candidates", str(self.all), "--corpus-root", str(self.corpus),
                   "--out-dir", str(self.root / "x"), "--max-clips-per-utterance", "1"]
        for full in (full_sel, full_sl):
            for i in range(1, len(full), 2):            # 인자 하나씩 빼면 모두 실패
                argv = full[:i] + full[i + 2:]
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    run(*argv)
        self.assertFalse((self.root / "x").exists())


if __name__ == "__main__":
    unittest.main()
