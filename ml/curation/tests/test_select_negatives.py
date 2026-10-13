"""가짜 FSD50K 메타데이터로 선별 규칙을 검증한다(실데이터 무관, repo 안에서 실행).

  python -m ml.curation.tests.test_select_negatives

T1~T5 = 규칙 검증. NC-1~NC-3 = 네거티브 컨트롤(규칙을 망가뜨리면 해당 테스트가
반드시 깨지는지) — baseline 통과 확인 → 주입 → 실패 확인 → finally 복원 → 재통과.
B1~B8 = 추가 선별(--boost) 검증. NC-4 · NC-5 = boost 쪽 네거티브 컨트롤.
"""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import wave
from contextlib import contextmanager
from pathlib import Path

from .. import select_negatives as sn
from ..taxonomy import ASSIGNMENT

# 라벨당 pool 을 상한보다 크게 잡아야 NC-3(선택 순서 치환)이 우연히 같은 답을
# 내지 않는다. 60개 중 6개를 고르므로 순서가 다르면 거의 확실히 갈린다.
PER_LABEL = 60
TARGET_SIZE = 24

VOCAB = ["Speech", "Music", "Telephone", "Dog", "Doorbell", "Knock", "Siren",
         "Alarm", "Door", "Slam", "Tap", "Bell", "Domestic_sounds_and_home_sounds"]
KEEP_LABELS = ["Speech", "Music", "Telephone", "Dog"]


def _write_wav(path: Path, seconds: float) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16_000)
        wf.writeframes(b"\x00\x00" * int(16_000 * seconds))


def build_fixture(root: Path) -> dict:
    """가짜 dev.csv · vocabulary.csv · pp_pnp · wav 를 만든다."""
    audio = root / "audio"
    audio.mkdir(parents=True)
    mids = {name: f"/m/fake{i:03d}" for i, name in enumerate(VOCAB)}

    (root / "vocabulary.csv").write_text(
        "".join(f"{i},{name},{mids[name]}\n" for i, name in enumerate(VOCAB)),
        encoding="utf-8")

    rows: list[dict] = []
    ratings: dict[str, dict] = {}
    short_ids: list[str] = []
    fsd = 1000

    def add(labels: list[str], seconds: float = 1.0, pp: bool = True) -> str:
        nonlocal fsd
        fsd += 1
        fid = str(fsd)
        rows.append({"fname": fid, "labels": ",".join(labels),
                     "mids": ",".join(mids[l] for l in labels),
                     "split": "train" if fsd % 5 else "val"})
        ratings[fid] = {mids[l]: ([1.0, 1.0] if pp else [0.5, 0.5]) for l in labels}
        _write_wav(audio / f"{fid}.wav", seconds)
        return fid

    for label in KEEP_LABELS:
        for i in range(PER_LABEL):
            add([label], pp=(i % 2 == 0))
    # 제외 ① — target 자신
    target_ids = [add(["Doorbell", "Alarm", "Door"]), add(["Knock", "Door"]),
                  add(["Siren", "Alarm"])]
    # 제외 ① — Alarm 미분화(자식 라벨 없음)
    target_ids.append(add(["Alarm", "Domestic_sounds_and_home_sounds"]))
    # 보류 — Tap / Door 미분화 / Bell 미분화
    hold_ids = [add(["Tap"]), add(["Door", "Domestic_sounds_and_home_sounds"]),
                add(["Bell"])]
    # 형제 hard negative 는 살아남아야 한다(부모로 제외하면 안 된다)
    sibling_ids = [add(["Slam", "Door", "Domestic_sounds_and_home_sounds"]),
                   add(["Telephone", "Alarm"])]
    # 제외 ② — 01_clips 양성으로 이미 쓴 원본
    # 희소 라벨(Slam)로 둬야 규모 상한에 밀리지 않고 「규칙이 뺐다」를 볼 수 있다
    positive_id = add(["Slam", "Door", "Domestic_sounds_and_home_sounds"])
    clips_dir = root / "01_clips" / "doorbell"
    clips_dir.mkdir(parents=True)
    _write_wav(clips_dir / f"{positive_id}_0000000.wav", 1.0)
    _write_wav(clips_dir / "direct_01_0000000.wav", 1.0)          # 비-FSD50K stem
    # 제외 ③ — 길이 미달
    short_ids.append(add(["Music"], seconds=0.01))

    with (root / "dev.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["fname", "labels", "mids", "split"])
        writer.writeheader()
        writer.writerows(rows)
    (root / "pp_pnp.json").write_text(json.dumps(ratings), encoding="utf-8")

    return {"root": root, "audio": audio, "target_ids": target_ids,
            "hold_ids": hold_ids, "sibling_ids": sibling_ids,
            "positive_id": positive_id, "short_ids": short_ids,
            "n_clips": len(rows)}


def run_selection(fx: dict, out_dir: Path) -> list[dict]:
    root = fx["root"]
    argv = [
        "--dev-csv", str(root / "dev.csv"),
        "--vocabulary-csv", str(root / "vocabulary.csv"),
        "--pp-pnp", str(root / "pp_pnp.json"),
        "--audio-root", str(fx["audio"]),
        "--positive-clips", str(root / "01_clips"),
        "--out-dir", str(out_dir),
        "--target-size", str(TARGET_SIZE),
    ]
    code = sn.main(argv)
    assert code in (0, 1), code          # 600 미만이라 1 이 정상(가짜 입력)
    with (out_dir / "candidates.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ── T1~T5 ────────────────────────────────────────────────────────────────────

def t1_target_excluded(fx: dict, rows: list[dict]) -> None:
    ids = {r["fsd_id"] for r in rows}
    assert not (ids & set(fx["target_ids"])), "target 계열이 후보에 섞였다"
    for row in rows:
        labels = row["all_labels"].split(",")
        assert not any(ASSIGNMENT[l] == "target" for l in labels), row
    # 🔴 부모(Door · Alarm)로 제외하면 형제 hard negative 가 통째로 사라진다.
    # 규모 상한과 무관하게 「제외되지 않는다」를 규칙 층에서 직접 본다.
    assert sn.classify(("Slam", "Door", "Domestic_sounds_and_home_sounds"))[0] == "keep"
    assert sn.classify(("Telephone", "Alarm"))[0] == "keep"
    # target 은 hold 보다 앞선다 — 라벨 나열 순서로 판정이 뒤집히면 안 된다.
    assert sn.classify(("Wood", "Knock", "Door"))[0] == "target"
    assert sn.classify(("Knock", "Wood", "Door"))[0] == "target"
    # 미분화 Alarm(부모 규칙 target)도 hold 라벨보다 앞선다.
    assert sn.classify(("Glockenspiel", "Alarm"))[0] == "target"
    # hold 만 있으면 그대로 보류.
    assert sn.classify(("Wood", "Domestic_sounds_and_home_sounds"))[0] == "hold"


def t2_positive_excluded(fx: dict, rows: list[dict]) -> None:
    ids = {r["fsd_id"] for r in rows}
    assert fx["positive_id"] not in ids, "양성으로 쓴 원본이 후보에 남았다"


def t3_short_excluded(fx: dict, rows: list[dict]) -> None:
    ids = {r["fsd_id"] for r in rows}
    assert not (ids & set(fx["short_ids"])), "MIN_DURATION_SEC 미만이 후보에 남았다"
    for row in rows:
        assert float(row["duration_sec"]) >= sn.MIN_DURATION_SEC, row


def t4_deterministic(fx: dict, rows: list[dict]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        again = run_selection(fx, Path(tmp))
    assert rows == again, "같은 입력인데 결과가 달라졌다"
    # 내장 hash() 였다면 프로세스 salt 때문에 재현이 안 된다 — 키가 sha256 인지 확인
    import hashlib
    assert sn.stable_key("1") == hashlib.sha256(
        f"{sn.SALT}:1".encode()).hexdigest()


def t5_outputs(fx: dict, rows: list[dict]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        run_selection(fx, out)
        for name in ("candidates.csv", "listen_sample.csv", "summary.md"):
            assert (out / name).is_file(), name
        with (out / "listen_sample.csv").open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            assert tuple(reader.fieldnames) == sn.CANDIDATE_FIELDS
            sample = list(reader)
        assert len(sample) == min(sn.LISTEN_SAMPLE_SIZE, len(rows)), len(sample)
        assert {r["fsd_id"] for r in sample} <= {r["fsd_id"] for r in rows}
        assert len({r["category"] for r in sample}) > 1, "층화가 안 됐다"
        text = (out / "summary.md").read_text(encoding="utf-8")
        assert "PP / PNP 비율" in text and "보류 사유별" in text
    assert tuple(rows[0]) == sn.CANDIDATE_FIELDS
    assert all(r["split"] in ("train", "val") for r in rows)
    assert all(r["rating"] in ("PP", "PNP", "NP", "U", "NA") for r in rows)


# ── B1~B8 추가 선별(boost) ───────────────────────────────────────────────────

BOOST_VOCAB = ["Walk_and_footsteps", "Slam", "Speech", "Tap", "Knock", "Door",
               "Domestic_sounds_and_home_sounds"]
WALK_POOL = 30          # 기존 상한(3)보다 훨씬 커야 「건너뛰기」 · 순서 차이가 드러난다
BOOST_ARGS = ["--boost", "Walk_and_footsteps=10", "--boost", "Slam=5"]


def build_boost_fixture(root: Path) -> dict:
    audio = root / "audio"
    audio.mkdir(parents=True)
    mids = {name: f"/m/b{i:03d}" for i, name in enumerate(BOOST_VOCAB)}
    (root / "vocabulary.csv").write_text(
        "".join(f"{i},{n},{mids[n]}\n" for i, n in enumerate(BOOST_VOCAB)), encoding="utf-8")
    rows, ratings, info = [], {}, {}
    fsd = 5000

    def add(labels: list[str], pp: bool = True) -> str:
        nonlocal fsd
        fsd += 1
        fid = str(fsd)
        rows.append({"fname": fid, "labels": ",".join(labels),
                     "mids": ",".join(mids[l] for l in labels), "split": "train"})
        ratings[fid] = {mids[l]: ([1.0] if pp else [0.5]) for l in labels}
        info[fid] = {"license": f"http://creativecommons.org/licenses/by/{fsd % 2 + 3}.0/"}
        _write_wav(audio / f"{fid}.wav", 1.0)
        return fid

    walk = [add(["Walk_and_footsteps"], pp=(i % 3 != 0)) for i in range(WALK_POOL)]
    slam = [add(["Slam", "Door", "Domestic_sounds_and_home_sounds"]) for _ in range(4)]
    speech = [add(["Speech"]) for _ in range(WALK_POOL)]
    # 🔴 지정 라벨 + hold/target — 어떤 경우에도 추가분이 되면 안 된다
    hold_ids = [add(["Walk_and_footsteps", "Tap"]) for _ in range(3)]
    target_ids = [add(["Walk_and_footsteps", "Knock", "Door"]) for _ in range(2)]
    positive_id = walk[-1]
    pos_dir = root / "01_clips" / "knock"
    pos_dir.mkdir(parents=True)
    _write_wav(pos_dir / f"{positive_id}_0000000.wav", 1.0)
    with (root / "dev.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["fname", "labels", "mids", "split"])
        writer.writeheader()
        writer.writerows(rows)
    (root / "pp_pnp.json").write_text(json.dumps(ratings), encoding="utf-8")
    (root / "clips_info.json").write_text(json.dumps(info), encoding="utf-8")
    return {"root": root, "audio": audio, "walk": walk, "slam": slam, "speech": speech,
            "hold_ids": hold_ids, "target_ids": target_ids, "positive_id": positive_id}


def _base_argv(fx: dict, out_dir: Path) -> list[str]:
    root = fx["root"]
    return ["--dev-csv", str(root / "dev.csv"), "--vocabulary-csv", str(root / "vocabulary.csv"),
            "--pp-pnp", str(root / "pp_pnp.json"), "--audio-root", str(fx["audio"]),
            "--positive-clips", str(root / "01_clips"), "--out-dir", str(out_dir),
            "--clips-info", str(root / "clips_info.json")]


def _read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def run_base(fx: dict, out_dir: Path) -> list[dict]:
    sn.main(_base_argv(fx, out_dir) + ["--target-size", "9"])   # 라벨당 3
    return _read(out_dir / "candidates.csv")


def run_boost(fx: dict, out_dir: Path, extra: list[str] = BOOST_ARGS) -> list[dict]:
    code = sn.main(_base_argv(fx, out_dir) + ["--existing-candidates",
                                              str(fx["existing_csv"]), *extra])
    assert code == 0, code
    return _read(out_dir / "candidates_boost.csv")


def b1_no_overlap(fx: dict, rows: list[dict]) -> None:
    assert not ({r["fsd_id"] for r in rows} & fx["existing_ids"]), "기존 후보와 겹친다"
    assert "기존 후보와 겹침: 0" in fx["summary"]


def b2_only_boost_labels(fx: dict, rows: list[dict]) -> None:
    assert {r["selected_label"] for r in rows} == {"Walk_and_footsteps", "Slam"}
    assert not ({r["fsd_id"] for r in rows} & set(fx["speech"])), "지정 밖 라벨이 들어왔다"
    assert fx["positive_id"] not in {r["fsd_id"] for r in rows}, "양성 원본이 들어왔다"
    assert all(r["license"] for r in rows), "license 열이 비었다"
    assert tuple(rows[0]) == sn.CANDIDATE_FIELDS


def b3_deterministic(fx: dict, rows: list[dict]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run_boost(fx, Path(tmp))
        for name in ("candidates_boost.csv", "boost_summary.md"):
            assert (Path(tmp) / name).read_bytes() == (fx["boost_out"] / name).read_bytes(), name


def b4_hold_target_zero(fx: dict, rows: list[dict]) -> None:
    banned = set(fx["hold_ids"]) | set(fx["target_ids"])
    assert not ({r["fsd_id"] for r in rows} & banned), "hold · target 클립이 들어왔다"
    # 규모와 무관하게 풀 층에서 직접 본다(N 개 안에 우연히 안 뽑혀 통과하는 것 방지)
    clips = sn.load_clips(fx["root"] / "dev.csv")
    ratings = json.loads((fx["root"] / "pp_pnp.json").read_text(encoding="utf-8"))
    pools = sn._build_pools(clips, set(), ratings, fx["audio"], sn.Rejections())
    pooled = {row[2].fsd_id for pool in pools.values() for row in pool}
    assert not (pooled & banned), "hold · target 클립이 풀에 들어왔다"


def b5_shortfall(fx: dict, rows: list[dict]) -> None:
    n_slam = sum(r["selected_label"] == "Slam" for r in rows)
    assert n_slam == len(fx["slam"]) - 3, n_slam          # 4 중 기존 3 → 1
    assert sum(r["selected_label"] == "Walk_and_footsteps" for r in rows) == 10
    assert "부족분: 4 — Slam 4" in fx["summary"], fx["summary"]


def b6_bad_args(fx: dict, rows: list[dict]) -> None:
    bad = [["--boost", "Walk=5"], ["--boost", "walk_and_footsteps=5"],
           ["--boost", "Tap=5"], ["--boost", "Knock=5"], ["--boost", "Door=5"],
           ["--boost", "Slam=0"], ["--boost", "Slam=-1"], ["--boost", "Slam"],
           ["--boost", "Slam=--5"], ["--boost", "Slam=2.5"],
           ["--boost", "Slam=5", "--boost", "Slam=3"]]
    for extra in bad:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                run_boost(fx, Path(tmp), extra)
            except SystemExit:
                assert not (Path(tmp) / "candidates_boost.csv").exists(), extra
                continue
            raise AssertionError(f"즉시 실패하지 않았다: {extra}")
    with tempfile.TemporaryDirectory() as tmp:     # --existing-candidates 누락
        try:
            sn.main(_base_argv(fx, Path(tmp)) + BOOST_ARGS)
        except SystemExit:
            return
    raise AssertionError("--existing-candidates 없이 통과했다")


def b7_other_not_positive(fx: dict, rows: list[dict]) -> None:
    """01_clips/other 에 기존 후보 조각(숫자 stem)이 있어도 기존 선별이 재현된다."""
    with tempfile.TemporaryDirectory() as tmp:
        again = run_base(fx, Path(tmp))
    assert again == fx["existing"], "other/ 조각 때문에 기존 후보가 바뀌었다"


def b8_next_after_existing(fx: dict, rows: list[dict]) -> None:
    """PP 우선 → sha256 순 풀에서 기존 후보 다음부터 N개 — sn 과 독립 계산으로 대조."""
    def key(fid: str) -> str:
        return hashlib.sha256(f"{sn.SALT}:{fid}".encode()).hexdigest()
    pp = {fid for i, fid in enumerate(fx["walk"]) if i % 3 != 0}
    pool = [f for f in fx["walk"] if f != fx["positive_id"]]
    pool.sort(key=lambda f: (0 if f in pp else 1, key(f)))
    expected = [f for f in pool if f not in fx["existing_ids"]][:10]
    got = {r["fsd_id"] for r in rows if r["selected_label"] == "Walk_and_footsteps"}
    assert got == set(expected), "선택 순서가 규칙(PP → sha256)과 다르다"


BOOST_TESTS = [("B1 기존과 겹침 0", b1_no_overlap),
               ("B2 지정 라벨만 · license", b2_only_boost_labels),
               ("B3 결정성(바이트)", b3_deterministic),
               ("B4 hold · target 0", b4_hold_target_zero),
               ("B5 풀 부족 = 가진 만큼 + 기록", b5_shortfall),
               ("B6 잘못된 인자 즉시 실패", b6_bad_args),
               ("B7 other/ ≠ 양성(재현)", b7_other_not_positive),
               ("B8 기존 다음부터 N", b8_next_after_existing)]


def prepare_boost(root: Path) -> tuple[dict, list[dict]]:
    """기존 선별 → other/ 에 그 조각을 넣는다(1차 재학습 뒤 상태) → 추가 선별."""
    fx = build_boost_fixture(root / "meta")
    fx["existing_csv"] = root / "base" / "candidates.csv"
    fx["existing"] = run_base(fx, root / "base")
    fx["existing_ids"] = {r["fsd_id"] for r in fx["existing"]}
    other = fx["root"] / "01_clips" / "other"
    other.mkdir()
    for fid in fx["existing_ids"]:
        _write_wav(other / f"{fid}_0000000.wav", 0.1)
    fx["boost_out"] = root / "boost"
    rows = run_boost(fx, fx["boost_out"])
    fx["summary"] = (fx["boost_out"] / "boost_summary.md").read_text(encoding="utf-8")
    return fx, rows


TESTS = [("T1 제외① target", t1_target_excluded),
         ("T2 제외② 양성중복", t2_positive_excluded),
         ("T3 제외③ 길이", t3_short_excluded),
         ("T4 결정성", t4_deterministic),
         ("T5 산출 형식", t5_outputs)]


# ── 네거티브 컨트롤 ──────────────────────────────────────────────────────────

@contextmanager
def patched(obj, attr, value):
    """4단계 보장 중 ②주입 / ④복원. finally 로 반드시 되돌린다."""
    original = getattr(obj, attr)
    try:
        setattr(obj, attr, value)
        yield
    finally:
        setattr(obj, attr, original)


def nc1_break_target_rule():
    broken = dict(ASSIGNMENT)
    broken["Doorbell"] = broken["Knock"] = broken["Siren"] = "c"
    broken["Alarm"] = "c"
    return ("ASSIGNMENT", broken, "T1 제외① target")


def nc2_break_positive_rule():
    return ("load_positive_source_ids", lambda _: set(), "T2 제외② 양성중복")


def nc3_break_stable_key():
    """sha256 → 상수 키. 정렬이 입력 순서로 무너져 선택 결과가 갈려야 한다."""
    return ("stable_key", lambda fsd_id: "0", "T4 결정성")


def _run_nc(fx: dict, rows: list[dict], name: str, attr: str, value,
            broken_test: str) -> bool:
    """②주입 → ③해당 테스트가 깨지는지 확인 → ④finally 복원(patched 가 보장)."""
    with patched(sn, attr, value):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                injected = run_selection(fx, Path(tmp))
            except Exception:
                injected = []
        try:
            if attr == "stable_key":
                # 선택 순서가 갈리는지를 본다(같으면 sha256 이 일을 안 한 것)
                assert {r["fsd_id"] for r in injected} == {r["fsd_id"] for r in rows}
            else:
                dict(TESTS)[broken_test](fx, injected)
            detected = False
        except Exception:
            detected = True
    print(f"  {name}: 주입 시 {broken_test} "
          f"{'깨짐(정상 검출)' if detected else '통과(🔴 미검출)'}")
    return detected


NCS = [("NC-1 target 규칙 무력화", nc1_break_target_rule),
       ("NC-2 양성 대조 무력화", nc2_break_positive_rule),
       ("NC-3 sha256 → 상수 키", nc3_break_stable_key)]


def _old_positive_ids(clips_dir: Path) -> set[str]:
    """수정 전 동작 — other/ 까지 양성으로 센다."""
    return {sn.source_key(w.stem) for w in clips_dir.rglob("*.wav")
            if sn.source_key(w.stem).isdigit()}


# boost 쪽 — (이름, 바꿀 속성, 값, 깨져야 할 테스트)
BOOST_NCS = [("NC-4 양성 정의를 옛 동작(other 포함)으로", "load_positive_source_ids",
              _old_positive_ids, "B7 other/ ≠ 양성(재현)"),
             ("NC-5 sha256 → 이름순 키", "stable_key", lambda fid: fid, "B8 기존 다음부터 N")]


def _run_boost_nc(root: Path, name: str, attr: str, value, broken_test: str) -> bool:
    with patched(sn, attr, value):
        try:
            fx, rows = prepare_boost(root)
            dict(BOOST_TESTS)[broken_test](fx, rows)
            detected = False
        except Exception:
            detected = True
    print(f"  {name}: 주입 시 {broken_test} "
          f"{'깨짐(정상 검출)' if detected else '통과(🔴 미검출)'}")
    return detected


def _main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fx = build_fixture(root / "meta")
        out = root / "out"
        rows = run_selection(fx, out)
        print(f"fixture: dev {fx['n_clips']} 클립 → 후보 {len(rows)}")

        print("\n[baseline] T1~T5")
        for name, fn in TESTS:
            fn(fx, rows)
            print(f"  {name}: 통과")

        print("\n[NC] 규칙 주입 → 해당 테스트가 깨지는지")
        detected = [_run_nc(fx, rows, name, *factory()) for name, factory in NCS]

        print("\n[복원 확인] 주입 해제 뒤 T1~T5 재실행")
        rows_after = run_selection(fx, root / "out2")
        assert rows_after == rows, "복원 실패 — 결과가 달라졌다"
        for name, fn in TESTS:
            fn(fx, rows_after)
        print("  전건 재통과 · 결과 바이트 동일")

        print("\n[boost] B1~B8")
        fx_b, rows_b = prepare_boost(root / "boost")
        print(f"  fixture: 기존 {len(fx_b['existing'])} → 추가분 {len(rows_b)}")
        for name, fn in BOOST_TESTS:
            fn(fx_b, rows_b)
            print(f"  {name}: 통과")

        print("\n[NC] boost 규칙 주입")
        detected += [_run_boost_nc(root / f"nc{i}", name, *rest)
                     for i, (name, *rest) in enumerate(BOOST_NCS)]

        print("\n[복원 확인] 주입 해제 뒤 B1~B8 재실행")
        fx_r, rows_r = prepare_boost(root / "boost_after")
        assert [r["fsd_id"] for r in rows_r] == [r["fsd_id"] for r in rows_b]
        for name, fn in BOOST_TESTS:
            fn(fx_r, rows_r)
        print("  전건 재통과")

        if not all(detected):
            print("\n🔴 NC 미검출 — 위임 §9 정지 트리거")
            return 1
    print("\n전건 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
