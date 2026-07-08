"""초인종 개인식별 알고리즘 리스크 스파이크 (SP/DTW + cosine).

decisions.md 카테고리 4("초인종 개인 등록 = 멜스펙트로그램 2D 템플릿 + FastDTW
SP/DTW + cosine distance") · 카테고리 26.3 진입점 2("옆집 초인종 잘못 반응 X" USP)
의 **알고리즘 되냐/안 되냐**를 8주차에 선제 검증하는 격리 스파이크.

★ 스코프 경계 (엄수):
  - 이 패키지는 **분리 가능성 실증 + 마진 숫자 + GO/NO-GO 권고**만 낸다.
    프로덕션 매칭 모듈·임계값 튜닝·서버 통합은 11~12주차 몫(본구현 아님).
  - 서버/파이프라인/라이브 배선 일절 없음. ml.pipeline/ml.training 미import(격리).
  - ★ 실 거리 숫자는 반드시 학부생 로컬(2층)에서 실 클립으로 재실행해야 유효.
    이 세션(MCP)이 낸 숫자는 전부 합성(1층) → 코드 경로 검증용, 값 자체는 무의미.

구성:
  constants.py   — 매직넘버 SSoT (SAMPLE_RATE / N_MELS / 임계값 / PRETEST_MARGIN)
  features.py    — wav → power-mel 2D 템플릿 (T, n_mels)  [librosa]
  distance.py    — dtw_cosine(template, query) -> float  [numpy DTW, fastdtw 옵션]
  experiment.py  — intra(같은 초인종) vs inter(다른 초인종) 분리 실험 + 마진 + EER
  synth_smoke.py — 실데이터 없이 합성 템플릿 E2E (스코프 1층 스모크)
"""
