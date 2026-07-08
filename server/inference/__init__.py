"""서버 ML 추론 서빙 조기경보 하네스 (standalone, 8주차 선제 de-risk).

★ 이 패키지는 라이브 Flask 앱(`server/app`)과 분리된 standalone 실험 번들이다.
   `server/app`(routes.py 등)은 이 패키지를 import 하지 않는다 → 라이브 `/detect`
   mock 경로 무영향(데모 보호). TensorFlow 는 여기서도 **모듈 import 시 로드하지 않고**
   `ModelRunner` 인스턴스화 시점에만 lazy import 한다(model_runner.py 참조).

실행(모두 `server/` 디렉터리에서):
  python3 -m inference.make_dummy_savedmodel --out-dir /tmp/dummy_savedmodel
  python3 -m inference.bench_inference --model-path /tmp/dummy_savedmodel
  python3 -m unittest inference.tests.test_inference_contract

★ 스코프 = 1층(합성 더미로 코드 경로만 검증). 실 RSS·지연 숫자는 학부생 로컬(2층,
  실 SavedModel `--model-path`) / 11주차 EC2(3층)에서 확정. 더미 산출 숫자는 무의미.
"""
