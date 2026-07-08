"""오디오 바이트 → YAMNet 입력 waveform 디코딩 계약.

★★ 가정(ASSUMPTION — 코드 추론 + 위임 명시, §5 Step1 escape valve) ★★
라이브 `/detect`(server/app/routes.py)는 현재 **mock-only**: `client_request_id`·
`device_id` JSON 만 수신하고 **오디오 바이트를 받지 않는다** → HTTP wire 오디오 계약이
코드에 **미정의**. 아래 디코딩 계약은 추측이 아니라 다음 근거의 '합리적 기본값'이다:
  - 카테고리 4: raw waveform 16kHz mono → YAMNet
  - 카테고리 33.2: 서빙 입력 waveform (1, None) float32
  - ml/pipeline SAMPLE_RATE=16000 (파이프라인 전역)
  - PCM 관행: 마이크 raw 캡처의 사실상 표준 = int16 little-endian
wire envelope(multipart / base64-in-JSON / raw body) 자체는 11주차 ESP32 통합에서
확정 → 본 모듈은 **transport-agnostic**(이미 디코딩된 `bytes` 만 받음).

계약: PCM int16 little-endian, mono, 16kHz → np.float32 waveform (1, N), 범위 [-1, 1].
"""

from __future__ import annotations

import numpy as np

from .constants import BYTES_PER_SAMPLE, NORM_DIVISOR, PCM_DTYPE, SAMPLE_RATE


def decode_pcm16(data: bytes, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """PCM int16 LE mono 바이트 → float32 waveform (1, N), [-1, 1].

    Args:
        data: raw PCM 바이트(int16 little-endian, mono). 길이는 2의 배수여야 함.
        sample_rate: 호출자가 단언하는 샘플레이트. SSoT(16000)와 불일치 시 거부
            (PoC 단계 리샘플 미지원 — 계약 위반을 조용히 삼키지 않음).

    Returns:
        np.float32 배열, shape (1, N), N = len(data)//2, 값 범위 [-1, 1].

    Raises:
        ValueError: 빈 데이터 / int16 미정렬(홀수 바이트) / 샘플레이트 불일치.
    """
    if sample_rate != SAMPLE_RATE:
        raise ValueError(
            f"샘플레이트 불일치: {sample_rate} != 계약 {SAMPLE_RATE} "
            "(PoC 단계 리샘플 미지원 — 16kHz mono 로 캡처/전송 필요)."
        )
    if len(data) == 0:
        raise ValueError("빈 오디오 데이터: 최소 int16 샘플 1개(2바이트) 필요.")
    if len(data) % BYTES_PER_SAMPLE != 0:
        raise ValueError(
            f"int16 미정렬: 바이트 길이 {len(data)} 가 {BYTES_PER_SAMPLE}의 배수가 아님 "
            "(PCM int16 little-endian mono 가정 위반)."
        )

    # frombuffer 는 read-only view → astype 로 복사(쓰기 가능 float32) + 정규화
    samples = np.frombuffer(data, dtype=PCM_DTYPE).astype(np.float32) / NORM_DIVISOR
    # 서빙 시그니처 배치 1 고정 (카테고리 33.2: (1, None))
    return samples.reshape(1, -1)
