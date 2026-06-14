"""device_id 단위 rate limit (카테고리 6.1: 5초당 1회).

Phase 2-1 로컬 단일 프로세스 전제의 in-memory 구현이다.
11주차 다중 워커(Gunicorn) 배포 시에는 Redis 등 공유 저장소로 교체해야 한다.
경과 측정은 시스템 시계 변경에 영향받지 않도록 monotonic clock 을 쓴다.
"""

import time
from threading import Lock

from .constants import DEVICE_RATE_LIMIT_SECONDS

_last_allowed = {}  # device_id -> monotonic 시각
_lock = Lock()


def check_and_register(device_id):
    """허용이면 None, 초과면 Retry-After 초(int, >=1) 반환.

    차단된 요청은 타이머를 갱신하지 않는다(고정 윈도우).
    """
    now = time.monotonic()
    with _lock:
        last = _last_allowed.get(device_id)
        if last is not None:
            elapsed = now - last
            if elapsed < DEVICE_RATE_LIMIT_SECONDS:
                return max(1, int(DEVICE_RATE_LIMIT_SECONDS - elapsed) + 1)
        _last_allowed[device_id] = now
    return None
