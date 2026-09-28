"""Step 6 — 합성 더미 관통 검증 (실제 데이터 EPERM 무관, repo 안에서 실행).

클래스당 6개 더미 16k mono wav 생성 → Step1~5 전관통 → 출력/manifest/개수/누수가드 확인.
pytest 로도, 단독(`python -m ml.pipeline.tests.test_pipeline`)으로도 실행 가능.
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import numpy as np

from .. import assemble, augment, config, preprocess, split
from ..audio_io import iter_audio_files, probe, save_wav
from ..guards import ContentLeakageError, assert_no_content_leakage, assert_no_leakage
from .. import make_dummy
from ..make_dummy import make_dummy_dataset

PER_CLASS = 6


def _run_pipeline(root: Path):
    paths = config.resolve_paths(root)
    preprocess.preprocess(paths)
    split.split_dataset(paths)
    augment.augment(paths)
    final_counts = assemble.assemble(paths)
    final_rows = assemble.load_final_manifest(paths)
    guard = assert_no_leakage(final_rows)
    assert_no_content_leakage(final_rows)  # 내용 층(이중 검사) — 전관통 경로에서 항상 통과해야
    return paths, final_counts, guard


def test_pipeline_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_dummy_dataset(Path(tmp), per_class=PER_CLASS, seed=1)
        paths, final_counts, guard = _run_pipeline(root)

        # 1) 02 전처리: 클래스당 전량 통과, 규격 16k mono
        for cls in config.CLASSES:
            outs = list(iter_audio_files(paths.preprocessed / cls))
            assert len(outs) == PER_CLASS, f"{cls} 전처리 개수"
            info = probe(outs[0])
            assert info.samplerate == config.SAMPLE_RATE and info.channels == config.CHANNELS

        # 2) split manifest: 전 클립이 정확히 한 split 에 배정
        rows = split.load_split_manifest(paths)
        assert len(rows) == PER_CLASS * len(config.CLASSES)
        assert {r["split"] for r in rows} <= {"train", "val", "test"}

        # 3) 증강: train 클립에만, val/test stem 은 03 에 없어야 함
        train_stems = {r["stem"] for r in rows if r["split"] == "train"}
        holdout_stems = {r["stem"] for r in rows if r["split"] != "train"}
        aug_base = set()
        for cls in config.CLASSES:
            for a in iter_audio_files(paths.augmented / cls):
                aug_base.add(augment.base_stem(a.name))
        assert aug_base <= train_stems, "train 밖 stem 이 증강됨"
        assert not (aug_base & holdout_stems), "val/test 가 증강됨 (누수)"

        # 4) 05 조립: val/test 는 원본만, train 은 원본+증강
        final_rows = assemble.load_final_manifest(paths)
        val_test_aug = [r for r in final_rows
                        if r["split"] in ("val", "test") and r["origin"] == "augmented"]
        assert not val_test_aug, "val/test 에 증강본 유입"
        train_orig = sum(1 for r in final_rows
                         if r["split"] == "train" and r["origin"] == "original")
        train_aug = sum(1 for r in final_rows
                        if r["split"] == "train" and r["origin"] == "augmented")
        assert train_orig == len(train_stems)
        assert train_aug > 0, "train 증강본 0"

        # 5) 누수 가드: train ∩ (val ∪ test) = 공집합
        assert guard["train"] > 0 and guard["val"] >= 0 and guard["test"] >= 0

        # 6) 실제 파일이 05 에 물리적으로 존재
        for split_name in ("train", "val", "test"):
            got = sum(len(list(iter_audio_files(paths.split_dir(split_name) / c)))
                      for c in config.CLASSES)
            assert got == sum(final_counts[split_name].values())

        return final_counts, guard


def test_empty_and_ultrashort_clips_skipped():
    """★ 회귀 가드 — PR#10 자체검증 ③ 누락분(빈 waveform).

    실제 버그 재현: 길이 0.0초 빈 wav(규격 16k mono는 통과) + 초단파 클립을
    01_clips 에 심고, preprocess 가 둘 다 skip 해 하류(split/augment/assemble)로
    내려보내지 않으며, augment 의 pink-noise FFT 크래시 없이 05 까지 완주하는지 검증.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = make_dummy_dataset(Path(tmp), per_class=PER_CLASS, seed=1)
        paths = config.resolve_paths(root)
        clips_dir = paths.clips / "fire_alarm"
        # (a) 실제 버그: 길이 0.0초 빈 wav (AI Hub S_103 빈 6개 모사) — frames=0
        save_wav(clips_dir / "fire_alarm_EMPTY.wav", np.zeros(0, dtype=np.float32))
        # (b) 초단파: MIN_SAMPLES 미만(0.05s=800 < 1600) — 경계값 위쪽 방어
        save_wav(clips_dir / "fire_alarm_TINY.wav",
                 np.zeros(int(0.05 * config.SAMPLE_RATE), dtype=np.float32))

        # preprocess 가 두 불량 클립을 skip (크래시 없이). 정상 6개는 전량 통과.
        stats = preprocess.preprocess(paths)
        fa_skipped = {name for name, _ in stats["fire_alarm"]["skipped"]}
        assert "fire_alarm_EMPTY.wav" in fa_skipped, "빈 클립이 preprocess 에서 안 잡힘"
        assert "fire_alarm_TINY.wav" in fa_skipped, "초단파 클립이 preprocess 에서 안 잡힘"
        assert stats["fire_alarm"]["ok"] == PER_CLASS, "정상 클립이 잘못 버려짐(회귀)"
        assert len(stats["fire_alarm"]["skipped"]) == 2

        # 하류 관통 — 여기서 예전엔 augment np.fft.rfft(길이 0) 크래시했음.
        split.split_dataset(paths)
        augment.augment(paths)
        assemble.assemble(paths)
        guard = assert_no_leakage(assemble.load_final_manifest(paths))

        # 불량 stem 이 02/05 어디에도 없어야 함
        pre_stems = {p.stem for p in iter_audio_files(paths.preprocessed / "fire_alarm")}
        assert not ({"fire_alarm_EMPTY", "fire_alarm_TINY"} & pre_stems)
        final_stems = {r["source_stem"] for r in assemble.load_final_manifest(paths)}
        assert not ({"fire_alarm_EMPTY", "fire_alarm_TINY"} & final_stems)

        # 개수 변동 후에도 누수 가드 통과(train ∩ val/test = 공집합)
        assert guard["train"] > 0
        return stats, guard


def test_stale_preprocessed_empty_cleaned_before_write():
    """★ 회귀 가드 — 실측 크래시 근본원인: 02 stale 빈 클립이 05 로 부활.

    실측 오진단 교정: split 은 이미 02 를 읽고 있었음(01 아님). 진짜 원인은 preprocess
    가 02 를 auto-clean 하지 않아, 가드 도입 전(PR#10) 02 로 흘러든 빈 클립이 재실행에도
    남아(02=1642 신규+6 stale=1648) split→05 로 부활 → data.py 빈 waveform 크래시.

    시나리오 재현:
      (1) 정상 더미 6개(01) + 01 에 빈 클립 1개(preprocess 가 skip).
      (2) '가드 이전 실행' 모사 — 02_preprocessed/fire_alarm 에 빈 클립을 직접 심음(stale).
      (3) preprocess(clean=True) 재실행 → 02 stale 이 지워지고 정상 6개만 남는지.
      (4) 전관통 → 빈 stem 이 05 어디에도 없는지(부활 0) assert.
    """
    STALE = "S-211104_S_103_C_006_0001_0039000"  # 실측 크래시 파일 stem(빈 waveform)
    with tempfile.TemporaryDirectory() as tmp:
        root = make_dummy_dataset(Path(tmp), per_class=PER_CLASS, seed=1)
        paths = config.resolve_paths(root)

        # (1) 01_clips 에도 동일 빈 클립 존재(preprocess 가 frames<MIN 으로 skip) — 실측 모사
        save_wav(paths.clips / "fire_alarm" / f"{STALE}.wav", np.zeros(0, dtype=np.float32))
        # (2) '가드 이전 실행' 이 02 에 남긴 stale 빈 클립을 직접 심음(preprocess 우회)
        save_wav(paths.preprocessed / "fire_alarm" / f"{STALE}.wav",
                 np.zeros(0, dtype=np.float32))
        # 다른 클래스에도 stale 산출물 하나 — clean 이 클래스별로 도는지 확인
        save_wav(paths.preprocessed / "knock" / "knock_STALE.wav",
                 np.zeros(0, dtype=np.float32))
        assert (paths.preprocessed / "fire_alarm" / f"{STALE}.wav").exists()

        # (3) preprocess 재실행(clean 기본 True) → 02 stale 제거 후 정상만 재기록
        stats = preprocess.preprocess(paths)
        assert stats["fire_alarm"]["ok"] == PER_CLASS, "정상 클립 손실(회귀)"
        # 빈 클립은 01→02 write 에서 skip + 02 stale 은 auto-clean 으로 제거 = 02 엔 없음
        assert f"{STALE}.wav" in {n for n, _ in stats["fire_alarm"]["skipped"]}
        pre_stems = {p.stem for p in iter_audio_files(paths.preprocessed / "fire_alarm")}
        assert STALE not in pre_stems, "02 stale 빈 클립이 auto-clean 되지 않음"
        assert len(pre_stems) == PER_CLASS, f"02 개수 {len(pre_stems)}≠{PER_CLASS}(stale 잔존)"
        assert "knock_STALE" not in {p.stem for p in iter_audio_files(paths.preprocessed / "knock")}

        # (4) 전관통 → 빈 stem 이 05·manifest 어디에도 도달 못함(부활 0)
        split.split_dataset(paths)
        augment.augment(paths)
        assemble.assemble(paths)
        guard = assert_no_leakage(assemble.load_final_manifest(paths))

        split_stems = {r["stem"] for r in split.load_split_manifest(paths)}
        assert STALE not in split_stems, "빈 클립이 split manifest 로 부활"
        final = assemble.load_final_manifest(paths)
        assert STALE not in {r["source_stem"] for r in final}, "빈 클립이 05 manifest 로 부활"
        for split_name in ("train", "val", "test"):
            disk = {p.stem for c in config.CLASSES
                    for p in iter_audio_files(paths.split_dir(split_name) / c)}
            assert STALE not in disk, f"빈 클립이 05/{split_name} 물리 파일로 부활"
        assert guard["train"] > 0
        return stats, guard


def test_no_clean_preserves_stale():
    """--no-clean(clean=False) 는 stale 을 보존(opt-out 계약 명시). 기본 경로와 대비 고정."""
    with tempfile.TemporaryDirectory() as tmp:
        root = make_dummy_dataset(Path(tmp), per_class=PER_CLASS, seed=1)
        paths = config.resolve_paths(root)
        save_wav(paths.preprocessed / "doorbell" / "doorbell_STALE.wav",
                 np.full(config.SAMPLE_RATE // 2, 0.1, dtype=np.float32))  # 유효 길이 stale
        preprocess.preprocess(paths, clean=False)
        stems = {p.stem for p in iter_audio_files(paths.preprocessed / "doorbell")}
        assert "doorbell_STALE" in stems, "--no-clean 인데 stale 이 지워짐(계약 위반)"


def _make_piece_dataset(
    root: Path, sources_per_class: int = 4, pieces_per_source: int = 3, seed: int = 7
) -> Path:
    """원본(source) 1개당 조각(piece) N개 구조의 더미 생성.

    파일명 = f"{cls}_src{s:02d}_30.0_40.0_{idx:07d}.wav" — 조각 인덱스는 맨 끝 7자리
    (_0000000/_0003000/_0006000). 중간에 점(.) 든 좌표(_30.0_40.0)를 넣어 실데이터
    (AudioSet)와 source_key 파싱(끝 앵커·Path 함정)을 관통 검증.
    """
    rng = np.random.default_rng(seed)
    freq = {"doorbell": 880.0, "knock": 220.0, "fire_alarm": 3000.0, "other": 1500.0}
    paths = config.resolve_paths(root)
    for cls in config.CLASSES:
        for s in range(sources_per_class):
            skey = f"{cls}_src{s:02d}_30.0_40.0"
            for p in range(pieces_per_source):
                dur = 0.6 + 0.3 * float(rng.random())
                n = int(dur * config.SAMPLE_RATE)
                t = np.arange(n) / config.SAMPLE_RATE
                y = (0.6 * np.sin(2 * np.pi * freq[cls] * t)
                     + 0.05 * rng.standard_normal(n)).astype(np.float32)
                idx = p * 3000  # 0/3000/6000 → _0000000/_0003000/_0006000
                save_wav(paths.clips / cls / f"{skey}_{idx:07d}.wav", y)
    return root


def test_source_group_split_no_scatter():
    """★ 회귀 가드 — data leakage fix: 원본(source) 단위 그룹 분할.

    같은 원본의 조각 3개가 절대 쪼개지지 않고 한 split 에 통째 들어가는지 +
    split 조기 무결성 assert + 05 완주 + stem 누수가드 통과를 검증.
    """
    SPC, PPS = 4, 3  # sources_per_class, pieces_per_source
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_piece_dataset(Path(tmp), sources_per_class=SPC, pieces_per_source=PPS)
        paths, final_counts, guard = _run_pipeline(root)

        rows = split.load_split_manifest(paths)

        # 1) source_key 컬럼 존재 + 파싱 정확(맨 끝 7자리만 제거, 점/앵커 보존)
        for r in rows:
            assert r["source_key"] == config.source_key(r["stem"])
            assert r["source_key"] + "_" in r["stem"] + "_"  # source_key 는 stem 의 접두
        # 대표 매핑 직접 확인
        assert config.source_key("doorbell_src00_30.0_40.0_0003000") == \
            "doorbell_src00_30.0_40.0"

        # 2) ★ 핵심: 어떤 (class, source) 도 2개 이상 split 에 흩어지지 않음
        split_of = split.assert_source_integrity(rows)  # 위반 시 SourceSplitError
        # 조각 단위로도 재확인 — source 별 split 집합 == 1
        by_src: dict[tuple[str, str], set[str]] = {}
        for r in rows:
            by_src.setdefault((r["class"], r["source_key"]), set()).add(r["split"])
        for key, splits in by_src.items():
            assert len(splits) == 1, f"source {key} 가 여러 split 에 흩어짐: {splits}"

        # 3) 클래스별 source 개수 == SPC, 조각 총 개수 == SPC*PPS
        for cls in config.CLASSES:
            cls_srcs = {r["source_key"] for r in rows if r["class"] == cls}
            cls_clips = [r for r in rows if r["class"] == cls]
            assert len(cls_srcs) == SPC, f"{cls} source 개수"
            assert len(cls_clips) == SPC * PPS, f"{cls} 조각 총 개수"
            # 각 source 는 정확히 PPS 조각
            for sk in cls_srcs:
                n_pieces = sum(1 for r in cls_clips if r["source_key"] == sk)
                assert n_pieces == PPS, f"{sk} 조각 수 {n_pieces}≠{PPS}"

        # 4) train source 집합 ∩ (val∪test source 집합) = 공집합 (Step 4 의미 직접 확인)
        train_src = {k for k, s in split_of.items() if s == "train"}
        holdout_src = {k for k, s in split_of.items() if s != "train"}
        assert not (train_src & holdout_src), "train source 가 holdout 과 겹침"

        # 5) 증강은 train 조각에만 — holdout stem 은 03 에 없음(누수 0)
        train_stems = {r["stem"] for r in rows if r["split"] == "train"}
        holdout_stems = {r["stem"] for r in rows if r["split"] != "train"}
        aug_base = set()
        for cls in config.CLASSES:
            for a in iter_audio_files(paths.augmented / cls):
                aug_base.add(augment.base_stem(a.name))
        assert aug_base <= train_stems, "train 밖 조각이 증강됨"
        assert not (aug_base & holdout_stems), "val/test 조각이 증강됨(누수)"

        # 6) 05 완주 + stem 누수가드 통과(이중)
        assert guard["train"] > 0 and guard["val"] >= 0 and guard["test"] >= 0
        return final_counts, guard, len(by_src)


# ──────────────────────────────────────────────────────────────────────────
# D1·D2·D3 — 내용 중복 제거 / 해시 고정 배정 / 직접녹음 유닛 키
# ──────────────────────────────────────────────────────────────────────────

def _tone(seed: int, sec: float = 0.5) -> np.ndarray:
    """서로 다른 seed → 서로 다른 내용(md5)."""
    rng = np.random.default_rng(seed)
    n = int(sec * config.SAMPLE_RATE)
    return (0.3 * rng.standard_normal(n)).astype(np.float32)


def _put_pre(paths, cls: str, stem: str, y: np.ndarray) -> None:
    """02_preprocessed 에 직접 심는다(split 단계만 겨냥 — preprocess 우회)."""
    save_wav(paths.preprocessed / cls / f"{stem}.wav", y)


def _split_only(tmp: Path, plant) -> tuple:
    """tempdir + 명시 인자로 split 단계만 실행. 반환: (paths, split rows, dedup rows)."""
    paths = config.resolve_paths(tmp)
    plant(paths)
    split.split_dataset(paths)
    return paths, split.load_split_manifest(paths), split.load_dedup_manifest(paths)


def test_dedup_same_class_duplicate_keeps_one():
    """T1 — 같은 클래스 안 내용 중복은 정렬상 첫 stem 1개만 남고 사유가 기록된다."""
    dup = _tone(1)
    with tempfile.TemporaryDirectory() as tmp:
        def plant(paths):
            for stem in ("doorbell_a_0000000", "doorbell_b_0000000", "doorbell_c_0000000"):
                _put_pre(paths, "doorbell", stem, dup)      # 3개 전부 같은 내용
            _put_pre(paths, "doorbell", "doorbell_z_0000000", _tone(2))
            _put_pre(paths, "knock", "knock_a_0000000", _tone(3))
            _put_pre(paths, "fire_alarm", "fire_alarm_a_0000000", _tone(4))

        _, rows, dropped = _split_only(Path(tmp), plant)
        kept = sorted(r["stem"] for r in rows if r["class"] == "doorbell")
        assert kept == ["doorbell_a_0000000", "doorbell_z_0000000"], kept
        reasons = {r["stem"]: r for r in dropped}
        assert set(reasons) == {"doorbell_b_0000000", "doorbell_c_0000000"}
        for r in reasons.values():
            assert r["reason"] == split.REASON_SAME_CLASS_DUP
            assert r["kept_stem"] == "doorbell_a_0000000"   # 어느 것이 살았는지까지 기록
            assert r["md5"] and r["class"] == "doorbell"
        return kept, dropped


def test_dedup_digital_silence_removed():
    """T2 — 디코딩 샘플 전부 0(디지털 무음)은 제거된다."""
    silence = np.zeros(int(0.5 * config.SAMPLE_RATE), dtype=np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        def plant(paths):
            _put_pre(paths, "doorbell", "doorbell_SILENT_0000000", silence)
            _put_pre(paths, "doorbell", "doorbell_ok_0000000", _tone(5))
            _put_pre(paths, "knock", "knock_ok_0000000", _tone(6))
            _put_pre(paths, "fire_alarm", "fire_alarm_ok_0000000", _tone(7))

        _, rows, dropped = _split_only(Path(tmp), plant)
        assert "doorbell_SILENT_0000000" not in {r["stem"] for r in rows}
        assert [r["reason"] for r in dropped if r["stem"] == "doorbell_SILENT_0000000"] \
            == [split.REASON_SILENCE]
        # 무음은 「유지본 1개」가 없다 — kept_stem 은 비어 있어야 한다.
        assert all(r["kept_stem"] == "" for r in dropped)
        return rows, dropped


def test_dedup_class_cross_removes_both_sides():
    """T3 — 같은 내용이 2개 클래스 폴더에 있으면 **양쪽 모두** 제거(한쪽 유지 아님)."""
    shared = _tone(8)
    with tempfile.TemporaryDirectory() as tmp:
        def plant(paths):
            _put_pre(paths, "doorbell", "cross_src_0000000", shared)
            _put_pre(paths, "fire_alarm", "cross_src_0000000", shared)
            _put_pre(paths, "doorbell", "doorbell_ok_0000000", _tone(9))
            _put_pre(paths, "knock", "knock_ok_0000000", _tone(10))
            _put_pre(paths, "fire_alarm", "fire_alarm_ok_0000000", _tone(11))

        _, rows, dropped = _split_only(Path(tmp), plant)
        assert "cross_src_0000000" not in {r["stem"] for r in rows}, "교차분이 한쪽이라도 살아남음"
        crossed = [r for r in dropped if r["stem"] == "cross_src_0000000"]
        assert len(crossed) == 2, f"교차 제거 {len(crossed)}건 — 양쪽 모두여야 한다"
        assert {r["class"] for r in crossed} == {"doorbell", "fire_alarm"}
        assert all(r["reason"] == split.REASON_CLASS_CROSS for r in crossed)
        return rows, dropped


def _assignments(paths) -> dict:
    return {(r["class"], r["source_key"]): r["split"] for r in split.load_split_manifest(paths)}


def test_new_source_does_not_move_existing_assignments():
    """T4 ★ 안정성 — doorbell 에 source 1개를 더해도 **기존 모든 클래스의 기존 배정 불변**.

    기각된 설계(클래스 공유 random.Random(SEED) + shuffle)에서는 doorbell source 1개
    추가가 knock 클립 124/714 를 흔들었다(decisions.md 5.2(c) 실측).
    """
    def plant_base(paths):
        for ci, cls in enumerate(config.CLASSES):
            for i in range(8):
                for k in range(2):
                    _put_pre(paths, cls, f"{cls}_src{i:02d}_30.0_40.0_{k*3000:07d}",
                             _tone(1000 + 100 * ci + 10 * i + k))

    with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
        paths_a, _, _ = _split_only(Path(tmp_a), plant_base)
        before = _assignments(paths_a)

        def plant_plus(paths):
            plant_base(paths)
            for k in range(2):
                _put_pre(paths, "doorbell", f"doorbell_srcNEW_30.0_40.0_{k*3000:07d}",
                         _tone(999_001 + k))

        paths_b, _, _ = _split_only(Path(tmp_b), plant_plus)
        after = _assignments(paths_b)

        moved = {k: (before[k], after[k]) for k in before if after.get(k) != before[k]}
        assert not moved, f"새 source 추가로 기존 배정이 바뀜: {sorted(moved)[:5]}"
        assert set(after) - set(before) == {("doorbell", "doorbell_srcNEW_30.0_40.0")}
        return len(before), len(after)


def test_direct_recording_unit_group_key():
    """T5 — direct_doorbell_A_01 · _A_02 · _B_01 → 유닛 A 2개 · B 1개(테이크는 같은 그룹)."""
    assert config.source_key("direct_doorbell_A_01") == "direct_doorbell_A"
    assert config.source_key("direct_doorbell_A_02") == "direct_doorbell_A"
    assert config.source_key("direct_doorbell_B_01") == "direct_doorbell_B"
    # 조각 suffix 가 붙어도 유닛으로 접힌다(조각 → 테이크 순서로 1회씩).
    assert config.source_key("direct_doorbell_A_01_0003000") == "direct_doorbell_A"
    # 클래스명 underscore(fire_alarm) 견고성
    assert config.source_key("direct_fire_alarm_C_10") == "direct_fire_alarm_C"
    # 공개데이터 stem 은 이 분기를 타지 않는다(기존 규칙 무변경)
    assert config.source_key("doorbell_src00_30.0_40.0_0003000") == "doorbell_src00_30.0_40.0"

    # dtw_doorbell 의 unit_id() 와 같은 결과(양쪽 규칙 고정 — 그쪽은 파일명, 여기는 stem)
    from ml.experiments.dtw_doorbell.experiment import group_key as dtw_group_key
    for stem in ("direct_doorbell_A_01", "direct_doorbell_A_02", "direct_doorbell_B_01",
                 "direct_fire_alarm_C_10"):
        assert config.source_key(stem) == dtw_group_key(f"{stem}.wav"), stem

    with tempfile.TemporaryDirectory() as tmp:
        def plant(paths):
            for stem, seed in (("direct_doorbell_A_01", 21), ("direct_doorbell_A_02", 22),
                               ("direct_doorbell_B_01", 23)):
                _put_pre(paths, "doorbell", stem, _tone(seed))
            _put_pre(paths, "knock", "knock_ok_0000000", _tone(24))
            _put_pre(paths, "fire_alarm", "fire_alarm_ok_0000000", _tone(25))

        _, rows, _ = _split_only(Path(tmp), plant)
        groups: dict[str, list[str]] = {}
        for r in rows:
            if r["class"] == "doorbell":
                groups.setdefault(r["source_key"], []).append(r["stem"])
        assert set(groups) == {"direct_doorbell_A", "direct_doorbell_B"}, groups
        assert len(groups["direct_doorbell_A"]) == 2 and len(groups["direct_doorbell_B"]) == 1
        # 유닛 A 의 두 테이크는 같은 split (그룹 분할의 실제 효과)
        a_splits = {r["split"] for r in rows if r["source_key"] == "direct_doorbell_A"}
        assert len(a_splits) == 1, a_splits
        return groups


def test_content_leakage_guard_catches_cross_split_content():
    """T6 — 같은 내용 해시가 두 split 에 있으면 내용 가드가 즉시 실패시킨다."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        same = _tone(31)
        a = root / "train" / "x.wav"
        b = root / "test" / "y.wav"          # 이름은 달라도 내용이 같다 = stem 가드 사각지대
        save_wav(a, same)
        save_wav(b, same)
        rows = [
            {"filepath": str(a), "class": "doorbell", "split": "train",
             "origin": "original", "source_stem": "x"},
            {"filepath": str(b), "class": "doorbell", "split": "test",
             "origin": "original", "source_stem": "y"},
        ]
        # 기존 stem 가드는 통과한다 — 그래서 내용 가드가 따로 필요하다.
        assert_no_leakage(rows)
        try:
            assert_no_content_leakage(rows)
        except ContentLeakageError as exc:
            msg = str(exc)
            assert "train" in msg and "test" in msg and "x" in msg and "y" in msg
            assert len([t for t in msg.split() if len(t) == 32 and all(
                c in "0123456789abcdef" for c in t)]) >= 1, "예외 메시지에 해시가 없음"
        else:
            raise AssertionError("내용 누수를 못 잡았다")

        # 같은 split 안이면 통과(가드가 과잉 검출하지 않는지 — 대조군)
        rows[1]["split"] = "train"
        counts = assert_no_content_leakage(rows)
        assert counts["train"] == 1 and counts["test"] == 0
        return counts


def test_split_is_reproducible():
    """T7 — 같은 입력으로 2회 실행하면 split·dedup manifest 가 완전히 동일하다."""
    def plant(paths):
        dup = _tone(41)
        for ci, cls in enumerate(config.CLASSES):
            for i in range(6):
                _put_pre(paths, cls, f"{cls}_src{i:02d}_0000000", _tone(500 + 10 * ci + i))
        _put_pre(paths, "knock", "knock_dupA_0000000", dup)
        _put_pre(paths, "knock", "knock_dupB_0000000", dup)

    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        _, rows1, drop1 = _split_only(Path(t1), plant)
        _, rows2, drop2 = _split_only(Path(t2), plant)
        key1 = sorted((r["class"], r["stem"], r["split"], r["source_key"]) for r in rows1)
        key2 = sorted((r["class"], r["stem"], r["split"], r["source_key"]) for r in rows2)
        assert key1 == key2, "동일 입력 2회 실행 결과가 다름"
        assert sorted((r["class"], r["stem"], r["reason"]) for r in drop1) == \
            sorted((r["class"], r["stem"], r["reason"]) for r in drop2)
        assert len(drop1) == 1 and drop1[0]["reason"] == split.REASON_SAME_CLASS_DUP
        return len(rows1), len(drop1)


def test_aihub_intro_pieces_excluded():
    """T8 — AI Hub 화재 앞머리 멘트 조각(시작 9000ms 미만)은 제외, 사유 = aihub_intro_speech.

    순서(무음 → 멘트 → 교차 → 중복)는 사유 라벨로만 드러나므로 개수가 아니라 사유를 단언한다.
    """
    rec_a, rec_b = "S-211107_S_103_C_013_0001", "S-211014_S_103_C_360_0001"
    intro = _tone(61)                               # 두 녹음의 0ms 조각이 바이트 동일(33.7(g))
    silence = np.zeros(int(0.5 * config.SAMPLE_RATE), dtype=np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        def plant(paths):
            for ms in (0, 3000, 6000, 9000):
                _put_pre(paths, "fire_alarm", f"{rec_a}_{ms:07d}",
                         intro if ms == 0 else _tone(62 + ms))
            _put_pre(paths, "fire_alarm", f"{rec_b}_0000000", intro)
            _put_pre(paths, "fire_alarm", f"{rec_b}_0003000", silence)   # 무음이 먼저
            _put_pre(paths, "fire_alarm", "S-211107_S_103_C_099_0001", _tone(71))  # suffix 없음
            _put_pre(paths, "fire_alarm", "fire_alarm_web_0000000", _tone(72))   # 비 AI Hub
            _put_pre(paths, "doorbell", f"{rec_a}_0000000", _tone(73))   # 대상 클래스 아님
            _put_pre(paths, "knock", "knock_ok_0000000", _tone(74))

        _, rows, dropped = _split_only(Path(tmp), plant)
        kept = {(r["class"], r["stem"]) for r in rows}
        reason = {(r["class"], r["stem"]): r["reason"] for r in dropped}
        intro_key = split.REASON_AIHUB_INTRO
        assert reason == {
            ("fire_alarm", f"{rec_a}_0000000"): intro_key,
            ("fire_alarm", f"{rec_a}_0003000"): intro_key,
            ("fire_alarm", f"{rec_a}_0006000"): intro_key,
            ("fire_alarm", f"{rec_b}_0000000"): intro_key,     # same_class_dup 아님
            ("fire_alarm", f"{rec_b}_0003000"): split.REASON_SILENCE,
        }, reason
        assert kept == {
            ("fire_alarm", f"{rec_a}_0009000"),
            ("fire_alarm", "S-211107_S_103_C_099_0001"),
            ("fire_alarm", "fire_alarm_web_0000000"),
            ("doorbell", f"{rec_a}_0000000"),
            ("knock", "knock_ok_0000000"),
        }, kept
        assert all(r["kept_stem"] == "" for r in dropped)
        return len(rows), len(dropped)


def test_pitch_markers_per_class():
    """T9 — pitch 마커는 초인종·노크 직접녹음만(33.3① 규격 화재음 왜곡 회피 · 5.3(b))."""
    assert config.PITCH_SHIFT_MODE == "korean_only"
    targets = ("direct_doorbell_home_01_0000000", "direct_knock_a_03_0003000")
    others = ("direct_fire_alarm_x_01_0000000", "S-211107_S_103_C_013_0001_0000000",
              "176226_0000000")
    for stem in targets:
        assert augment._pitch_targets(stem) == list(config.PITCH_SHIFT_SEMITONES), stem
    for stem in others:
        assert augment._pitch_targets(stem) == [], stem
    return len(targets), len(others)


def test_zeroth_speaker_group_key():
    """T10 — Zeroth 조각은 화자 단위로 묶인다(발화마다 갈리면 같은 화자가 train·test 로 누수)."""
    stems = ("zeroth_106_003_0077_0000000", "zeroth_106_003_0098_0003000",
             "zeroth_106_004_0001_0000000", "zeroth_106_003_0077")
    for stem in stems:
        assert config.source_key(stem) == "zeroth_106", stem
    assert config.source_key("zeroth_107_003_0077_0000000") == "zeroth_107"
    # 접두가 zeroth_ 가 아니면 이 분기를 타지 않는다(기존 규칙 무변경)
    for stem, key in (("106_003_0077_0000000", "106_003_0077"),
                      ("xzeroth_106_003_0077_0000000", "xzeroth_106_003_0077"),
                      ("S-211107_S_103_C_013_0001_0000000", "S-211107_S_103_C_013_0001"),
                      ("direct_doorbell_A_01_0003000", "direct_doorbell_A")):
        assert config.source_key(stem) == key, stem

    with tempfile.TemporaryDirectory() as tmp:
        def plant(paths):
            for stem, seed in (("zeroth_106_003_0077_0000000", 41),
                               ("zeroth_106_003_0098_0000000", 42),
                               ("zeroth_107_003_0011_0000000", 43)):
                _put_pre(paths, "knock", stem, _tone(seed))
            _put_pre(paths, "doorbell", "doorbell_ok_0000000", _tone(44))
            _put_pre(paths, "fire_alarm", "fire_alarm_ok_0000000", _tone(45))

        _, rows, _ = _split_only(Path(tmp), plant)
        keys = {r["stem"]: r["source_key"] for r in rows if r["class"] == "knock"}
        assert set(keys.values()) == {"zeroth_106", "zeroth_107"}, keys
        splits = {r["split"] for r in rows if r["source_key"] == "zeroth_106"}
        assert len(splits) == 1, splits
    return len(stems) + 1


def test_boardbg_unit_group_key():
    """T11 — 보드 배경 조각은 유닛 단위로 묶인다(테이크마다 갈리면 같은 보드 잡음이 train·test 로 누수)."""
    stems = ("boardbg_home_03_0000000", "boardbg_home_04_0000000", "boardbg_home_123_0003000",
             "boardbg_home_03")
    for stem in stems:
        assert config.source_key(stem) == "boardbg_home", stem
    assert config.source_key("boardbg_bg2_01_0000000") == "boardbg_bg2"
    # 대표 stem(공개데이터 3계열 · direct_ · zeroth_ · 접두 불일치) — 기존 키 불변
    for stem, key in (("100634_0000000", "100634"),
                      ("S-211107_S_103_C_015_0001_0003000", "S-211107_S_103_C_015_0001"),
                      ("_Uf47SnKl5Q_30.0_40.0_0003000", "_Uf47SnKl5Q_30.0_40.0"),
                      ("direct_doorbell_home_01_0001000", "direct_doorbell_home"),
                      ("zeroth_106_003_0077_0000000", "zeroth_106"),
                      ("xboardbg_home_03_0000000", "xboardbg_home_03")):
        assert config.source_key(stem) == key, stem
    return len(stems) + 1


def test_other_snr_lookup():
    """T12 — 결정 D-b: other 증강 SNR = 초인종·노크와 같은 (10, 20). other 는 CLASSES 편입 클래스."""
    assert "other" in config.CLASSES
    assert config.BG_NOISE_SNR_DB["other"] == config.BG_NOISE_SNR_DB["knock"] == (10.0, 20.0)
    out = augment._augment_one(_tone(46), "other", "boardbg_home_01_0000000")
    assert {"snr10", "snr20"} <= set(out), sorted(out)
    return sorted(out)


def test_class_order_server_contract():
    """T13 — 서버 계약 순서: 0·1·2 불변(doorbell/knock/fire_alarm), other = 3(33.13(d) 끝에 추가)."""
    assert config.CLASSES[:3] == ("doorbell", "knock", "fire_alarm"), config.CLASSES
    assert config.CLASSES[3] == "other" and len(config.CLASSES) == 4, config.CLASSES
    return config.CLASSES


def test_dummy_class_freq_distinct():
    """T14 — 더미 클래스 분리 가능: 클래스마다 대표 주파수가 달라야 한다(같으면 KeyError 없이 학습만 흐려진다)."""
    freqs = [make_dummy._CLASS_FREQ[c] for c in config.CLASSES]
    assert len(set(freqs)) == len(freqs), dict(zip(config.CLASSES, freqs))
    return dict(zip(config.CLASSES, freqs))


def _main() -> int:
    counts, guard = test_pipeline_end_to_end()
    print("PASS — test_pipeline_end_to_end")
    scounts, sguard, n_src = test_source_group_split_no_scatter()
    print(f"PASS — test_source_group_split_no_scatter (원본 {n_src}개, 미분할·누수0)")
    for split_name in ("train", "val", "test"):
        row = scounts[split_name]
        print(f"  {split_name:<5} " + " ".join(f"{c}={row[c]}" for c in config.CLASSES)
              + f"  total={sum(row.values())}")
    stats, eguard = test_empty_and_ultrashort_clips_skipped()
    fa = stats["fire_alarm"]
    print("PASS — test_empty_and_ultrashort_clips_skipped")
    print(f"  fire_alarm: ok={fa['ok']} skipped={len(fa['skipped'])} "
          f"({', '.join(n for n, _ in fa['skipped'])})")
    sstats, _ = test_stale_preprocessed_empty_cleaned_before_write()
    print("PASS — test_stale_preprocessed_empty_cleaned_before_write")
    print(f"  02 stale 빈클립 auto-clean → 05 부활 0 (fire_alarm ok={sstats['fire_alarm']['ok']})")
    test_no_clean_preserves_stale()
    print("PASS — test_no_clean_preserves_stale (--no-clean 는 stale 보존)")
    kept, dropped = test_dedup_same_class_duplicate_keeps_one()
    print(f"PASS — T1 test_dedup_same_class_duplicate_keeps_one (유지 {kept}, 제거 {len(dropped)})")
    test_dedup_digital_silence_removed()
    print("PASS — T2 test_dedup_digital_silence_removed")
    test_dedup_class_cross_removes_both_sides()
    print("PASS — T3 test_dedup_class_cross_removes_both_sides (양쪽 제거)")
    n_before, n_after = test_new_source_does_not_move_existing_assignments()
    print(f"PASS — T4 test_new_source_does_not_move_existing_assignments "
          f"(기존 {n_before} source 배정 변경 0, 신규 +{n_after - n_before})")
    groups = test_direct_recording_unit_group_key()
    print(f"PASS — T5 test_direct_recording_unit_group_key "
          f"(유닛 { {k: len(v) for k, v in sorted(groups.items())} })")
    test_content_leakage_guard_catches_cross_split_content()
    print("PASS — T6 test_content_leakage_guard_catches_cross_split_content")
    n_rows, n_drop = test_split_is_reproducible()
    print(f"PASS — T7 test_split_is_reproducible (2회 동일: {n_rows} rows / 제거 {n_drop})")
    n_rows, n_drop = test_aihub_intro_pieces_excluded()
    print(f"PASS — T8 test_aihub_intro_pieces_excluded (유지 {n_rows} / 제거 {n_drop})")
    n_t, n_o = test_pitch_markers_per_class()
    print(f"PASS — T9 test_pitch_markers_per_class (대상 {n_t} / 비대상 {n_o})")
    n_z = test_zeroth_speaker_group_key()
    print(f"PASS — T10 test_zeroth_speaker_group_key (zeroth stem {n_z} → 화자 키)")
    n_b = test_boardbg_unit_group_key()
    print(f"PASS — T11 test_boardbg_unit_group_key (boardbg stem {n_b} → 유닛 키 · 대표 stem 불변)")
    tags = test_other_snr_lookup()
    print(f"PASS — T12 test_other_snr_lookup (other 증강 태그 {tags})")
    print(f"PASS — T13 test_class_order_server_contract ({test_class_order_server_contract()})")
    print(f"PASS — T14 test_dummy_class_freq_distinct ({test_dummy_class_freq_distinct()})")
    for split_name in ("train", "val", "test"):
        row = counts[split_name]
        print(f"  {split_name:<5} " + " ".join(f"{c}={row[c]}" for c in config.CLASSES)
              + f"  total={sum(row.values())}")
    print(f"  누수가드 stem: train={guard['train']} val={guard['val']} test={guard['test']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
