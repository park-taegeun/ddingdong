"""/detect 추론 입력 레벨 — 4클래스 모델에만 학습과 같은 피크 정규화 (사용자 결정 2026-09-30).

학습 전처리는 파일마다 피크를 TARGET_PEAK 로 맞추고(ml/pipeline/audio_io.peak_normalize),
서빙은 decode_pcm16(÷32768)만 한다(decisions.md 5.2(d) 비대칭). 이 모듈은 그 식을 서버에
복제한다 — 서버는 ml 패키지를 import 하지 않으므로(sound_match 선례) 값과 식을 옮겨 적고,
test_serving_level 이 ml 원문 텍스트와 매 실행 대조한다.

★ 4클래스 결합(안전장치 ①): 정규화는 PREDICTED_CLASSES 에 other 가 있을 때만 켜진다.
  3클래스 모델 + 정규화는 보드 무음을 fire_alarm 으로 끌어올려 ToF 를 우회 발송한다
  (33.18(b): presence=false 발송 0 → 12, 2026-09-29 재측정 4 → 25). 그래서 그 조합은 기동 실패다.
  근거 측정 = repo 밖 ~/ddingdong-측정결과/2026-09-29/level_norm_4cls/report.md
  (4클래스 + peak: 보드 무음 오발송 22 → 5, 초인종 · 노크 · 공개 test · 화재 손실 0).
★ 적용 범위(안전장치 ②): /detect 의 model_serving.predict 입력만. 등록 계측(registration_observe)
  은 query 를 waveform 에서, 저장 템플릿을 원본 PCM decode 에서 만들므로 waveform 은 원본 그대로
  둬야 두 쪽 레벨이 맞는다. STT(/enrich)도 원본.
★ 재판정 트리거: 학습 정규화 규칙이 바뀌면(예: 3차 재학습 후보 「글리치 제외 피크」 채택) 이 식도
  함께 바꿔야 한다 — 대조 테스트가 ml 원문 변경을 FAIL 로 알린다.
★ 규칙 계보(사용자 결정 B, 2026-09-30): 모델이 자기 입력 규칙을 선언하고 서버가 따라간다. 학습 run
  폴더 train_config.json 의 peak_rule(02 전처리 기록 → 05 → 학습이 옮긴 값)을 기동 시 읽어(resolve_rule)
  RULES 의 같은 이름 함수로 정규화한다. 두 규칙 모두 ml/pipeline/audio_io 원문과 매 실행 대조된다.
"""

import json
from pathlib import Path

import numpy as np

# ml/pipeline/config 복제 — TARGET_PEAK(0.95 linear ≈ -0.45 dBFS) · 규칙 이름 · 클램프 끝값 · 가림 폭.
TARGET_PEAK = 0.95
RULE_PLAIN = "peak_plain_v1"
RULE_CLAMPMASK32 = "peak_clampmask32_v1"
CLAMP_LEVEL = 32767 / 32768
CLAMP_GUARD_SAMPLES = 32
# ml/training/train.TRAIN_CONFIG_NAME 과 그 안의 규칙 키.
TRAIN_CONFIG_NAME = "train_config.json"
RULE_KEY = "peak_rule"

LEVEL_RAW = "raw"
LEVEL_PEAK = "peak"
LEVEL_ENV = "DDINGDONG_SERVING_LEVEL"


def peak_normalize(waveform):
    """(1, N) float32 → 피크를 TARGET_PEAK 로 맞춘 새 배열. 피크 ≤ 1e-9 면 원본 그대로(학습 식과 동일)."""
    peak = float(np.max(np.abs(waveform)))
    if peak <= 1e-9:
        return waveform
    return waveform * (TARGET_PEAK / peak)


def peak_normalize_clampmask(waveform):
    """(1, N) float32 → 모든 클램프(|x| ≥ CLAMP_LEVEL) ±CLAMP_GUARD_SAMPLES 를 피크 계산에서 뺀 이득을 전체에 적용.
    남는 샘플이 없거나 남은 피크 ≤ 1e-9 면 원본 그대로(학습 식 audio_io.peak_normalize_clampmask 와 동일)."""
    flat = np.abs(waveform).reshape(-1)
    clamp = (flat >= CLAMP_LEVEL).astype(np.int32)
    kernel = np.ones(2 * CLAMP_GUARD_SAMPLES + 1, dtype=np.int32)
    masked = np.convolve(clamp, kernel, mode="full")[CLAMP_GUARD_SAMPLES:CLAMP_GUARD_SAMPLES + flat.size] > 0
    rest = flat[~masked]
    peak = float(rest.max()) if rest.size else 0.0
    if peak <= 1e-9:
        return waveform
    return waveform * (TARGET_PEAK / peak)


RULES = {RULE_PLAIN: peak_normalize, RULE_CLAMPMASK32: peak_normalize_clampmask}


def resolve_rule(model_path):
    """기동 시 1회(peak 모드 + 실모델). MODEL_PATH 상위 run 폴더 train_config.json 의 peak_rule → (규칙, 옛 모델 여부).

    파일 또는 키가 없음 = 옛 모델 → (RULE_PLAIN, True). 근거 = 사실: 정규화는 ml/pipeline 첫 커밋(#10 de05c7e)부터
    PEAK_NORMALIZE=True · audio_io.peak_normalize 단일 식이었고(git log -S PEAK_NORMALIZE · audio_io 커밋 1개),
    peak_rule 필드는 이 규칙 계보 PR 에서 처음 생긴다 — 그 전 학습(1차 run = train_config.json 자체 없음,
    2차 run = 키 없음)은 전부 plain 이다. 호출자가 WARNING 을 남긴다.
    그 밖의 값(null · 빈 문자열 · 모르는 이름)은 전부 ValueError — 기본값 fallback 없음.
    """
    path = Path(model_path).parent / TRAIN_CONFIG_NAME
    cfg = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if RULE_KEY not in cfg:
        return RULE_PLAIN, True
    rule = cfg[RULE_KEY]
    if not isinstance(rule, str) or rule not in RULES:
        raise ValueError(f"{path} {RULE_KEY}={rule!r}: 서버가 모르는 정규화 규칙입니다(허용: {tuple(RULES)}).")
    return rule, False


def resolve_mode(classes, env_value):
    """기동 시 1회. env 미설정(None) = 모델 계약(other 있으면 peak, 없으면 raw).
    env 는 raw / peak 만 허용 — 빈 문자열 · 공백 · 그 밖의 값은 전부 ValueError(기본값 fallback 없음)."""
    has_other = "other" in classes
    if env_value is None:
        return LEVEL_PEAK if has_other else LEVEL_RAW
    if env_value not in (LEVEL_RAW, LEVEL_PEAK):
        raise ValueError(f"{LEVEL_ENV}={env_value!r}: raw 또는 peak 만 허용합니다(미설정 = 모델 계약).")
    if env_value == LEVEL_PEAK and not has_other:
        raise ValueError(
            f"{LEVEL_ENV}=peak 는 other 클래스가 있는 4클래스 모델에만 허용합니다 "
            f"(현재 클래스 {tuple(classes)}) — 3클래스 + 정규화 = 보드 무음 화재 우회 발송(33.18(b))."
        )
    return env_value
