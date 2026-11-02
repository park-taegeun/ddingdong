"""YAMNet transfer-learning 학습 스크립트 골격 (05_final_dataset → --classes 로 준 클래스 분류).

decisions.md 카테고리 4·5 SSoT:
  - backbone = YAMNet(16kHz mono waveform → 1024-d embedding), **frozen**(고정 특징추출기).
  - head    = Dense(클래스 수) softmax (필요시 Dense(128)+dropout 중간층), **trainable**.
  - 라벨 인덱스 순서 = ml.pipeline.config.CLASSES 순서로 정규화, 실행별로 run labels.json 에 기록.

실제 학습은 학부생 로컬(EPERM: repo 밖 실데이터). repo 안에서는 합성 더미로 관통 검증만.
  [현재값 2026-11-02 — 근거 = decisions.md 5.1 · 33.8] EPERM은 옛 형제 폴더 위치의 사정이다 — 실데이터는
  학부생 홈으로 옮겼고(5.1), 지금 repo 안에서 실학습이 안 도는 이유는 데이터가 repo 밖이고
  `--data-root` 또는 `DDINGDONG_DATA_ROOT`가 필수(기본값 없음 — PR #60)이기 때문이다.
"""
