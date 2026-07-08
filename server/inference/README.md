# server/inference — 추론 서빙 조기경보 하네스

서버 ML 추론(YAMNet+TF)이 **t3.small(2GB)에 메모리 fit** 되는지 + **추론 지연이 5초
예산** 안인지를 8주차에 미리 죽이기 위한 standalone 번들. 라이브 `/detect`(mock) 무수정.

> ⚠️ **스코프 3층** — 이 PR은 **1층**(합성 더미로 코드 경로만 검증, 숫자 무의미)만 한다.
> - **1층 (이 PR, 지금)**: 합성 더미 SavedModel → 코드 경로 검증.
> - **2층 (학부생 로컬 M4 venv)**: 실 SavedModel 로 RSS·M4 지연 실측 (아래 커맨드).
> - **3층 (11주차 EC2)**: 진짜 t3.small 지연 확정.

## 구성
| 파일 | 역할 |
|---|---|
| `constants.py` | 매직넘버 SSoT (SAMPLE_RATE / MEM_BUDGET_MB / LATENCY_BUDGET_MS 등) |
| `audio_decode.py` | PCM int16 LE mono → float32 waveform `(1, N)` (계약 = **가정**, 아래) |
| `model_runner.py` | SavedModel **lazy-load**(TF import = 인스턴스화 시점) + `predict → (1,3)` |
| `make_dummy_savedmodel.py` | 실모델 없이 시그니처 일치 random 스텁 생성 |
| `bench_inference.py` | RSS 4-체크포인트 분해 + 지연 p50/p95 + verdict |
| `tests/test_inference_contract.py` | decode/predict 계약 + 에러케이스 |

## 오디오 계약 (★ 가정 — ASSUMPTION)
라이브 `/detect`는 현재 **mock-only** → 오디오 바이트를 받지 않아 wire 계약이 코드에 미정의.
아래는 카테고리 4(16kHz mono waveform) + 33.2(입력 `(1,None)` f32) + ml/pipeline
`SAMPLE_RATE=16000` + PCM 관행(int16 LE)에서 추론한 합리적 기본값이다.

| 항목 | 값 |
|---|---|
| 인코딩 | PCM signed 16-bit, **little-endian** |
| 채널 | mono (1ch) |
| 샘플레이트 | 16000 Hz |
| 정규화 | `int16 / 32768.0` → `[-1, 1]` float32 |
| 출력 shape | `(1, N)` (배치 1 고정, 카테고리 33.2) |

wire envelope(multipart / base64-in-JSON / raw body)는 **11주차 ESP32 통합에서 확정**.
`audio_decode`는 transport-agnostic(이미 디코딩된 `bytes`만 받음).

## 실행 (모두 `server/` 디렉터리에서)
```bash
# 계약 테스트 (numpy 만 필요; TF 없으면 predict 테스트 skip)
python3 -m unittest inference.tests.test_inference_contract -v

# 더미로 벤치 (숫자 무의미 — 코드 경로 확인용)
python3 -m inference.bench_inference

# ★ 2층: 실 SavedModel 로 RSS·지연 실측 (학부생 로컬 M4 venv)
python3 -m inference.bench_inference --model-path <ml/models/yamnet/inference_savedmodel>
```

## verdict 해석
- `메모리 peak … / 2048MB 예산` — peak RSS 가 t3.small 예산 안인가. TF import 가 대부분
  점유(체크포인트 Δ 참조) → 초과 시 **TFLite 변환**이 유일한 실질 카드.
- `지연 p95 … / 5000ms 예산` — 단일 추론이 1차 알림 ≤5초 예산 안인가.
- **gunicorn COW**: 워커 2개(`preload_app=True`)는 모델 페이지를 copy-on-write 공유 →
  실메모리 ≈ 1×모델 + 2×오버헤드(2×모델 아님). peak 는 워커 1개 기준 하한.
