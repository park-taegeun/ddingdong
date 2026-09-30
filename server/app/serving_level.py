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
"""

import numpy as np

# ml/pipeline/config.TARGET_PEAK 복제(0.95 linear ≈ -0.45 dBFS).
TARGET_PEAK = 0.95

LEVEL_RAW = "raw"
LEVEL_PEAK = "peak"
LEVEL_ENV = "DDINGDONG_SERVING_LEVEL"


def peak_normalize(waveform):
    """(1, N) float32 → 피크를 TARGET_PEAK 로 맞춘 새 배열. 피크 ≤ 1e-9 면 원본 그대로(학습 식과 동일)."""
    peak = float(np.max(np.abs(waveform)))
    if peak <= 1e-9:
        return waveform
    return waveform * (TARGET_PEAK / peak)


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
