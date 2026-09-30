"""클래스 집합 명시 · 산출 폴더 필수 · 덮어쓰기 거부 · 빈 클래스 즉시 실패 · 실행별 라벨 · early stop patience
· 정규화 규칙 계보(02 기록 → 05 → train_config.json peak_rule).

05_final_dataset 을 tempdir 에 직접 만들고(파이프라인 생략) 더미 embed_fn · 더미 YAMNet 으로
train → evaluate → export 를 관통한다. 실데이터 · hub · 서빙 모델 폴더 무접촉.

  python -m ml.training.tests.test_class_subset
  pytest ml/training/tests/test_class_subset.py
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from ml.pipeline import audio_io, preprocess, run_all
from ml.pipeline import config as pipe
from ml.pipeline.make_dummy import make_dummy_dataset
from ml.training import config, data, evaluate, export, train
from ml.training.tests.test_export_smoke import _load_dummy_yamnet
from ml.training.tests.test_training_smoke import PER_CLASS, dummy_embed_fn

WITH_OTHER = config.CLASSES                    # 4클래스 경로 — other 편입(33.13(d)) 후 전역 CLASSES 그대로
THREE = ("doorbell", "knock", "fire_alarm")    # other 가 없는 허용 집합 — 집합 밖 이름 거부 확인용
_FREQ = {"doorbell": 880.0, "knock": 120.0, "fire_alarm": 3000.0, "other": 440.0}


def _make_final(root: Path, classes, per=3, empty: tuple[str, str] | None = None) -> Path:
    """final/{split}/{class}/*.wav 더미. empty=(split, class) 는 폴더만 만들고 비운다."""
    final = root / "05_final_dataset"
    t = np.arange(int(0.5 * config.SAMPLE_RATE)) / config.SAMPLE_RATE
    for split in config.SPLITS:
        for cls in classes:
            d = final / split / cls
            d.mkdir(parents=True, exist_ok=True)
            if (split, cls) == empty:
                continue
            for i in range(per):
                y = (0.3 + 0.1 * i) * np.sin(2 * np.pi * _FREQ[cls] * t)
                audio_io.save_wav(d / f"{cls}_{i}.wav", y.astype(np.float32))
    preprocess.write_norm_rule(final, pipe.PEAK_RULE)  # run_all 이 남기는 규칙 기록(학습 필수 입력)
    return final


def _train(final, out, classes, allowed=config.CLASSES, **kw):
    return train.train(final, out, classes=classes, allowed=allowed, embed_fn=dummy_embed_fn,
                       epochs=1, batch_size=4, export_inference=False, verbose=0, **kw)


def _labels(run: Path) -> dict:
    return json.loads((run / config.LABELS_NAME).read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _raises(exc, fn, *needles):
    try:
        fn()
    except exc as e:
        for n in needles:
            assert n in str(e), f"메시지에 {n!r} 없음: {e}"
        return
    raise AssertionError(f"{exc.__name__} 미발생")


def test_resolve_classes():
    assert config.resolve_classes("doorbell,knock,fire_alarm") == ("doorbell", "knock", "fire_alarm")
    assert config.resolve_classes("fire_alarm,doorbell,knock") == ("doorbell", "knock", "fire_alarm")
    assert config.resolve_classes(["fire_alarm", "doorbell"]) == ("doorbell", "fire_alarm")
    assert config.resolve_classes("other,knock", WITH_OTHER) == ("knock", "other")
    for bad in ("", "doorbell,,knock", "doorbell,siren", "knock,knock", []):
        _raises(ValueError, lambda b=bad: config.resolve_classes(b))
    _raises(ValueError, lambda: config.resolve_classes("other", THREE))   # 허용 집합 밖 other 는 거부
    print("[classes] 정규화 · 거부(빈/모름/중복) OK")


def test_run_dir_required():
    saved = os.environ.pop("DDINGDONG_MODEL_DIR", None)
    try:
        _raises(ValueError, lambda: config.resolve_run_dir(None), "DDINGDONG_MODEL_DIR")
        _raises(ValueError, lambda: config.resolve_run_dir(""))
        os.environ["DDINGDONG_MODEL_DIR"] = "~/x_run"
        assert config.resolve_run_dir(None) == Path("~/x_run").expanduser()
        assert config.resolve_run_dir("/a/b") == Path("/a/b")
    finally:
        os.environ.pop("DDINGDONG_MODEL_DIR", None)
        if saved is not None:
            os.environ["DDINGDONG_MODEL_DIR"] = saved
    print("[run_dir] 미지정 = 실패 · env/인자 해석 OK")


def test_empty_class_fails():
    with tempfile.TemporaryDirectory() as tmp:
        final = _make_final(Path(tmp), config.CLASSES, empty=("val", "knock"))
        _raises(ValueError, lambda: data.list_examples(final, "val", config.CLASSES),
                "split=val", "class=knock", str(final / "val" / "knock"))
        assert len(data.list_examples(final, "train", config.CLASSES)) == 4 * 3
        out = Path(tmp) / "run"
        _raises(ValueError, lambda: _train(final, out, "doorbell,knock,fire_alarm"), "split=val")
        assert not out.exists(), "빈 클래스 실패인데 산출 폴더가 생김(부분 산출물)"
        # knock 을 빼면 같은 데이터로 학습 가능(부분집합은 의도된 제외)
        _train(final, out, "doorbell,fire_alarm")
    _raises(ValueError, lambda: data.compute_class_weights([0, 0, 2], 3), "[1]")
    print("[빈 클래스] list_examples · train · class_weight 즉시 실패 OK")


def test_overwrite_refused():
    with tempfile.TemporaryDirectory() as tmp:
        final = _make_final(Path(tmp), config.CLASSES)
        for name in config.TRAIN_ARTIFACTS + (train.TRAIN_CONFIG_NAME,):
            out = Path(tmp) / f"run_{name}"
            out.mkdir()
            sentinel = out / name
            sentinel.write_bytes(b"sentinel " + name.encode())
            before = _sha(sentinel)
            _raises(FileExistsError, lambda o=out: _train(final, o, config.CLASSES), name)
            assert _sha(sentinel) == before, f"{name} 가 덮어써짐"
            assert sorted(p.name for p in out.iterdir()) == [name], "거부인데 다른 파일이 생김"
        # evaluate · export 도 기존 산출물 거부
        run = Path(tmp) / "run"
        _train(final, run, config.CLASSES)
        evaluate.evaluate(final, run, classes=config.CLASSES, embed_fn=dummy_embed_fn)
        rep = run / config.EVAL_REPORT_NAME
        before = _sha(rep)
        _raises(FileExistsError, lambda: evaluate.evaluate(
            final, run, classes=config.CLASSES, embed_fn=dummy_embed_fn), config.EVAL_REPORT_NAME)
        assert _sha(rep) == before
        (run / config.SAVEDMODEL_NAME).mkdir()
        _raises(FileExistsError, lambda: export.export_savedmodel(
            run, classes=config.CLASSES, yamnet=object()), config.SAVEDMODEL_NAME)
    print("[덮어쓰기] train(체크포인트/labels/savedmodel/train_config) · evaluate · export 거부 + 해시 불변 OK")


def test_three_class_shuffled_order():
    with tempfile.TemporaryDirectory() as tmp:
        final = _make_final(Path(tmp), config.CLASSES)
        run = Path(tmp) / "run"
        s = _train(final, run, "fire_alarm,doorbell,knock")
        lab = _labels(run)
        assert lab["classes"] == ["doorbell", "knock", "fire_alarm"], lab
        assert lab["index"] == {"doorbell": 0, "knock": 1, "fire_alarm": 2}, lab
        assert s["classes"] == lab["classes"]
    print("[3클래스] 뒤섞은 입력 → doorbell 0 · knock 1 · fire_alarm 2 OK")


def test_two_class_subset_through_export():
    import tensorflow as tf

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        final = _make_final(work, config.CLASSES)
        run = work / "run"
        _train(final, run, "fire_alarm,doorbell")
        assert _labels(run)["classes"] == ["doorbell", "fire_alarm"]
        head = tf.keras.models.load_model(str(run / config.CHECKPOINT_NAME))
        assert head.output_shape == (None, 2), head.output_shape

        rep = evaluate.evaluate(final, run, classes="doorbell,fire_alarm", embed_fn=dummy_embed_fn)
        assert set(rep["per_class"]) == {"doorbell", "fire_alarm"}
        assert np.array(rep["confusion"]).shape == (2, 2)

        # run labels.json 과 다른 클래스 인자 → 거부
        _raises(ValueError, lambda: evaluate.evaluate(
            final, run, classes=config.CLASSES, embed_fn=dummy_embed_fn), "클래스 불일치")
        yamnet = _load_dummy_yamnet(work)      # 진짜 더미 — 가드가 없으면 export 가 성공해 버리도록
        _raises(ValueError, lambda: export.export_savedmodel(
            run, classes=config.CLASSES, yamnet=yamnet), "클래스 불일치")
        assert not (run / config.SAVEDMODEL_NAME).exists()
        # --checkpoint 로 다른 run(4클래스) head 를 주면 labels.json(2클래스)과 출력 수 불일치 → 거부
        other = work / "other_run"
        _train(final, other, config.CLASSES)
        _raises(ValueError, lambda: export.export_savedmodel(
            run, classes="doorbell,fire_alarm", checkpoint=other / config.CHECKPOINT_NAME,
            yamnet=yamnet), "head 출력 4")
        assert not (run / config.SAVEDMODEL_NAME).exists()

        summary = export.export_savedmodel(run, classes="doorbell,fire_alarm", yamnet=yamnet)
        assert summary["classes"] == ["doorbell", "fire_alarm"] != list(config.CLASSES), summary
        sig = tf.saved_model.load(summary["savedmodel"]).signatures["serving_default"]
        probs = list(sig(tf.zeros([1, config.SAMPLE_RATE])).values())[0].numpy()
        assert probs.shape == (1, 2), probs.shape
    print("[2클래스] head 2 · labels 2 · evaluate 2x2 · export classes 2 · serving (1,2) OK")


def test_four_class_other_index():
    import tensorflow as tf

    with tempfile.TemporaryDirectory() as tmp:
        final = _make_final(Path(tmp), WITH_OTHER)
        run = Path(tmp) / "run"
        _train(final, run, "other,knock,doorbell,fire_alarm", allowed=WITH_OTHER)
        lab = _labels(run)
        assert lab["classes"] == ["doorbell", "knock", "fire_alarm", "other"], lab
        assert lab["index"]["other"] == 3
        head = tf.keras.models.load_model(str(run / config.CHECKPOINT_NAME))
        assert head.output_shape == (None, 4), head.output_shape
        rep = evaluate.evaluate(final, run, classes=list(WITH_OTHER), allowed=WITH_OTHER,
                                embed_fn=dummy_embed_fn)
        assert rep["per_class"]["other"]["pretrained_baseline_top1"] is None
        assert config.CLASSES == ("doorbell", "knock", "fire_alarm", "other"), "전역 CLASSES 가 바뀜"
    print("[4클래스] head 4 · other=3 · config.CLASSES 4개 유지 OK")


def test_early_stop_patience():
    import tensorflow as tf

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        # CLI → train() 전달: 미지정 = config 값, 15 = 15 (학습은 가로채서 생략)
        seen = []
        orig_train = train.train
        train.train = lambda *a, **kw: seen.append(kw) or {}
        try:
            base = ["--data-root", tmp, "--classes", "doorbell", "--out-dir", str(work / "cli"), "--quiet"]
            train.main(base)
            train.main(base + ["--early-stop-patience", "15"])
        finally:
            train.train = orig_train
        assert [kw["early_stop_patience"] for kw in seen] == [config.EARLY_STOP_PATIENCE, 15], seen

        # train() → EarlyStopping 콜백 patience + train_config.json
        final = _make_final(work, config.CLASSES)
        built = []
        orig_cb = train._callbacks
        train._callbacks = lambda *a, **kw: built.append(orig_cb(*a, **kw)) or built[-1]
        try:
            run = work / "run"
            _train(final, run, "doorbell,knock", early_stop_patience=15)
        finally:
            train._callbacks = orig_cb
        es = [cb for cb in built[0] if isinstance(cb, tf.keras.callbacks.EarlyStopping)]
        assert len(es) == 1 and es[0].patience == 15, es
        cfg = json.loads((run / train.TRAIN_CONFIG_NAME).read_text(encoding="utf-8"))
        assert cfg == {"epochs": 1, "batch_size": 4, "early_stop_patience": 15,
                       "classes": ["doorbell", "knock"], "peak_rule": pipe.PEAK_RULE}, cfg

        # 1 미만 거부 — 쓰기 전에 실패(부분 산출물 0)
        for bad in (0, -1):
            out = work / f"bad_{bad}"
            _raises(ValueError, lambda o=out, b=bad: _train(final, o, "doorbell,knock",
                                                            early_stop_patience=b), str(bad))
            assert not out.exists(), f"patience={bad} 거부인데 산출 폴더가 생김"
    print(f"[patience] CLI 기본 {config.EARLY_STOP_PATIENCE} · 15 전달 · EarlyStopping 15 · "
          "train_config.json · 0/-1 거부 OK")


def test_peak_rule_lineage():
    """02 가 실제로 쓴 규칙 → 05 기록 → train_config.json peak_rule. 기록 없는 02 · 05 는 실패.

    ★ 02 를 config 기본(pipe.PEAK_RULE)과 **다른** 규칙으로 만든다 — 같으면 학습이 config 값을 적어도
      통과해 버린다(NC-3 함정). 클램프 1샘플을 심어 두 규칙의 02 출력이 실제로 갈리는지도 확인.
    """
    other_rule = next(r for r in audio_io.PEAK_RULES if r != pipe.PEAK_RULE)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_dummy_dataset(root, per_class=PER_CLASS, seed=1)
        paths = pipe.resolve_paths(root)
        src = sorted((paths.clips / "doorbell").glob("*.wav"))[0]
        y = audio_io.load_mono(src)
        y[len(y) // 2] = 1.0  # 저장하면 +32767 = 클램프
        audio_io.save_wav(src, y)
        run_all.run(paths, clean=True, rule=other_rule)

        assert preprocess.read_norm_rule(paths.preprocessed) == other_rule
        assert preprocess.read_norm_rule(paths.final) == other_rule
        got = audio_io.load_mono(paths.preprocessed / "doorbell" / src.name)
        raw = audio_io.load_mono(src)
        lsb = 1.5 / 32768
        assert np.max(np.abs(got - audio_io.PEAK_RULES[other_rule](raw))) < lsb, "02 출력 ≠ 기록된 규칙"
        assert np.max(np.abs(got - audio_io.PEAK_RULES[pipe.PEAK_RULE](raw))) > lsb, "두 규칙이 안 갈림"

        run = root / "run"
        _train(paths.final, run, "doorbell,knock")
        cfg = json.loads((run / train.TRAIN_CONFIG_NAME).read_text(encoding="utf-8"))
        assert cfg["peak_rule"] == other_rule != pipe.PEAK_RULE, cfg

        # 기록 없는 05 로 학습 = 쓰기 전에 실패(산출 폴더 생성 0)
        (paths.final / pipe.NORM_RULE_FILE).unlink()
        out = root / "no_record"
        _raises(FileNotFoundError, lambda: _train(paths.final, out, "doorbell,knock"), pipe.NORM_RULE_FILE)
        assert not out.exists()
        # 기록 없는 02 로 조립 = 실패
        (paths.preprocessed / pipe.NORM_RULE_FILE).unlink()
        from ml.pipeline import assemble
        _raises(FileNotFoundError, lambda: assemble.assemble(paths), pipe.NORM_RULE_FILE)
    print(f"[계보] 02 {other_rule} → 05 → train_config peak_rule 일치(config 기본 {pipe.PEAK_RULE} 아님) · "
          "기록 없는 05 학습 · 02 조립 실패 OK")


if __name__ == "__main__":
    test_resolve_classes()
    test_run_dir_required()
    test_empty_class_fails()
    test_overwrite_refused()
    test_three_class_shuffled_order()
    test_two_class_subset_through_export()
    test_four_class_other_index()
    test_early_stop_patience()
    test_peak_rule_lineage()
    print("=== 클래스 집합 · 산출 폴더 전체 통과 (9) ===")
