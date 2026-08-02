"""서버 ML 추론 서빙 조기경보 하네스 (standalone, 8주차 선제 de-risk).

★ 이 패키지는 원래 라이브 Flask 앱(`server/app`)과 분리된 standalone 실험 번들로 출발했으나,
   PR #28(`a0b87a2`)부터 `server/app/routes.py`가 `inference.audio_decode`·`inference.constants`를
   직접 import하고 `server/app/model_serving.py`가 `inference.model_runner.ModelRunner`를 lazy
   import한다(카테고리 6.2) → 더 이상 무영향 standalone 아님, 라이브 `/detect` 실추론 경로의 일부다.
   TensorFlow 는 여전히 **모듈 import 시 로드하지 않고** `ModelRunner` 인스턴스화 시점에만
   lazy import 한다(model_runner.py 참조).

실행(모두 `server/` 디렉터리에서):
  python3 -m inference.make_dummy_savedmodel --out-dir /tmp/dummy_savedmodel
  python3 -m inference.bench_inference --model-path /tmp/dummy_savedmodel
  python3 -m unittest inference.tests.test_inference_contract

★ 스코프 = 1층(합성 더미로 코드 경로만 검증). 실 RSS·지연 숫자는 학부생 로컬(2층,
  실 SavedModel `--model-path`) / 11주차 EC2(3층)에서 확정. 더미 산출 숫자는 무의미.
"""
