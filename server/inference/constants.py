"""추론 서빙 하네스 상수 (매직넘버 중앙 관리, server/app/constants.py 컨벤션 준수).

값의 SSoT 는 docs/decisions.md 카테고리 3·6·33.2. 여기서는 그 결정값을 서버 추론
도메인 로컬 상수로 명시(가정·발명 금지 — 각 항목에 근거 카테고리 주석).
"""

from __future__ import annotations

# 카테고리 4/33.2: raw waveform 16kHz mono (YAMNet 입력 SSoT)
SAMPLE_RATE: int = 16000

# 카테고리 33.2: 서빙 출력 (1, 3) — 라벨 순서 = CLASSES 상속 (doorbell=0/knock=1/fire_alarm=2)
NUM_CLASSES: int = 3
CLASSES: tuple[str, str, str] = ("doorbell", "knock", "fire_alarm")

# 오디오 계약(가정, audio_decode.py 참조): PCM int16 little-endian
BYTES_PER_SAMPLE: int = 2          # int16 = 2 bytes
PCM_DTYPE: str = "<i2"             # little-endian signed 16-bit
NORM_DIVISOR: float = 32768.0      # int16 → [-1, 1] 정규화(32768 = 2^15, 대칭 하한 기준)

# 카테고리 6: t3.small 2GB RAM → 추론 메모리 예산
MEM_BUDGET_MB: int = 2048

# 카테고리 3: 1차 알림 목표 ≤5초 → 추론 지연 예산(단일 추론 상한, ms)
LATENCY_BUDGET_MS: int = 5000

# 벤치 기본값
DEFAULT_ITERATIONS: int = 30       # 측정 반복(warm-up 제외 후)
DEFAULT_WARMUP: int = 3            # graph trace·캐시 워밍업(측정 제외)
DEFAULT_CLIP_SECONDS: float = 2.0  # 합성 오디오 길이(초)

# TFLite 전환 권고 임계: TF+YAMNet peak RSS 가 예산의 이 비율 초과 시 경고
TFLITE_ADVISE_RATIO: float = 0.85  # peak_rss > 2048*0.85 ≈ 1741MB → TFLite 변환 권고
