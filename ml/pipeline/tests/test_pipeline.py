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
from ..guards import assert_no_leakage
from ..make_dummy import make_dummy_dataset

PER_CLASS = 6


def _run_pipeline(root: Path):
    paths = config.resolve_paths(root)
    preprocess.preprocess(paths)
    split.split_dataset(paths)
    augment.augment(paths)
    final_counts = assemble.assemble(paths)
    guard = assert_no_leakage(assemble.load_final_manifest(paths))
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
    freq = {"doorbell": 880.0, "knock": 220.0, "fire_alarm": 3000.0}
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
    for split_name in ("train", "val", "test"):
        row = counts[split_name]
        print(f"  {split_name:<5} " + " ".join(f"{c}={row[c]}" for c in config.CLASSES)
              + f"  total={sum(row.values())}")
    print(f"  누수가드 stem: train={guard['train']} val={guard['val']} test={guard['test']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
