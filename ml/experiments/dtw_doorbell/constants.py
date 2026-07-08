"""DTW 초인종 스파이크 매직넘버 SSoT. 각 값에 근거(카테고리/가정) 주석."""

from __future__ import annotations

# ── 오디오 (카테고리 4: raw waveform 16kHz mono) ──
SAMPLE_RATE: int = 16000  # 카테고리 4 확정 (01_clips = 16k mono Int16)

# ── 멜스펙트로그램 (★ 가정 — 카테고리 4는 "멜스펙 2D 템플릿"만 명시, 세부값 미정) ──
# YAMNet 관례(25ms window / 10ms hop / 64 mel)를 기본값으로 채택. 11~12주차 튜닝 대상.
N_MELS: int = 64  # 가정: YAMNet 64-mel 관례
N_FFT: int = 400  # 가정: 25ms @ 16kHz (400 samples)
HOP_LENGTH: int = 160  # 가정: 10ms @ 16kHz (160 samples)
FMIN_HZ: float = 0.0
FMAX_HZ: float = 8000.0  # Nyquist (16kHz/2)
MEL_POWER: float = 2.0  # power 멜(에너지). cosine 국소거리가 스케일 불변이라 dB 미변환.

# ── DTW 거리 ──
COSINE_EPS: float = 1e-8  # 근사-무음 프레임 0-division 가드
FASTDTW_RADIUS: int = 10  # fastdtw 백엔드 사용 시 근사 반경(설치 시에만)
# DTW 비용 상한 가드: 프레임수 T가 과대하면 순수 DTW가 O(T^2)로 느려짐 → 중앙 크롭.
# 3s 조각(≈300프레임)은 통과, 과장 길이만 절단. 절단 시 experiment가 로그로 명시.
MAX_TEMPLATE_FRAMES: int = 400  # 가정(런타임 가드): 10ms hop 기준 ≈4초

# ── 분리 지표 / 판정 ──
PRETEST_MARGIN: float = 8.42  # pretest 분리 마진(카테고리 근거) — 실측 정합 비교 기준
# GO 권고 임계(Cohen's d류). 0.8=large. 강한 분리 확신선을 보수적으로 2.0.
# ★ 이건 권고 가이드지 확정 임계 아님 — 실 임계 스윕/튜닝은 11~12주차.
GO_MARGIN_MIN: float = 2.0  # 가정(권고): margin ≥ 2.0 → 알고리즘 GO 신호

# ── 실험 샘플링 상한(런타임 유계화 — 초과분은 experiment가 로그로 명시, silent 절단 금지) ──
MAX_INTRA_PAIRS_PER_GROUP: int = 3  # 그룹당 intra쌍 상한(조합 폭발 억제)
MAX_INTER_PAIRS: int = 400  # inter쌍 총 상한
RANDOM_SEED: int = 0  # 결정적 샘플링(재현 가능)

# ── 라벨 (카테고리 4 predicted_class enum과 정합; 이 스파이크는 doorbell 전용) ──
TARGET_CLASS: str = "doorbell"  # 01_clips 하위 폴더명 = 실험 대상 클래스
