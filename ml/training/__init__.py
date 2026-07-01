"""YAMNet transfer-learning 학습 스크립트 골격 (05_final_dataset → 3-class 분류).

decisions.md 카테고리 4·5 SSoT:
  - backbone = YAMNet(16kHz mono waveform → 1024-d embedding), **frozen**(고정 특징추출기).
  - head    = Dense(3) softmax (필요시 Dense(128)+dropout 중간층), **trainable**.
  - 라벨 인덱스 순서 = ml.pipeline.config.CLASSES 단일 출처(추론 불일치 방지).

실제 학습은 학부생 로컬(EPERM: repo 밖 실데이터). repo 안에서는 합성 더미로 관통 검증만.
"""
