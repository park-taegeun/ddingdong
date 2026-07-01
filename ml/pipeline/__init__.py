"""ddingdong ML 데이터 파이프라인.

01_clips → 02_preprocessed → (파일단위 split) → 03_augmented(train만) → 05_final_dataset.

decisions.md 카테고리 4·5 SSoT 기반. 오디오는 waveform(16kHz mono) 유지 —
멜스펙트로그램/ SpecAugment 변환은 학습 스크립트 몫(카테고리 4).
"""
