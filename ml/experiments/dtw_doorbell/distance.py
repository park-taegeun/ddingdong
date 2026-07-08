"""DTW + cosine 국소거리 (카테고리 4: FastDTW SP/DTW + cosine distance).

primary = 순수 numpy 정확 DTW(외부 의존 0 — numpy만). fastdtw 설치 시 근사 백엔드
선택 가능(긴 시퀀스 가속). §9 규율: fastdtw 미설치가 정지 사유 아님 → 폴백으로 완주.

국소거리 = 프레임간 cosine distance (1 - cos_sim). L2 정규화 후라 진폭 스케일 불변
→ 같은 초인종의 볼륨/거리 차이에 강건(카테고리 4 설계 의도).
"""

from __future__ import annotations

import numpy as np

from .constants import COSINE_EPS, FASTDTW_RADIUS, MAX_TEMPLATE_FRAMES

try:
    import fastdtw as _fastdtw_mod  # noqa: F401

    _HAS_FASTDTW = True
except Exception:  # noqa: BLE001 (미설치 → 폴백)
    _HAS_FASTDTW = False


def has_fastdtw() -> bool:
    """fastdtw 설치 여부(리포트/백엔드 선택용)."""
    return _HAS_FASTDTW


def _l2_normalize(mat: np.ndarray, eps: float = COSINE_EPS) -> np.ndarray:
    """행별 L2 정규화 (근사-무음 프레임은 eps로 가드)."""
    norms = np.sqrt(np.sum(mat * mat, axis=1, keepdims=True))
    return mat / np.maximum(norms, eps)


def _clip_frames(template: np.ndarray, max_frames: int = MAX_TEMPLATE_FRAMES) -> np.ndarray:
    """프레임수 상한 가드(O(T^2) DTW 유계화). 초과 시 중앙 크롭."""
    t = template.shape[0]
    if t <= max_frames:
        return template
    start = (t - max_frames) // 2
    return template[start : start + max_frames]


def _cost_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """cosine 국소거리 행렬 (Ta, Tb) = 1 - cos_sim. power-mel 비음수 → [0, 1]."""
    an = _l2_normalize(a)
    bn = _l2_normalize(b)
    sim = an @ bn.T  # (Ta, Tb)
    return 1.0 - sim


def _dtw_exact(cost: np.ndarray) -> float:
    """비용행렬 위 정확 DTW 누적 → 경로비용. (Ta+Tb) 정규화된 값 반환."""
    ta, tb = cost.shape
    acc = np.full((ta + 1, tb + 1), np.inf, dtype=np.float64)
    acc[0, 0] = 0.0
    for i in range(1, ta + 1):
        ci = cost[i - 1]
        row = acc[i]
        prev = acc[i - 1]
        for j in range(1, tb + 1):
            row[j] = ci[j - 1] + min(prev[j], row[j - 1], prev[j - 1])
    return float(acc[ta, tb] / (ta + tb))


def _dtw_fastdtw(a: np.ndarray, b: np.ndarray) -> float:
    """fastdtw 근사 백엔드. cosine 국소거리, 경로길이 정규화."""
    from fastdtw import fastdtw
    from scipy.spatial.distance import cosine

    an = _l2_normalize(a)
    bn = _l2_normalize(b)
    dist, path = fastdtw(an, bn, radius=FASTDTW_RADIUS, dist=cosine)
    return float(dist / max(1, len(path)))


def dtw_cosine(
    template: np.ndarray, query: np.ndarray, *, backend: str = "auto"
) -> float:
    """두 멜 템플릿 (T, n_mels) 간 DTW-cosine 거리(정규화). 작을수록 유사.

    backend: "auto"(fastdtw 있으면 사용) / "exact"(순수 numpy) / "fastdtw".
    """
    if template.ndim != 2 or query.ndim != 2:
        raise ValueError("템플릿은 2D (T, n_mels) 여야 함")
    if template.shape[1] != query.shape[1]:
        raise ValueError(
            f"mel 차원 불일치: {template.shape[1]} vs {query.shape[1]}"
        )
    a = _clip_frames(np.asarray(template, dtype=np.float32))
    b = _clip_frames(np.asarray(query, dtype=np.float32))

    resolved = backend
    if resolved == "auto":
        resolved = "fastdtw" if _HAS_FASTDTW else "exact"
    if resolved == "fastdtw":
        return _dtw_fastdtw(a, b)
    if resolved == "exact":
        return _dtw_exact(_cost_matrix(a, b))
    raise ValueError(f"알 수 없는 backend: {backend}")
