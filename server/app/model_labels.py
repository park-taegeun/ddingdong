"""기동 시 모델 라벨 순서 가드 — run 폴더 labels.json ↔ 서빙 라벨 순서 (사용자 결정 2026-10-16 09:41 KST).

배경(2026-10-13 전 계층 감사): 서버는 MODEL_PATH 상위 run 폴더의 train_config.json(peak_rule)은 읽지만
같은 폴더의 labels.json(학습 실제 클래스 · 순서 — decisions.md 33.16(f) 실행별 단일 출처)은 읽지 않았다.
클래스 개수 불일치는 model_runner 출력 shape 검사가 잡지만 순서 불일치는 못 잡는다 → 순서가 어긋난
모델을 올리면 화재경보 · 초인종 라벨이 뒤바뀐 채 서빙된다. 그래서 모델 로드 전에 순서를 대조한다.

★ 옛 모델 경로: labels.json 이 없으면 WARNING 후 기동 계속(serving_level 옛 모델 규칙과 같은 방식).
  labels.json 은 33.16(f)(PR #80) 이후 학습만 쓰므로, 그 전 run 을 막을 근거가 없다.
★ 그 밖(깨진 JSON · 키 없음 · 형식 틀림 · 순서/개수/이름 불일치 · index 불일치)은 전부 ValueError —
  기본값 fallback 없음. 형식 = ml/training/config.write_labels: {"classes": [...], "index": {클래스: 인덱스}}.
"""

import json
from pathlib import Path

# ml/training/config.LABELS_NAME 복제(서버는 ml 패키지를 import 하지 않는다 — serving_level 선례).
LABELS_NAME = "labels.json"


def resolve_labels(model_path, expected):
    """기동 시 1회(MODEL_PATH 설정 시). → (classes 튜플, False) 일치 / (None, True) 파일 없음(옛 모델).

    위치 규칙 = serving_level.resolve_rule 과 같다(Path(model_path).parent, 심볼릭 링크 resolve 안 함).
    """
    path = Path(model_path).parent / LABELS_NAME
    if not path.is_file():
        return None, True
    expected = tuple(expected)

    def fail(why, actual):
        return ValueError(f"{path}: {why} (기대 {expected}, 실제 {actual!r}) — 라벨 순서 불일치 모델은 기동하지 않습니다.")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise fail(f"JSON 파싱 실패({exc})", None) from exc
    classes = data.get("classes") if isinstance(data, dict) else None
    if not isinstance(classes, list) or not all(isinstance(c, str) for c in classes):
        raise fail('"classes" 가 문자열 리스트가 아님', classes)
    classes = tuple(classes)
    if classes != expected:
        raise fail("classes ≠ 서빙 라벨 순서", classes)
    index = data.get("index")
    if index != {c: i for i, c in enumerate(classes)}:
        raise fail('"index" 가 classes 순서와 다름', index)
    return classes, False
