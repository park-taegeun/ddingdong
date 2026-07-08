# DTW 초인종 개인식별 스파이크 (SP/DTW + cosine)

발표 USP "우리집 초인종만 반응, 옆집 초인종 무시"(카테고리 26.3 진입점 2)가 **알고리즘
수준에서 실제로 등록 vs 미등록 초인종을 분리하는지**를 8주차에 선제 검증하는 격리 스파이크.
설계 = 카테고리 4("멜스펙트로그램 2D 템플릿 + FastDTW SP/DTW + cosine distance").

> ⚠️ **스코프 = 되냐/안 되냐 판정만.** 프로덕션 매칭 모듈·임계값 튜닝·서버 통합은
> 11~12주차 몫. 여기선 **분리 마진 숫자 + GO/NO-GO 권고**만 낸다.

---

## ★ 채택한 실험 설계 (intra 정의)

`01_clips/doorbell` 파일명 = `{원본ID}_{7자리 offset}.wav`. 실측:
**436 클립 → 182 원본 그룹**(AudioSet-style 85 + FSD50K-style 97), **119 그룹이 조각 ≥2**.

- **intra쌍 (같은 초인종)** = 같은 원본ID의 다른 조각
- **inter쌍 (다른 초인종)** = 다른 원본ID 대표끼리

→ 공개데이터에 초인종별 라벨이 없어도 **원본ID 그룹으로 실 intra/inter 확보 가능**
(대체 self/other-augment 설계 불필요, §5 Step1 1순위 경로).

> ### ★★ 반드시 읽을 캐비앗
> intra쌍은 **한 소스 녹음의 인접 조각**이다. 즉 "같은 초인종을 다른 때 다시 누른"
> 독립 재녹음이 **아니라** 같은 녹음의 이웃 구간 → **실제 재-누름 변동보다 낙관적**.
> 따라서 여기 마진은 **상한 근사(optimistic bound)**. 진짜 판정은 학부생
> 직접녹음(`04_direct_recording`, 카테고리 5: 초인종 90개 계획)으로 2층 재검증해야 확정.

---

## 구성
| 파일 | 역할 |
|---|---|
| `constants.py` | 매직넘버 SSoT (SAMPLE_RATE / N_MELS / 임계값 / PRETEST_MARGIN=8.42) |
| `features.py` | wav → power-mel 2D 템플릿 `(T, N_MELS)` (librosa) |
| `distance.py` | `dtw_cosine(template, query)` — 순수 numpy DTW + cosine 국소거리 (fastdtw 옵션) |
| `experiment.py` | intra/inter 분포 + 분리 마진 + 임계 스윕/EER + GO 권고 |
| `synth_smoke.py` | 실데이터 없이 합성 템플릿 E2E (스코프 1층) |
| `tests/test_dtw_contract.py` | DTW/통계/특징 계약 테스트 |

## 멜/DTW 설정 (★ 가정 — 카테고리 4는 세부값 미명시)
| 항목 | 값 | 근거 |
|---|---|---|
| sample_rate | 16000 | 카테고리 4 (확정) |
| n_mels | 64 | 가정: YAMNet 관례 |
| n_fft / hop | 400 / 160 (25ms / 10ms) | 가정: YAMNet 관례 |
| 국소거리 | cosine (L2 정규화 후) | 카테고리 4 "cosine distance" |
| DTW | 순수 numpy 정확 DTW | fastdtw 미설치 → 폴백(§9). 설치 시 `--backend fastdtw` |

→ 세부 멜값·임계값은 **11~12주차 튜닝 knob**. 이 스파이크는 방향성 판정용 기본값.

---

## 학부생 로컬 실행 (2층 — 실 클립, 실 판정)

```bash
# venv (TF/numpy/librosa 확인됨). fastdtw 는 선택(가속) — 미설치여도 exact 폴백 동작.
source ~/ddingdong_ml_env/bin/activate
pip install fastdtw            # (선택) 긴 클립 가속. 안 해도 됨.

cd <repo>
# 실 doorbell 클립으로 분리 실험 (01_clips 또는 01_clips/doorbell 경로)
python3 -m ml.experiments.dtw_doorbell.experiment \
    --clips-dir "$HOME/ML 학습 데이터/ddingdong_dataset/01_clips"

# 빠른 확인(그룹 제한):  --max-groups 30
```

## 결과 해석 가이드
- **분리 마진** = `(inter평균 − intra평균) / pooled_std` (Cohen's d류). 클수록 깨끗한 분리.
  - `margin ≥ 2.0` (`GO_MARGIN_MIN`) → **알고리즘 GO 신호**(강한 분리).
  - pretest 분리 마진 **8.42** 와 대조 → 실 클립 마진이 이 근방이면 pretest 정합.
  - `margin < 2.0` → NO-GO/재검토(특징·거리 재설계 or 직접녹음 의존).
- **EER**(Equal Error Rate) 낮을수록 좋음. 등록(intra) 거부율 = 미등록(inter) 수락율 되는 지점.
- **임계 스윕 최고정확도** = 단일 거리 임계로 등록/미등록 가를 때 상한 정확도.
- ★ 위 캐비앗대로 여기 숫자는 **상한**. 직접녹음 재-누름으로 하한도 확인해야 시연 확신.

## 자기검증 (MCP 세션 = 1층, 합성)
```bash
python3 -m unittest ml.experiments.dtw_doorbell.tests.test_dtw_contract   # 12 tests
python3 -m ml.experiments.dtw_doorbell.synth_smoke                        # 합성 E2E
```
→ 합성 스모크 마진/EER 숫자는 **무의미**(코드 경로·intra<inter 방향만 확인). 실 숫자는 2층.
