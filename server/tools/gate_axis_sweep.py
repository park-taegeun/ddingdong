#!/usr/bin/env python3
"""게이트 축 전수 스윕 하네스 — held-out test 424건 재현 (계측 계층, 제품 동작 불변).

**성격 = 방법론 자산**(8.4(f) SSR NC 하네스 · 6.3(o) `env:mic_noiseprobe` 계열).
33.6(b)(d)가 일회성 스크립트로 측정하고 repo에 남기지 않은 축
(`pass_ok` / `pass_NG` / `blocked` + `pass_NG` 오분류 대상 내역)을 **재현 가능한 도구**로
고정한다. 임계값·정책·클래스 구성은 **한 줄도 바꾸지 않는다** — `pass_NG` 27건의 대응 방향은
33.6(a)(d)에 「사용자 판단 대기」로 등재된 별건이며 본 하네스는 그 판단을 대신하지 않는다.

**측정 경로**(33.6(b)(d)와 동일): HTTP 미경유. 프로즌 `inference.model_runner.ModelRunner`
(= `tf.saved_model.load` + (1,3) 시그니처 계약 검사)로 직접 추론하고, 전처리는 프로즌
`inference.audio_decode.decode_pcm16`을 **import해서** 쓴다(자체 구현 금지 — 학습 파이프라인과
동일 전처리임을 보장하는 것이 33.6(b) 재현의 핵심). 판정 어휘는 프로즌
`app.model_serving.scores_to_prediction`(2자리 반올림)과 `app.constants.CONFIDENCE_THRESHOLD`
(strict `<`)를 그대로 쓴다. ⇒ `/detect`를 호출하지 않으므로 **카카오톡 발송 경로가 없다.**

**raw / rounded 2열 판정**(33.6(e) 근거): 제품 경로는 `scores_to_prediction`이 confidence를
**2자리 반올림한 뒤** `utils._apply_prediction_policy`의 strict `<` 게이트를 탄다. 33.6(d)
스윕은 SavedModel 원값 기준이었다. 33.6(e)가 "test 424건 전수에서 raw confidence가
`[0.695, 0.70)`에 든 건 **0건**"이라 현재 두 기준의 결과는 같지만 **그건 우연이지 보장이
아니다.** 본 하네스는 두 기준을 **동시에** 산출하고 일치 여부를 스스로 단언한다. 불일치는
실패가 아니라 **결과**이며 종료 코드로 구분된다(EXIT_GATE_DIVERGENCE).

--------------------------------------------------------------------------------
④런타임 절차서 (학부생 몫 — MCP 미수행)
--------------------------------------------------------------------------------
0) 좀비 서버 확인(본 하네스는 HTTP 미경유라 서버가 **필요 없다**. 떠 있으면 혼동만 생긴다):

     lsof -nP -iTCP:5000 -sTCP:LISTEN

1) 자기검증(데이터·모델 없이 수초, negative control 4종 동시 실행):

     cd "/Users/xorms/Desktop/서경대학교/시험 준비/26-1/공학종합설계1/프로젝트/ddingdong/server"
     venv_real/bin/python3 tools/gate_axis_sweep.py --self-test

2) 드라이런(환경변수·매니페스트만 검증. TF 미로드, 추론 0건):

     DDINGDONG_DATA_ROOT="$HOME/ML 학습 데이터/ddingdong_dataset" \
     venv_real/bin/python3 tools/gate_axis_sweep.py --dry-run

3) 전수 스윕(424건, 수 초. `.env` 무변경 — **셸 앞 변수만** 쓴다. 33.6(c) 관용구):

     DDINGDONG_DATA_ROOT="$HOME/ML 학습 데이터/ddingdong_dataset" \
     DDINGDONG_MODEL_PATH="/Users/xorms/Desktop/서경대학교/시험 준비/26-1/공학종합설계1/프로젝트/ddingdong/ml/models/yamnet/inference_savedmodel" \
     venv_real/bin/python3 tools/gate_axis_sweep.py

4) 로그 저장(repo 밖 — 카테고리 실측 로그 규약. repo 안은 `.gitignore` 차단분):

     mkdir -p "$HOME/ddingdong-측정결과/$(date +%F)"
     … 위 3) 명령 … 2>&1 | tee "$HOME/ddingdong-측정결과/$(date +%F)/realmodel_gate_axis_sweep.log"

   메타 헤더에 손으로 적을 것: env(파이썬·TF 버전) / 커밋 해시 / 상수값(임계 0.7 strict `<`) /
   측정 환경(보드 유무·장소) / 프로토콜(HTTP 미경유) / 미수행·한계.

5) 결과 읽는 법:
   - `[실모델 확증]` 3줄 = RSS(KB) / TF 라이브러리 매핑 수 / 동일 입력 2회 출력 일치.
     ★ 이 3축이 mock 반증이다 — 셋 다 보이지 않으면 실모델이 아니다.
   - `[재현 대조]` 줄 = 33.6(b)(d) 기준값과 전건 일치 여부.
   - `[raw vs rounded]` 줄 = 두 게이트 기준의 분류 일치 여부(33.6(e)).
   - 종료 코드: 0 전건 일치 / 1 재현 불일치 / 2 raw↔rounded 불일치(결과이지 실패 아님) /
     3 환경·입력 오류 / 4 라벨 순서 불일치.
   - 소요: 424건 수 초(33.6(b) 실측 2.2초 + 모델 로드 ~4초).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import wave
from collections import Counter
from pathlib import Path

# 이 파일은 `server/tools/` 에 있고 프로즌 `app` · `inference` 패키지는 `server/` 직하위다.
# 실행 관용구가 `cd server && venv_real/bin/python3 tools/...` 이므로 sys.path[0] 은 tools/ 가
# 된다 → 상위(server/)를 명시적으로 얹는다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.constants import CONFIDENCE_THRESHOLD, PREDICTED_CLASSES  # noqa: E402
from app.model_serving import scores_to_prediction  # noqa: E402
from inference.audio_decode import decode_pcm16  # noqa: E402
from inference.constants import SAMPLE_RATE  # noqa: E402

# ── 게이트 축 어휘 (33.6(b) 신설 축) ────────────────────────────────────────
AXIS_OK = "pass_ok"        # 게이트 통과 + 예측 일치
AXIS_NG = "pass_NG"        # 게이트 통과 + 오분류 = 게이트를 넘은 오알림
AXIS_BLOCKED = "blocked"   # 신뢰도 < 임계 → 1차 알림 skip(low_confidence)
AXES = (AXIS_OK, AXIS_NG, AXIS_BLOCKED)

# ── 재현 대조 기준값 ────────────────────────────────────────────────────────
# 출처 = docs/decisions.md 33.6(d) 「대조군 재현 (3회차)」 표 (33.6(b) 표와 전건 일치).
# 계수 단위 = **클립 수(파일 수)**. 매직 넘버가 아니라 SSoT 인용값이다.
BASELINE_AXIS: dict[str, dict[str, int]] = {
    "doorbell":   {"n": 62,  AXIS_OK: 44,  AXIS_NG: 9,  AXIS_BLOCKED: 9},
    "knock":      {"n": 108, AXIS_OK: 92,  AXIS_NG: 5,  AXIS_BLOCKED: 11},
    "fire_alarm": {"n": 254, AXIS_OK: 231, AXIS_NG: 13, AXIS_BLOCKED: 10},
}
# 출처 = 33.6(d) 「`pass_NG` 27건의 오분류 대상 내역」 표. (true, predicted) → 클립 수.
# ⚠️ 「`fire_alarm`이 흡인 클래스」는 33.6(d)가 **논증**으로 못박은 해석이며 support 254
#   최다와의 인과는 미실증이다 — 본 상수는 계수일 뿐 그 해석을 확정하지 않는다.
BASELINE_NG_CONFUSION: dict[tuple[str, str], int] = {
    ("doorbell", "knock"): 3,      ("doorbell", "fire_alarm"): 6,
    ("knock", "doorbell"): 1,      ("knock", "fire_alarm"): 4,
    ("fire_alarm", "doorbell"): 9, ("fire_alarm", "knock"): 4,
}
# 출처 = 33.6(b) overall accuracy 0.8868 = 376/424 (`eval_report.json`
# 0.8867924528301887 과 일치). 게이트와 무관한 순수 예측 정확도다.
BASELINE_CORRECT = 376
BASELINE_TOTAL = 424

# 실모델 확증 3축 ① RSS. 33.6(a) 475,920KB / 33.6(d) 461,280KB — **자릿수(6자리)만** 본다.
# 기기·TF 빌드마다 다르므로 정확 일치를 요구하면 그 자체가 거짓 실패가 된다.
REAL_MODEL_RSS_KB_RANGE = (100_000, 999_999)

# split SSoT. 33.6(b) 「`split_manifest.csv` 의 test split 과 개수 일치」.
# ⚠️ 같은 폴더의 `final_manifest.csv`(증강 포함 전수 인덱스)는 split 정의가 아니다.
MANIFEST_RELPATH = "manifests/split_manifest.csv"
TEST_SPLIT = "test"

# 입력 위생 계약 — (framerate, channels, sampwidth). SAMPLE_RATE 는 프로즌 상수 상속.
WAV_CONTRACT = (SAMPLE_RATE, 1, 2)

EXIT_OK = 0
EXIT_BASELINE_MISMATCH = 1
EXIT_GATE_DIVERGENCE = 2   # raw ↔ rounded 불일치. **결과**이지 실패가 아니다(33.6(e)).
EXIT_ENV = 3
# labels.json(재학습 export 산출) 의 라벨 순서가 하네스의 argmax 매핑과 갈렸다.
# 4 = 기존 값 도메인 {0,1,2,3} 의 첫 빈 번호. EXIT_BASELINE_MISMATCH(1)와 **갈라야** 한다 —
# 라벨이 어긋나면 집계가 통째로 틀리는데 1 로 나오면 "모델이 달라졌나"로 오독된다.
EXIT_LABEL_MISMATCH = 4


# ──────────────────────────────────────────────────────────────────────────
# 순수 판정부 (self-test 가 TF·데이터 없이 직접 때리는 지점)
# ──────────────────────────────────────────────────────────────────────────


def axis_of(predicted: str, confidence: float, true_class: str,
            threshold: float = CONFIDENCE_THRESHOLD) -> str:
    """(예측, 신뢰도, 정답) → 게이트 축 1개.

    비교는 프로즌 `utils._apply_prediction_policy` 와 동일한 **strict `<`** 다
    (카테고리 3 `CONFIDENCE_THRESHOLD=0.7`). 경계값 0.7 자체는 **통과**다.
    ★ ToF 게이트(G12 `fire_alarm` 우회)는 본 축에 들어오지 않는다 — 33.6(b)의 축 정의가
      신뢰도 게이트 단독이고, 본 하네스는 ToF telemetry 를 입력으로 받지 않는다.
      `pass_NG` 중 「위험 방향」(타클래스 → `fire_alarm`)이 presence 무관 발송이 되는 이유가
      바로 그 G12 우회지만, 그 판정은 서버 경로의 몫이며 여기서 재현하지 않는다.
    """
    if confidence < threshold:
        return AXIS_BLOCKED
    return AXIS_OK if predicted == true_class else AXIS_NG


def judge(scores, true_class: str, classes=PREDICTED_CLASSES) -> dict:
    """(1,3) 확률 1행 → raw/rounded 2열 판정.

    - `predicted` = argmax 인덱스를 `classes` 로 매핑. 기본값은 프로즌
      `app.constants.PREDICTED_CLASSES`(doorbell 0 / knock 1 / fire_alarm 2, 33.2).
      `classes` 인자는 **NC-1(라벨 매핑 의존성) 전용 주입구**다 — 프로즌 파일을 변형하지
      않고 "이 하네스가 라벨 순서에 실제로 의존하는가"를 때리기 위한 것.
    - `conf_rounded` 는 프로즌 `scores_to_prediction` 이 낸 값을 그대로 쓴다(재구현 금지).
      제품 경로의 반올림 그 자체여야 33.6(e) 비교가 성립한다.
    """
    row = scores[0]
    idx = int(row.argmax())
    predicted = classes[idx]
    conf_raw = float(row[idx])
    _, conf_rounded, _ = scores_to_prediction(scores)
    return {
        "predicted": predicted,
        "conf_raw": conf_raw,
        "conf_rounded": conf_rounded,
        "axis_raw": axis_of(predicted, conf_raw, true_class),
        "axis_rounded": axis_of(predicted, conf_rounded, true_class),
    }


def tally(results: list[dict], axis_key: str) -> dict[str, dict[str, int]]:
    """판정 목록 → 클래스별 게이트 축 집계(기준값 표와 동형)."""
    out = {c: {"n": 0, AXIS_OK: 0, AXIS_NG: 0, AXIS_BLOCKED: 0} for c in PREDICTED_CLASSES}
    for r in results:
        cell = out.setdefault(
            r["true"], {"n": 0, AXIS_OK: 0, AXIS_NG: 0, AXIS_BLOCKED: 0}
        )
        cell["n"] += 1
        cell[r[axis_key]] += 1
    return out


def ng_confusion(results: list[dict], axis_key: str) -> Counter:
    """`pass_NG` 건의 (정답, 예측) 계수 — 33.6(d) 오분류 대상 내역."""
    return Counter(
        (r["true"], r["predicted"]) for r in results if r[axis_key] == AXIS_NG
    )


def compare_baseline(axis_counts, ng_counts, correct, total,
                     baseline_axis=BASELINE_AXIS,
                     baseline_ng=BASELINE_NG_CONFUSION,
                     baseline_correct=BASELINE_CORRECT,
                     baseline_total=BASELINE_TOTAL) -> list[str]:
    """33.6(b)(d) 기준값과 **전 칸 정확 일치** 대조. 반환 = 불일치 설명 목록(빈 목록 = 일치).

    ★ 느슨한 비교(부분 일치·근사)를 쓰면 NC-2 가 통과해 버린다 — 전 칸 `!=` 비교를 유지할 것.
    """
    diffs: list[str] = []
    for cls, expect in baseline_axis.items():
        got = axis_counts.get(cls)
        if got is None:
            diffs.append(f"클래스 누락: {cls}")
            continue
        for key in ("n", *AXES):
            if got[key] != expect[key]:
                diffs.append(f"{cls}.{key}: 실측 {got[key]} != 기준 {expect[key]}")
    for cls in axis_counts:
        if cls not in baseline_axis:
            diffs.append(f"기준값에 없는 클래스 출현: {cls}")
    for pair in set(baseline_ng) | set(ng_counts):
        exp, got = baseline_ng.get(pair, 0), ng_counts.get(pair, 0)
        if exp != got:
            diffs.append(f"pass_NG {pair[0]}→{pair[1]}: 실측 {got} != 기준 {exp}")
    if total != baseline_total:
        diffs.append(f"총 건수: 실측 {total} != 기준 {baseline_total}")
    if correct != baseline_correct:
        diffs.append(f"정답 건수: 실측 {correct} != 기준 {baseline_correct}")
    return diffs


# ──────────────────────────────────────────────────────────────────────────
# 입력부
# ──────────────────────────────────────────────────────────────────────────


def fail_env(msg: str):
    """환경·입력 오류 → 읽을 수 있는 메시지 + EXIT_ENV.

    ★ 종료 코드를 EXIT_BASELINE_MISMATCH(1)와 **갈라야** 한다 — "환경을 잘못 줬다"와
      "기준값과 달랐다"가 같은 코드로 나오면 절차서의 결과 판독이 무너진다.
    """
    print(f"[환경 오류] {msg}", file=sys.stderr)
    return SystemExit(EXIT_ENV)


def labels_path() -> Path:
    """배포 라벨 스냅샷(`labels.json`) 경로. `ml.training.config.model_dir()` 과 같은 규칙.

    (ml 패키지를 import 하지 않는다 — 이 하네스는 server/ 런타임에서 돌고 ml 은 의존성이
     다르다. 규칙만 복제하고 근거를 여기 각인한다: env DDINGDONG_MODEL_DIR 우선,
     없으면 repo 내 `ml/models/yamnet`.)
    """
    raw = os.environ.get("DDINGDONG_MODEL_DIR", "").strip()
    base = (Path(raw).expanduser() if raw
            else Path(__file__).resolve().parents[2] / "ml" / "models" / "yamnet")
    return base / "labels.json"


def assert_label_order(path: Path, classes=PREDICTED_CLASSES) -> None:
    """`labels.json` 의 라벨 순서 == 하네스가 argmax 매핑에 실제로 쓰는 상수인가.

    **비교 대상 선택 근거**: judge() 가 argmax 인덱스를 클래스 이름으로 바꿀 때 실제로
    참조하는 것은 `app.constants.PREDICTED_CLASSES` 다. 33.2 는 서빙 출력의 라벨 순서를
    「`CLASSES` 상속」으로 등재했고 `labels.json` 은 그 상속을 재학습 시점에 굳힌 스냅샷이다.
    ⇒ 대조해야 할 두 축은 「하네스가 믿는 순서」와 「산출물이 주장하는 순서」다.

    **왜 실행 시점에 보는가**: 셋(labels.json / PREDICTED_CLASSES / inference CLASSES)이
    갈릴 수 있는 유일한 지점은 `python -m ml.training.export` 다. 갈리면 하네스는 조용히
    오라벨링된 집계를 내고 사람은 EXIT_BASELINE_MISMATCH(1) 만 본다 — 원인이 라벨인지
    모델인지 안 갈린다. 그 침묵을 없애는 것이 이 확인의 전부다.

    **부재 시 거동 = 실패(EXIT_ENV)**. 이 파일은 git 미추적이라 clone 직후엔 없지만,
    이 확인은 **실스윕 경로에서만** 돈다. 실스윕은 DDINGDONG_MODEL_PATH(= export 산출물)를
    요구하므로 export 가 돈 환경에서만 도달한다 ⇒ 거기서의 부재는 정상이 아니라 「환경을
    잘못 줬다」. `--self-test` · `--dry-run` 은 모델이 필요 없어 이 경로를 지나가지 않으므로
    clone 직후에도 하네스는 돈다(「없으면 조용히 통과」를 두지 않고도 양쪽을 만족).
    """
    if not path.is_file():
        raise fail_env(
            f"라벨 스냅샷 없음: {path}\n"
            "  → `python -m ml.training.export` 산출물과 같은 폴더인지, "
            "DDINGDONG_MODEL_DIR 지정이 맞는지 확인.\n"
            "  ⚠️ 이 파일은 git 미추적이다 — clone 직후라면 export 를 먼저 돌려야 한다."
        )
    try:
        got = tuple(json.loads(path.read_text(encoding="utf-8"))["classes"])
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise fail_env(f"라벨 스냅샷을 읽을 수 없음 {path}: {exc!r}")
    if got != tuple(classes):
        print(
            f"[라벨 순서 불일치] {path}\n"
            f"  labels.json       = {list(got)}\n"
            f"  PREDICTED_CLASSES = {list(classes)}\n"
            "  → argmax 인덱스→클래스 매핑이 어긋난다. 이 상태의 집계는 전부 오라벨링이다.\n"
            "  → 재학습 산출물(33.2 export)과 서빙 상수 중 어느 쪽이 옳은지 정하고 맞출 것.",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_LABEL_MISMATCH)


def read_wav(path: Path) -> tuple[bytes, int]:
    """wav → (PCM 바이트, framerate). 계약 위반은 **건너뛰지 않고 예외**로 올린다.

    조용한 누락이 가장 나쁘다 — 누락된 파일은 집계에서 사라져 재현 대조를 통과시켜 버린다.
    """
    with wave.open(str(path), "rb") as w:
        actual = (w.getframerate(), w.getnchannels(), w.getsampwidth())
        if actual != WAV_CONTRACT:
            raise ValueError(
                f"입력 위생 위반 {path.name}: (framerate, channels, sampwidth)="
                f"{actual} != 계약 {WAV_CONTRACT}"
            )
        return w.readframes(w.getnframes()), actual[0]


def load_test_rows(data_root: Path) -> list[dict]:
    """split SSoT 에서 test split 행만. 반환 = [{filepath, class, stem}, ...] (파일 순서 보존)."""
    manifest = data_root / MANIFEST_RELPATH
    if not manifest.is_file():
        raise fail_env(
            f"split manifest 없음: {manifest}\n"
            f"  → DDINGDONG_DATA_ROOT 가 '{MANIFEST_RELPATH}' 상위 폴더인지 확인.\n"
            "  ⚠️ 같은 폴더의 final_manifest.csv 는 증강 포함 전수 인덱스이지 split 정의가 아니다."
        )
    with manifest.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == TEST_SPLIT]
    if not rows:
        raise fail_env(f"{manifest} 에 split=={TEST_SPLIT} 행이 0건")
    return rows


def env_path(name: str) -> Path:
    """필수 환경변수 → Path. 미설정은 스택트레이스가 아니라 **읽을 수 있는 에러**로."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise fail_env(
            f"{name} 미설정 — 경로 하드코딩을 두지 않으므로 주입이 필수입니다.\n"
            f"  예: {name}=\"…\" venv_real/bin/python3 tools/gate_axis_sweep.py"
        )
    p = Path(raw).expanduser()
    if not p.exists():
        raise fail_env(f"{name} 경로가 존재하지 않음: {p}")
    return p


# ──────────────────────────────────────────────────────────────────────────
# 실모델 확증 3축 (mock 반증 — 33.6(a)(d))
# ──────────────────────────────────────────────────────────────────────────


def rss_kb() -> int | None:
    """자기 프로세스 RSS(KB). `ps` 기준 = 33.6(a)(d) 기록값과 같은 단위."""
    try:
        out = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(os.getpid())],
            capture_output=True, text=True, check=True,
        )
        return int(out.stdout.strip())
    except Exception:
        return None


def tf_mapping_count() -> int | None:
    """프로세스에 매핑된 tensorflow 공유 라이브러리 수. 33.6(a)(d) 기록값 54 계열."""
    try:
        out = subprocess.run(
            ["lsof", "-p", str(os.getpid())],
            capture_output=True, text=True, check=False,
        )
        return sum(1 for line in out.stdout.splitlines() if "tensorflow" in line)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────
# 스윕
# ──────────────────────────────────────────────────────────────────────────


def sweep(data_root: Path, model_path: Path, rows_out) -> int:
    from inference.model_runner import ModelRunner  # TF lazy import (프로즌 러너 경유)

    rows = load_test_rows(data_root)
    print(f"[입력] {data_root / MANIFEST_RELPATH} split={TEST_SPLIT} → {len(rows)}건(클립 수)")

    runner = ModelRunner(str(model_path))
    print(f"[모델] {model_path}")

    results: list[dict] = []
    first_shape = None
    for row in rows:
        path = Path(row["filepath"])
        pcm, framerate = read_wav(path)
        # ★ decode_pcm16 반환은 이미 (1, N) = 배치 차원 포함이다. 여기에 `[None, :]` 로
        #   배치를 재추가하면 (1, 1, N) 이 되어 YAMNet Pad 에러로 전건 실패한다(33.6(c)
        #   실사고 — 424건 전건 실패). **절대 배치를 덧씌우지 말 것.**
        waveform = decode_pcm16(pcm, framerate)
        if first_shape is None:
            first_shape = waveform.shape
            print(f"[전처리] decoded shape {first_shape} (프로즌 decode_pcm16, 배치 재추가 없음)")
        scores = runner.predict(waveform)
        verdict = judge(scores, row["class"])
        verdict.update(true=row["class"], stem=row["stem"])
        results.append(verdict)

    # ── 실모델 확증 3축 ──────────────────────────────────────────────────
    same = runner.predict(decode_pcm16(*read_wav(Path(rows[0]["filepath"]))))
    twice_identical = bool(
        (same == runner.predict(decode_pcm16(*read_wav(Path(rows[0]["filepath"]))))).all()
    )
    rss, maps = rss_kb(), tf_mapping_count()
    lo, hi = REAL_MODEL_RSS_KB_RANGE
    print("[실모델 확증] ① RSS = "
          f"{rss}KB ({'자릿수 정합' if rss and lo <= rss <= hi else '⚠️ 범위 밖 — 확인 필요'})")
    print(f"[실모델 확증] ② TF 라이브러리 매핑 = {maps}개")
    print(f"[실모델 확증] ③ 동일 입력 2회 출력 완전 일치 = {twice_identical}")
    if not maps or not twice_identical:
        print("[실모델 확증] 🔴 ②③ 중 실패 — mock 가능성. 결과를 실모델 실측으로 기록하지 말 것.")
        return EXIT_ENV

    # ── 집계 · 대조 ──────────────────────────────────────────────────────
    axis_counts = tally(results, "axis_raw")
    ngc = ng_confusion(results, "axis_raw")
    correct = sum(1 for r in results if r["predicted"] == r["true"])
    print_summary(axis_counts, ngc, correct, len(results))

    diverged = [r for r in results if r["axis_raw"] != r["axis_rounded"]]
    print(f"\n[raw vs rounded] 분류가 갈린 건 = {len(diverged)}건 "
          "(33.6(e) — raw 게이트 vs 2자리 반올림 게이트)")
    for r in diverged:
        print(f"  - {r['stem']} true={r['true']} pred={r['predicted']} "
              f"raw={r['conf_raw']!r} → {r['axis_raw']} / rounded={r['conf_rounded']!r} "
              f"→ {r['axis_rounded']}")

    write_rows(results, rows_out)

    diffs = compare_baseline(axis_counts, ngc, correct, len(results))
    if diffs:
        print("\n[재현 대조] 🔴 33.6(b)(d) 기준값과 불일치 "
              f"{len(diffs)}건 — 하네스 결함인지 데이터·모델 변화인지 가를 것:")
        for d in diffs:
            print(f"  - {d}")
        return EXIT_BASELINE_MISMATCH
    print("\n[재현 대조] ✅ 33.6(b)(d) 기준값과 전건 일치 (값 갱신이 아니라 재현)")
    return EXIT_GATE_DIVERGENCE if diverged else EXIT_OK


def print_summary(axis_counts, ngc, correct, total) -> None:
    print("\n[게이트 축] 신뢰도 임계 "
          f"{CONFIDENCE_THRESHOLD} strict `<` · 계수 단위 = 클립 수(파일 수)")
    print(f"{'true':<12}{'n':>5}{'pass_ok':>9}{'pass_NG':>9}{'blocked':>9}{'pass%':>8}")
    for cls in PREDICTED_CLASSES:
        c = axis_counts.get(cls, {"n": 0, AXIS_OK: 0, AXIS_NG: 0, AXIS_BLOCKED: 0})
        pct = (c[AXIS_OK] + c[AXIS_NG]) / c["n"] * 100 if c["n"] else 0.0
        print(f"{cls:<12}{c['n']:>5}{c[AXIS_OK]:>9}{c[AXIS_NG]:>9}{c[AXIS_BLOCKED]:>9}{pct:>7.1f}%")
    tot = {k: sum(c[k] for c in axis_counts.values()) for k in ("n", *AXES)}
    print(f"{'합계':<11}{tot['n']:>5}{tot[AXIS_OK]:>9}{tot[AXIS_NG]:>9}{tot[AXIS_BLOCKED]:>9}")

    print("\n[pass_NG 오분류 대상] 게이트를 넘은 오알림의 행선지")
    for true_cls in PREDICTED_CLASSES:
        parts = [f"→{p} {n}" for (t, p), n in sorted(ngc.items()) if t == true_cls]
        print(f"  {true_cls:<12}{' · '.join(parts) if parts else '(없음)'}")
    print(f"\n[accuracy] {correct}/{total} = {correct / total:.10f} (게이트 무관 순수 예측)")


def write_rows(results: list[dict], out) -> None:
    """행 단위 기계 판독 결과. 기본은 stdout — repo 안에 파일을 쓰지 않는 것이 기본값이다."""
    fields = ["stem", "true", "predicted", "conf_raw", "conf_rounded", "axis_raw", "axis_rounded"]
    stream = sys.stdout if out is None else out.open("w", newline="", encoding="utf-8")
    try:
        if out is None:
            print("\n--- rows(csv) ---")
        w = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    finally:
        if out is not None:
            stream.close()
            print(f"\n[행 결과] {out}")


# ──────────────────────────────────────────────────────────────────────────
# negative control — 하네스가 진짜 잡는지 자체 검증 (8.4(f) 선례, 카테고리 20)
# ──────────────────────────────────────────────────────────────────────────


def self_test() -> int:
    """TF·데이터 없이 도는 NC 4종 + 각 축의 baseline(통과가 정상인 대조군).

    ★ 프로즌 파일을 **변형하지 않는다** — 라벨 매핑은 `judge(classes=…)` 주입구로, 기준값은
      `compare_baseline(baseline_*=…)` 주입구로 때린다. 따라서 복원할 원본이 없다
      (파일 변형형 NC 가 아니므로 §복원 증명 대상 자체가 성립하지 않는다).
    """
    import numpy as np

    def scores(*p):
        return np.array([list(p)], dtype=np.float32)

    # 합성 판정 입력: doorbell 정답 3건(통과 / 오분류 통과 / 차단)
    fixture = [
        (scores(0.90, 0.05, 0.05), "doorbell"),   # → pass_ok
        (scores(0.05, 0.05, 0.90), "doorbell"),   # → pass_NG (→fire_alarm)
        (scores(0.50, 0.30, 0.20), "doorbell"),   # → blocked
    ]

    def run(classes=PREDICTED_CLASSES):
        out = []
        for s, t in fixture:
            v = judge(s, t, classes=classes)
            v.update(true=t, stem="synthetic")
            out.append(v)
        return out

    base = run()
    ok = True

    # --- baseline(무변형): 판정부가 정상 동작하는가 = 도구 생존 증명 ---
    got = [r["axis_raw"] for r in base]
    ok &= _check("baseline", got == [AXIS_OK, AXIS_NG, AXIS_BLOCKED], f"축={got}")

    # --- NC-1 라벨 매핑 의존성 --------------------------------------------
    # 불변식: 이 하네스는 argmax 인덱스 → 클래스 이름 매핑에 **실제로** 의존한다.
    # 결함 조건: 매핑이 뒤집혔는데도 집계가 그대로면, 하네스는 라벨을 보지 않고 있다.
    # 함정: 클래스 "이름"만 비교하면 안 잡힌다 — **정답 대비 축 분류**가 바뀌어야 검출이다.
    flipped = run(classes=tuple(reversed(PREDICTED_CLASSES)))
    ok &= _check(
        "NC-1 라벨 매핑 뒤집기",
        [r["axis_raw"] for r in flipped] != got,
        f"뒤집은 축={[r['axis_raw'] for r in flipped]}",
    )

    # --- NC-2 재현 대조가 실제로 대조하는가 -------------------------------
    # 불변식: 기준값 한 칸만 틀려도 불일치로 잡힌다.
    # 함정: 부분 일치·근사 비교를 쓰면 통과해 버린다.
    counts = tally(base, "axis_raw")
    ngc = ng_confusion(base, "axis_raw")
    # ⚠️ tally() 는 미출현 클래스도 0 으로 채운다 → 기준값도 3클래스 전부를 담아야 한다
    #   (한 클래스만 넣으면 "기준값에 없는 클래스 출현"이 떠서 대조군이 거짓 실패한다).
    full = {cls: dict(cell) for cls, cell in counts.items()}
    clean = compare_baseline(counts, ngc, 1, 3, baseline_axis=full,
                             baseline_ng=dict(ngc), baseline_correct=1, baseline_total=3)
    ok &= _check("NC-2 대조군(무변형)", clean == [], f"불일치={clean}")
    tampered = {cls: dict(cell) for cls, cell in full.items()}
    tampered["doorbell"][AXIS_NG] += 1        # 딱 한 칸
    dirty = compare_baseline(counts, ngc, 1, 3, baseline_axis=tampered,
                             baseline_ng=dict(ngc), baseline_correct=1, baseline_total=3)
    ok &= _check("NC-2 기준값 한 칸 변조", bool(dirty), f"불일치={dirty}")

    # --- NC-3 입력 위생이 침묵하지 않는가 ---------------------------------
    # 불변식: 계약 위반 파일은 조용히 건너뛰지 않고 **실패**한다.
    # 함정: 합성 wav 로만 때린다(데이터셋 오염 금지). finally 로 삭제한다.
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    try:
        good, bad = tmp / "good.wav", tmp / "bad_8k.wav"
        for path, rate in ((good, SAMPLE_RATE), (bad, 8000)):
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(rate)
                w.writeframes(b"\x00\x00" * 100)
        pcm, fr = read_wav(good)
        ok &= _check("NC-3 대조군(계약 준수 wav)", (len(pcm), fr) == (200, SAMPLE_RATE),
                     f"bytes={len(pcm)} framerate={fr}")
        try:
            read_wav(bad)
            ok &= _check("NC-3 8kHz 혼입", False, "예외 없이 통과 — 조용한 누락")
        except ValueError as exc:
            ok &= _check("NC-3 8kHz 혼입", True, str(exc))
    finally:
        for p in tmp.glob("*"):
            p.unlink()
        tmp.rmdir()
        ok &= _check("NC-3 임시 파일 정리", not tmp.exists(), f"{tmp} 삭제")

    # --- NC-4 raw / rounded 2열이 실제로 갈리는가 -------------------------
    # 불변식: raw 가 [0.695, 0.70) 이면 raw=blocked / rounded=pass 로 **갈려서 보고**된다.
    # 함정: 한쪽 열만 계산하면 33.6(e) 는 영원히 0건으로 보인다.
    edge = judge(scores(0.6970, 0.2000, 0.1030), "doorbell")
    ok &= _check(
        "NC-4 [0.695,0.70) 경계",
        (edge["axis_raw"], edge["axis_rounded"]) == (AXIS_BLOCKED, AXIS_OK),
        f"raw={edge['conf_raw']!r}→{edge['axis_raw']} / "
        f"rounded={edge['conf_rounded']!r}→{edge['axis_rounded']}",
    )
    # 대조군: 경계 밖 값은 두 열이 같아야 한다(과검출 방지).
    mid = judge(scores(0.9000, 0.0500, 0.0500), "doorbell")
    ok &= _check("NC-4 대조군(경계 밖)", mid["axis_raw"] == mid["axis_rounded"],
                 f"{mid['axis_raw']} / {mid['axis_rounded']}")

    # --- NC-5 라벨 스냅샷 대조가 침묵하지 않는가 ---------------------------
    # 불변식: labels.json 의 라벨 순서가 하네스의 argmax 매핑과 갈리면 **조용히 통과하지
    #   않는다**(전용 종료 코드 4). 부재도 마찬가지로 침묵하지 않는다(3).
    # 함정: 실물 `ml/models/yamnet/labels.json` 은 **git 미추적**이라 잃으면 export 없이
    #   복구가 안 된다 → 원본은 읽지도 쓰지도 않고 tmp 에 **합성 복제본**만 때린다.
    #   (파일 변형형 NC 가 아니므로 복원 증명 대신 "원본 미접촉"이 증명 대상이다.)
    real = labels_path()
    before = real.read_bytes() if real.is_file() else None
    tmp2 = Path(tempfile.mkdtemp())
    try:
        good = tmp2 / "labels.json"
        good.write_text(json.dumps({"classes": list(PREDICTED_CLASSES)}), encoding="utf-8")
        try:                                    # 대조군: 일치하면 조용히 통과가 정상
            assert_label_order(good)
            ok &= _check("NC-5 대조군(순서 일치)", True, f"{list(PREDICTED_CLASSES)}")
        except SystemExit as exc:
            ok &= _check("NC-5 대조군(순서 일치)", False, f"거짓 실패 exit={exc.code}")

        bad = tmp2 / "flipped.json"
        bad.write_text(json.dumps({"classes": list(reversed(PREDICTED_CLASSES))}), encoding="utf-8")
        try:
            assert_label_order(bad)
            ok &= _check("NC-5 순서 뒤집기", False, "예외 없이 통과 — 조용한 오라벨링")
        except SystemExit as exc:
            ok &= _check("NC-5 순서 뒤집기", exc.code == EXIT_LABEL_MISMATCH,
                         f"exit={exc.code} (기대 {EXIT_LABEL_MISMATCH})")

        try:                                    # 부재도 침묵하지 않는가
            assert_label_order(tmp2 / "absent.json")
            ok &= _check("NC-5 스냅샷 부재", False, "예외 없이 통과")
        except SystemExit as exc:
            ok &= _check("NC-5 스냅샷 부재", exc.code == EXIT_ENV,
                         f"exit={exc.code} (기대 {EXIT_ENV})")
    finally:
        for f in tmp2.glob("*"):
            f.unlink()
        tmp2.rmdir()
        after = real.read_bytes() if real.is_file() else None
        ok &= _check("NC-5 실물 labels.json 미접촉", after == before,
                     f"{real} {'무변경' if after == before else '★변경됨★'}"
                     f" (존재={after is not None})")

    print("\n" + ("✅ self-test 전건 통과" if ok else "🔴 self-test 실패 — 하네스를 믿지 말 것"))
    return EXIT_OK if ok else EXIT_BASELINE_MISMATCH


def _check(name: str, passed: bool, detail: str) -> bool:
    print(f"  [{'PASS' if passed else 'FAIL'}] {name:<28} {detail}")
    return passed


# ──────────────────────────────────────────────────────────────────────────


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="게이트 축 전수 스윕 (33.6(b)(d) 재현 · 제품 동작 불변)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--self-test", action="store_true",
                    help="negative control 4종 실행(데이터·모델 불필요)")
    ap.add_argument("--dry-run", action="store_true",
                    help="환경변수·매니페스트 파싱까지만(추론 0건, TF 미로드)")
    ap.add_argument("--rows-out", type=Path, default=None,
                    help="행 단위 CSV 저장 경로(repo 밖만). 미지정 시 stdout.")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if args.rows_out is not None:
        repo = Path(__file__).resolve().parents[2]
        if repo in args.rows_out.resolve().parents:
            raise fail_env(
                f"--rows-out 이 repo 안을 가리킴: {args.rows_out}\n"
                "  → 측정 결과는 repo 밖에 둔다(실측 로그 규약, `.gitignore` 차단분)."
            )

    data_root = env_path("DDINGDONG_DATA_ROOT")
    if args.dry_run:
        rows = load_test_rows(data_root)
        dist = Counter(r["class"] for r in rows)
        print(f"[드라이런] test split {len(rows)}건 / 분포 {dict(dist)}")
        print("[드라이런] 추론 미수행 · TF 미로드 — DDINGDONG_MODEL_PATH 미검증")
        return EXIT_OK

    assert_label_order(labels_path())
    return sweep(data_root, env_path("DDINGDONG_MODEL_PATH"), args.rows_out)


if __name__ == "__main__":
    sys.exit(main())
