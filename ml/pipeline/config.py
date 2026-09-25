"""파이프라인 전역 설정 — decisions.md 카테고리 4·5 SSoT 상수화.

경로 하드코딩 금지: DATA_ROOT는 환경변수 `DDINGDONG_DATA_ROOT` 또는 CLI로 주입.
증강 파라미터는 전부 카테고리 5 값 그대로 상수화(매직넘버 금지).
"""

from __future__ import annotations

import os
import re
import shutil
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
# 한국 환경음 소스 = 직접녹음 클립만(파일명 부분 문자열 매칭). decisions.md 33.3-①(PoC-24) 확정:
#   · 대상 = 직접녹음만, S_103(AI Hub 화재) 제외 — 최약 클래스 doorbell 수혜 + 규격 화재음 왜곡 회피.
#   · 위상 = 보조 수단(doorbell 성능의 실제 지렛대는 직접녹음 절대량, 8주차 유입 후 실효).
#   · 마커 = 클래스별(decisions.md 5.3(b)). 부분 문자열 매칭이라 `("direct_",)` 로 켜면
#     직접녹음 화재경보(`direct_fire_alarm_…`)까지 pitch 대상이 되어 위 「규격 화재음 왜곡
#     회피」와 충돌한다 ⇒ 초인종·노크 직접녹음만 겨눈다. AI Hub(S_103)는 prefix 가 없어 미포함.
#   · 직접녹음 클립이 train 에 아직 없으면 대상 0 이다(마커는 세팅돼 있다).
KOREAN_SOURCE_MARKERS: tuple[str, ...] = ("direct_doorbell_", "direct_knock_")

# --------------------------------------------------------------------------
# SpecAugment (카테고리 5) — ★ waveform 단계에서 굽지 않음.
# 스펙트로그램 마스킹이라 학습 시점(2번 학습 스크립트) 적용. 여기선 파라미터만 기록.
# --------------------------------------------------------------------------
SPECAUGMENT: dict[str, object] = {
    "freq_mask_param": 10,
    "time_mask_param": 5,
    "applied_at": "training",  # NOT this pipeline
}

# 클래스 불균형 (카테고리 5) — 학습에 걸리는 것은 `ml/training/data.compute_class_weights`
#   = sklearn `balanced`(n_total / (n_classes · n_c)) 자동 산출뿐이다.
# SAMPLE_WEIGHT_RANGE(한국 환경음 1.5~2.0배)는 제거 — 카테고리 5 「구현하지 않는다」(2026-09-23 결정).

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

# 직접녹음 그룹 키 규칙 — decisions.md 5.2(b) 실측: `direct_{클래스}_{유닛}_{테이크}` 는
#   끝이 2자리라 PIECE_SUFFIX_PATTERN(`_\d{7}$`)에 걸리지 않아 **테이크 1개 = source 1개**로
#   흩어졌다. 같은 유닛(같은 초인종)을 다시 누른 테이크는 사실상 같은 원본이므로 train 과
#   val/test 로 갈리면 누수다 ⇒ 유닛까지를 그룹 키로 삼는다(사용자 결정 D3, 2026-09-21).
#   규칙은 `ml/experiments/dtw_doorbell` 의 `unit_id()`(맨 끝 `_\d+` 하나 제거)와 같은 결과를
#   내도록 맞췄다 — 그쪽은 파일명(`.wav` 포함), 여기는 stem 이라는 차이뿐이다.
DIRECT_RECORDING_PREFIX: str = "direct_"
DIRECT_TAKE_PATTERN: re.Pattern[str] = re.compile(r"_\d+$")


def source_key(stem: str) -> str:
    """파일 stem → 원본(source) key. 맨 끝 조각 suffix(`_\\d{7}$`) 하나만 제거.

    - 조각 suffix 가 없는 단일 클립(조각 안 된 원본)은 stem 전체가 곧 source key
      (그룹 1개, 에러 아님).
    - ★ 반드시 **stem 문자열에 직접** 적용할 것. AudioSet `..._30.0_40.0_0000000`
      처럼 점(.)이 든 이름을 `Path(stem).stem` 으로 재처리하면 마지막 점 뒤를 확장자로
      오인해 `..._30.0_40` 로 잘린다(실측 확인). 여기선 Path 를 다시 씌우지 않고
      정규식만 적용해 그 함정을 회피한다. 호출부는 `p.stem`(확장자 .wav 제거된
      값, 점은 보존)을 그대로 넘긴다.
    - 직접녹음(`direct_` prefix)은 조각 suffix 제거 **후** 남은 끝 `_{테이크}`(`_\\d+$`)를
      한 번 더 제거해 **유닛**을 그룹 키로 삼는다(D3). 공개데이터 stem 은 이 분기를 타지
      않으므로 기존 배정 규칙 무변경이다. 33.3① KOREAN_SOURCE_MARKERS 는 별개 축이며
      여기서 건드리지 않는다.
    """
    key = PIECE_SUFFIX_PATTERN.sub("", stem, count=1) or stem
    if key.startswith(DIRECT_RECORDING_PREFIX):
        key = DIRECT_TAKE_PATTERN.sub("", key, count=1) or key
    return key

# --------------------------------------------------------------------------
# 데이터 루트 — **기본값 fallback 없음**. 명시 인자 또는 env DDINGDONG_DATA_ROOT 필수.
#   근거: decisions.md 카테고리 5 「실 파이프라인·학습 실행 = 학부생 로컬 셸
#   (`DDINGDONG_DATA_ROOT="…" python -m ml.pipeline.run_all`)」 — env 주입이 이미 정본
#   관용구로 등재돼 있다. 새 정책이 아니라 코드를 등재된 정책에 맞춘 것.
#   ★ 여기 있던 DEFAULT_DATA_ROOT 는 repo 밖 형제 폴더, 곧 카테고리 5가 「OS TCC(EPERM)로
#     접근 차단 → 학부생 홈으로 이동 확정」이라 적은 **옛 위치**를 가리킨 채 방치됐다.
#     아무도 부딪히지 않은 이유는 fallback 이 틀린 값을 조용히 흘려보냈기 때문 —
#     그래서 값을 고치는 대신 fallback 자체를 제거한다.
# --------------------------------------------------------------------------
DATA_ROOT_ENV = "DDINGDONG_DATA_ROOT"

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
    """우선순위: 명시 인자 > 환경변수 DDINGDONG_DATA_ROOT. **둘 다 없으면 즉시 실패.**

    - 예외 종류 = ValueError. 이 모듈은 라이브러리이지 진입점이 아니다(호출자 =
      run_all.main / ml.training.config.resolve_final_dir / 테스트). 종료 코드를 직접
      정하는 SystemExit 은 호출자의 몫을 뺏는다. 같은 파일의 clean_stage_class_dirs
      거부가 이미 ValueError 를 쓰므로 in-file 관용구와도 일치한다.
    - **경로 존재 여부는 검사하지 않는다**(의도): run_all.run() 이 이미 `01_clips` 부재를
      FileNotFoundError 로 잡고, 학습 경로는 05_final_dataset 부재로 잡는다. 여기서 또
      검사하면 가드가 둘로 갈려 메시지 출처만 흐려진다. 이 함수의 계약은 「경로를 받았는가」
      하나로 유지한다.
    - `.expanduser()` 는 기존 계약 — `~` 기반 주입(정본 관용구)이 그대로 동작해야 한다.
    """
    raw = data_root if data_root is not None else os.environ.get(DATA_ROOT_ENV, "")
    if not str(raw).strip():
        raise ValueError(
            "데이터 루트가 지정되지 않았습니다 — 기본값 fallback 은 의도적으로 없습니다.\n"
            f"  → 환경변수 {DATA_ROOT_ENV} 를 '{DIR_CLIPS}' 상위 폴더로 지정하거나 "
            "--data-root 로 넘기세요.\n"
            f'  예: {DATA_ROOT_ENV}="~/ML 학습 데이터/ddingdong_dataset" '
            "python -m ml.pipeline.run_all"
        )
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


def clean_stage_class_dirs(stage_dir: Path, expected_name: str) -> list[Path]:
    """스테이지(02/03) 재생성 전 클래스 하위폴더를 비운다(stale 잔재 제거).

    배경: preprocess/augment 는 산출물을 save_wav 로 덮어쓸 뿐 기존 파일을 지우지 않는다.
    → 가드 도입 이전(PR#10)에 02 로 흘러든 빈 클립 6개(AI Hub S_103)가 재실행해도
    남아, split 이 02(=1642 신규 + 6 stale = 1648)를 읽어 05 로 부활 → data.py 빈 waveform
    크래시. 05 의 clean_final 과 동일한 idiom 을 02/03 에도 적용해 stale 을 원천 제거한다.

    ★ 안전 가드(카테고리 7: 상위/원본/manifest 절대 삭제 금지 — clean_final 과 동일):
      - stage_dir 폴더명이 정확히 expected_name(02/03)일 때만 동작(오폴더 삭제 차단).
      - 삭제 대상은 CLASSES 하위폴더뿐. 각 대상이 정말 stage_dir 직하위인지 resolve 로
        재확인(심볼릭/트래버설 차단). 00_source_raw/01_clips/manifests 절대 불가.
    반환: 실제로 제거된 클래스 폴더 목록.
    """
    if stage_dir.name != expected_name:
        raise ValueError(f"clean 거부: 스테이지 경로명이 {expected_name!r} 아님 → {stage_dir}")
    stage_resolved = stage_dir.resolve()
    removed: list[Path] = []
    for cls in CLASSES:
        target = stage_dir / cls
        if target.resolve().parent != stage_resolved:
            raise ValueError(f"clean 거부: {target} 가 {stage_dir} 직하위가 아님")
        if target.exists():
            shutil.rmtree(target)
            removed.append(target)
    return removed
