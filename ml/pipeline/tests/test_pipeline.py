"""Step 6 — 합성 더미 관통 검증 (실제 데이터 EPERM 무관, repo 안에서 실행).

클래스당 6개 더미 16k mono wav 생성 → Step1~5 전관통 → 출력/manifest/개수/누수가드 확인.
pytest 로도, 단독(`python -m ml.pipeline.tests.test_pipeline`)으로도 실행 가능.
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from .. import assemble, augment, config, preprocess, split
from ..audio_io import iter_audio_files, probe
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


def _main() -> int:
    counts, guard = test_pipeline_end_to_end()
    print("PASS — test_pipeline_end_to_end")
    for split_name in ("train", "val", "test"):
        row = counts[split_name]
        print(f"  {split_name:<5} " + " ".join(f"{c}={row[c]}" for c in config.CLASSES)
              + f"  total={sum(row.values())}")
    print(f"  누수가드 stem: train={guard['train']} val={guard['val']} test={guard['test']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
