"""파이프라인 전역 설정 — decisions.md 카테고리 4·5 SSoT 상수화.

경로 하드코딩 금지: DATA_ROOT는 환경변수 `DDINGDONG_DATA_ROOT` 또는 CLI로 주입.
증강 파라미터는 전부 카테고리 5 값 그대로 상수화(매직넘버 금지).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# 클래스 (카테고리 4 enum) — 코드 식별자는 영문 표기 고정.
# 한글 "초인종" 등은 UI 전용, 파이프라인 코드/폴더는 아래 영문만 사용.
# --------------------------------------------------------------------------
CLASSES: tuple[str, ...] = ("doorbell", "knock", "fire_alarm")

# --------------------------------------------------------------------------
# 오디오 규격 (카테고리 4: YAMNet 입력 = raw waveform 16kHz mono)
# --------------------------------------------------------------------------
SAMPLE_RATE: int = 16_000
CHANNELS: int = 1  # mono
OUTPUT_SUBTYPE: str = "PCM_16"  # Int16 저장 (입력 클립과 동일 규격)

# 전처리 정규화 정책
#   - peak 정규화: 클립 최대 진폭을 TARGET_PEAK 로 스케일(클리핑 방지·볼륨 편차 완화)
#   - 길이 정책: PRESERVE(원본 길이 유지). YAMNet은 가변 길이 waveform을 내부
#     0.96s 프레임으로 처리하므로 강제 trim/pad 불필요. 고정 길이가 필요하면
#     FIXED_DURATION_SEC 를 float로 지정(그 경우 짧으면 zero-pad, 길면 앞에서 trim).
PEAK_NORMALIZE: bool = True
TARGET_PEAK: float = 0.95  # linear (≈ -0.45 dBFS)
FIXED_DURATION_SEC: float | None = None  # None = 원본 길이 유지

# 최소 유효 길이 가드 (매직넘버 금지 — 상수화).
#   근거: 01_clips 원본 중 길이 0.0초 빈 wav 6개(AI Hub S_103, fire_alarm)가
#   preprocess를 무검증 통과 → augment 의 pink-noise FFT(np.fft.rfft, 길이 0)에서
#   "Invalid number of FFT data points (0)" 크래시. 하류 전체를 방어하기 위해
#   preprocess 단계에서 초단파/빈 클립을 skip 한다. 정상 클립(대다수 수 초)엔 무영향.
MIN_DURATION_SEC: float = 0.1  # 이보다 짧은 클립은 학습에 무의미 → skip
MIN_SAMPLES: int = int(round(MIN_DURATION_SEC * SAMPLE_RATE))  # 파생: 0.1s × 16k = 1600

# --------------------------------------------------------------------------
# 증강 파라미터 (카테고리 5 — 정확히 이 값. train split에만 적용)
# --------------------------------------------------------------------------
TIME_STRETCH_RATES: tuple[float, ...] = (0.85, 1.15)
VOLUME_GAIN_DB: float = -6.0

# BG noise SNR: 클래스별 (낮은 SNR = 잡음 강함). 초인종·노크 10/20dB, 화재 25/35dB.
BG_NOISE_SNR_DB: dict[str, tuple[float, ...]] = {
    "doorbell": (10.0, 20.0),
    "knock": (10.0, 20.0),
    "fire_alarm": (25.0, 35.0),
}
# 실제 배경소음 파일 디렉토리(있으면 그 wav들을 잡음 소스로 사용). None이면 합성 잡음.
BG_NOISE_DIR: Path | None = None
BG_NOISE_KIND: str = "pink"  # 합성 잡음 종류: "pink" | "white"

# pitch shift ±2 semitone — 카테고리 5: "한국 환경음만".
# 소스 태그를 클립 파일명만으로 판별할 수 없음 → MODE 로 적용 대상을 명시 분리.
#   "korean_only": KOREAN_SOURCE_MARKERS 중 하나가 파일명(stem)에 포함된 클립에만 적용.
#                  마커가 비어 있으면 대상 0 → 경고 로그 + 학부생 결정 트리거(막힘 섹션 9).
#   "all"        : 전 클립에 적용(태그 무시).
#   "none"       : pitch shift 미적용.
PITCH_SHIFT_SEMITONES: tuple[float, ...] = (-2.0, 2.0)
PITCH_SHIFT_MODE: str = "korean_only"
# 한국 환경음 소스를 나타내는 파일명 부분 문자열(예: AI Hub S_103 → "S_103").
# 학부생이 실제 소스 명명 규칙 확인 후 채워야 pitch shift가 대상에 적용됨.
KOREAN_SOURCE_MARKERS: tuple[str, ...] = ()

# --------------------------------------------------------------------------
# SpecAugment (카테고리 5) — ★ waveform 단계에서 굽지 않음.
# 스펙트로그램 마스킹이라 학습 시점(2번 학습 스크립트) 적용. 여기선 파라미터만 기록.
# --------------------------------------------------------------------------
SPECAUGMENT: dict[str, object] = {
    "freq_mask_param": 10,
    "time_mask_param": 5,
    "applied_at": "training",  # NOT this pipeline
}

# 클래스 불균형 (카테고리 5) — 증강 배수 폭주 대신 가중치. 학습 스크립트가 소비.
SAMPLE_WEIGHT_RANGE: tuple[float, float] = (1.5, 2.0)  # 한국 환경음 가중

# --------------------------------------------------------------------------
# 분할 (카테고리 5: "파일 단위 분할, data leakage 방지")
#   ★ 실제 요구 = 원본(source) 단위 그룹 분할. 한 원본 오디오를 3초 간격으로 자른
#     조각(piece) 클립이 다수 존재(파일 stem 끝에 `_`+7자리 조각 인덱스: _0000000,
#     _0003000, ...). 같은 원본의 조각이 train/val/test 로 흩어지면 leakage → 반드시
#     원본 단위로 통째 배정해야 "파일 단위 분할, leakage 방지"의 실제 의도를 충족.
#   계획 배분 train1954/val434/test410 은 참고값. 실제는 비율 + 재현 seed.
# --------------------------------------------------------------------------
SPLIT_RATIO: tuple[float, float, float] = (0.70, 0.15, 0.15)  # train / val / test
SEED: int = 42

# 조각(piece) suffix 파싱 규칙 — 원본(source) 단위 그룹 분할의 핵심(매직넘버/정규식 금지).
#   규칙: 파일 stem 맨 끝의 `_` + 7자리 조각 인덱스(`_\d{7}$`) 하나만 제거한 나머지 = source key.
#   ★ 끝 앵커($) 필수 — 회귀 위험 최상위: 중간 숫자 블록(AI Hub `..._S_103_C_001_0001_...`)
#     이나 소수점 좌표(AudioSet `_30.0_40.0`)를 절대 건드리지 말고, 맨 끝 조각 인덱스
#     "딱 하나"만 제거한다.
PIECE_SUFFIX_PATTERN: re.Pattern[str] = re.compile(r"_\d{7}$")


def source_key(stem: str) -> str:
    """파일 stem → 원본(source) key. 맨 끝 조각 suffix(`_\\d{7}$`) 하나만 제거.

    - 조각 suffix 가 없는 단일 클립(조각 안 된 원본)은 stem 전체가 곧 source key
      (그룹 1개, 에러 아님).
    - ★ 반드시 **stem 문자열에 직접** 적용할 것. AudioSet `..._30.0_40.0_0000000`
      처럼 점(.)이 든 이름을 `Path(stem).stem` 으로 재처리하면 마지막 점 뒤를 확장자로
      오인해 `..._30.0_40` 로 잘린다(실측 확인). 여기선 Path 를 다시 씌우지 않고
      정규식만 적용해 그 함정을 회피한다. 호출부는 `p.stem`(확장자 .wav 제거된
      값, 점은 보존)을 그대로 넘긴다.
    """
    return PIECE_SUFFIX_PATTERN.sub("", stem, count=1) or stem

# --------------------------------------------------------------------------
# 데이터 루트 (외부 형제 폴더 — Claude Code는 OS TCC로 접근 불가. config 값으로만.)
# 실제 실행은 학부생이 자기 셸에서 DDINGDONG_DATA_ROOT 지정.
# --------------------------------------------------------------------------
DEFAULT_DATA_ROOT = (
    "/Users/xorms/Desktop/서경대학교/시험 준비/26-1/공학종합설계1/"
    "ML 학습 데이터/ddingdong_dataset"
)

# 스테이지 폴더명 (실측 확정된 실제 폴더 구조와 1:1)
DIR_CLIPS = "01_clips"          # 입력(원본 2,798 클립)
DIR_PREPROCESSED = "02_preprocessed"
DIR_AUGMENTED = "03_augmented"
DIR_FINAL = "05_final_dataset"  # train/val/test
DIR_MANIFESTS = "manifests"     # split/final manifest CSV 저장
# ★ 파이프라인이 절대 건드리지 않는 폴더: 00_source_raw / 01_extracted / 04_direct_recording


@dataclass(frozen=True)
class Paths:
    """DATA_ROOT 기준 스테이지 경로 묶음."""

    root: Path
    clips: Path
    preprocessed: Path
    augmented: Path
    final: Path
    manifests: Path

    def split_dir(self, split: str) -> Path:
        return self.final / split


def resolve_data_root(data_root: str | os.PathLike | None = None) -> Path:
    """우선순위: 명시 인자 > 환경변수 DDINGDONG_DATA_ROOT > DEFAULT_DATA_ROOT."""
    raw = data_root or os.environ.get("DDINGDONG_DATA_ROOT") or DEFAULT_DATA_ROOT
    return Path(raw).expanduser()


def resolve_paths(data_root: str | os.PathLike | None = None) -> Paths:
    root = resolve_data_root(data_root)
    return Paths(
        root=root,
        clips=root / DIR_CLIPS,
        preprocessed=root / DIR_PREPROCESSED,
        augmented=root / DIR_AUGMENTED,
        final=root / DIR_FINAL,
        manifests=root / DIR_MANIFESTS,
    )
