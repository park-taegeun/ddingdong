# 평가 결과 v2 — decisions-rag 검색 개선

규칙 = `eval/PREREG_v2.md`(사전 등록 f919fe5). 표본이 작다(v1 검색 25 · H1 검색 12 · 답변 60행) · 실행 1회 — 수치는 방향 판단용이며 일반화 주장을 하지 않는다.
질문 문장 · 생성문(가상 문단 · 재작성 질의)은 여기 다시 쓰지 않는다(문항 번호로만 — 본문은 `eval/eval_set_v1.jsonl` · `eval/eval_holdout_h1.jsonl`).

## ① 요약

- 1단계(v1 검색 25문항): E4 rewrite · E5 큰 임베딩이 통과(Hit@3 6 → 8 둘 다), E3 hyde는 미통과(6 → 5). 동점 규칙(MRR@10 0.226 > 0.209)으로 E4가 2단계 후보.
- 2단계 검색(H1 12문항): E4 Hit@3 5 · 기준선 1 → 통과.
- 2단계 답변: 후보 v1 정답 10(필요 ≥ 9) 통과 · 후보 H1 정답 8 < 기준선 H1 9 → 미통과. **E4 = 미채택**(사전 등록 규칙 기준).
- 후보 v1 부분 + 오답 20건 중 16건이 여전히 검색 실패(R). 기준선 v1의 R 19문항 중 4문항만 정답 청크가 상위 5에 들어왔고 그중 2문항이 정답이 됐다.
- 채점 일관성: 기준선 · 2라운드 · v2 세 시트에서 같은 답 쌍 50 · 빈 답 쌍 139 중 판정 불일치 0.

## ② 설정 · 버전

| 항목 | 값 |
|---|---|
| 원문 | `git show e471052:docs/decisions.md` |
| 사전 등록 | f919fe5(2026-10-07 14:25:35 +0900 push — 실험 코드 커밋 84535c9보다 먼저) |
| 평가셋 | v1 `eval/eval_set_v1.jsonl` sha256 = `761f112d990546cbff450006ddeeed1d79aceaf64fe665dec95cb08b0dff97f7`(30문항) · H1 `eval/eval_holdout_h1.jsonl` sha256 = `7dd7e268d3b8abc6877168a4bac51e5edf1681a6c8858e7cf0e18d7d20bbd679`(15문항) |
| 답변 · 생성 모델 | `gpt-4.1-mini-2025-04-14`(스냅샷) · 온도 0 · 상위 5 청크. 생성(hyde · rewrite)은 seed = 20261007 |
| 임베딩 | 기준선 · E3 · E4 = `text-embedding-3-small`(인덱스 `index-e471052-baseline`, 설정 해시 `38144084c4c0…`) / E5 = `text-embedding-3-large`(인덱스 `index-e471052-e5`, 설정 해시 `02c3390ca2ee…`). 둘 다 청크 1,331 · 청커 버전 1 |
| 임베딩 평균 | 원 질문 · 생성문 임베딩의 산술 평균 — llama-index-core 0.14.25 `custom_embedding_strs` → `mean_agg`(`np.array(...).mean(axis=0)`, 재정규화 없음) |
| 제목 목록(E4) | 567줄 · 33,169자 · sha256 `bd3fd5b19d58c8de81934f621a468a0ba6dfd31eebf2cee766dbfc74cf97e362` · 각 80자에서 자름 |
| 평가기 | 검색 · 생성 · 답변 실행 = 84535c9 / 합산 = 388825c(실행 구분 수정) / 2단계 답변 판정 = 25b5fb9 |
| 패키지 | llama-index-core 0.14.25 · llama-index-llms-openai 0.8.2 · llama-index-embeddings-openai 0.7.0 · chromadb 1.5.9 · openai 2.54.0 · tiktoken 0.14.0 |

## ③ 검색

Hit@3 = 「n 중 m」, 괄호 = MRR@10. not_in_doc은 뺀다.

### v1 (n = 25)

| 조건 | 전체 | fact | identifier | reversal | false_premise |
|---|---|---|---|---|---|
| dense(기준선 · v1 재사용) | 25 중 6 (0.131) | 10 중 3 (0.200) | 5 중 1 (0.067) | 5 중 2 (0.167) | 5 중 0 (0.020) |
| hyde(E3) | 25 중 5 (0.170) | 10 중 3 (0.250) | 5 중 1 (0.067) | 5 중 1 (0.250) | 5 중 0 (0.033) |
| rewrite(E4) | 25 중 8 (0.226) | 10 중 2 (0.160) | 5 중 2 (0.292) | 5 중 2 (0.350) | 5 중 2 (0.167) |
| e5_large dense(E5) | 25 중 8 (0.209) | 10 중 4 (0.233) | 5 중 1 (0.092) | 5 중 2 (0.400) | 5 중 1 (0.089) |
| gold_removed:hyde | 25 중 0 (0.000) | 10 중 0 | 5 중 0 | 5 중 0 | 5 중 0 |
| gold_removed:rewrite | 25 중 0 (0.000) | 10 중 0 | 5 중 0 | 5 중 0 | 5 중 0 |
| gold_removed:dense(E5) | 25 중 0 (0.000) | 10 중 0 | 5 중 0 | 5 중 0 | 5 중 0 |

### H1 (n = 12)

| 조건 | 전체 | fact | identifier | reversal | false_premise |
|---|---|---|---|---|---|
| random | 12 중 0 (0.000) | 3 중 0 (0.000) | 3 중 0 (0.000) | 3 중 0 (0.000) | 3 중 0 (0.000) |
| bm25 | 12 중 2 (0.190) | 3 중 0 (0.083) | 3 중 0 (0.083) | 3 중 0 (0.150) | 3 중 2 (0.444) |
| dense(기준선) | 12 중 1 (0.158) | 3 중 0 (0.048) | 3 중 0 (0.083) | 3 중 0 (0.083) | 3 중 1 (0.417) |
| rewrite(E4) | 12 중 5 (0.302) | 3 중 1 (0.167) | 3 중 0 (0.042) | 3 중 2 (0.500) | 3 중 2 (0.500) |
| gold_removed:dense | 12 중 0 (0.000) | 3 중 0 | 3 중 0 | 3 중 0 | 3 중 0 |
| gold_removed:rewrite | 12 중 0 (0.000) | 3 중 0 | 3 중 0 | 3 중 0 | 3 중 0 |

gold_removed가 전부 0 — 정답 청크를 빼면 적중이 사라진다(평가기 자기 검증).
v1에서 E4 · E5의 적중 문항은 4개만 겹친다(E4 8 · E5 8 · 합집합 12 — 문항마다 나은 쪽을 고른 상한이지 결합 방법의 값이 아니다).

## ④ 1단계 판정 — v1 검색

`evaluate.py adopt-v2 --stage 1` 결과 = 검색 기록(retrieval.jsonl)에서 평가기 코드 없이 다시 센 값과 일치.

| 실험 | 조항(PREREG_v2 원문) | n | 기준선 | 실험 | 차이 | 필요 | 판정 |
|---|---|---|---|---|---|---|---|
| E3 | 전체 Hit@3 +2문항 이상 | 25 | 6 | 5 | −1 | ≥ +2 | 미통과 |
| E3 | 유형별 Hit@3 2문항 이상 감소 없음 | — | — | — | 최저 −1(reversal) | ≥ −1 | 통과 |
| E4 | 전체 Hit@3 +2문항 이상 | 25 | 6 | 8 | +2 | ≥ +2 | 통과 |
| E4 | 유형별 Hit@3 2문항 이상 감소 없음 | — | — | — | 최저 −1(fact) | ≥ −1 | 통과 |
| E5 | 전체 Hit@3 +2문항 이상 | 25 | 6 | 8 | +2 | ≥ +2 | 통과 |
| E5 | 유형별 Hit@3 2문항 이상 감소 없음 | — | — | — | 최저 +0 | ≥ −1 | 통과 |

통과 2개(E4 · E5) → 「전체 Hit@3가 높은 쪽 → 같으면 MRR@10이 높은 쪽 → 같으면 E5 · E3 · E4 순」: Hit@3 8 = 8 → MRR@10 E4 0.2257 > E5 0.2094 → **E4가 2단계 후보**.

## ⑤ 2단계 판정 + 최종 채택

`adopt-v2 --stage 2` · `adopt-v2-answers` 결과 = 시트 · 열쇠에서 합산 코드 없이 다시 센 값과 일치. 「정답 수」는 개수 비교(「부분」은 정답 아님).

| 단계 | 조항(PREREG_v2 원문) | 후보 E4 | 기준 | 판정 |
|---|---|---|---|---|
| 1단계 | 전체 Hit@3 ≥ 기준선 + 2 · 어떤 유형도 2문항 이상 감소 없음 | 8 · 최저 −1 | 8 · ≥ −1 | 통과 |
| 2단계 검색 | 후보의 Hit@3 ≥ 기준선의 Hit@3(H1 답 있는 12문항) | 5 | 1 | 통과 |
| 2단계 답변 | 후보 v1 정답 수 ≥ 9 | 10 | 9 | 통과 |
| 2단계 답변 | 후보 H1 정답 수 ≥ 기준선 H1 정답 수 | 8 | 9 | **미통과** |
| **종합** | 채택 = 1 · 2단계 모두 통과 | | | **미채택** |

참고(판정에 안 씀) — 정답이 바뀐 문항: v1 정답 → 비정답 Q09 · Q16 / 비정답 → 정답 Q11 · Q24 · Q29. H1 정답 → 비정답 H08 · H09 / 비정답 → 정답 H03.

「채택」은 사전 등록 규칙 통과만을 뜻한다. 기본 설정(`configs/baseline.json`) 반영은 별도 판단이다.

## ⑥ 답변

칸 = 정답 · 부분 · 오답. 모두 gpt-4.1-mini · 상위 5. 기준선 v1은 v1 결과의 기준선 실행 재사용(⑨ (d)).

| 실행 | fact | identifier | reversal | not_in_doc | false_premise | 전체 |
|---|---|---|---|---|---|---|
| 기준선 v1(dense, 재사용) | 2 · 1 · 7 | 1 · 1 · 3 | 2 · 1 · 2 | 4 · 0 · 1 | 0 · 1 · 4 | 9 · 4 · 17 |
| 후보 v1(rewrite) | 1 · 2 · 7 | 2 · 1 · 2 | 1 · 0 · 4 | 5 · 0 · 0 | 1 · 0 · 4 | 10 · 3 · 17 |
| 기준선 H1(dense) | 0 · 1 · 2 | 1 · 1 · 1 | 3 · 0 · 0 | 3 · 0 · 0 | 2 · 0 · 1 | 9 · 2 · 4 |
| 후보 H1(rewrite) | 1 · 0 · 2 | 1 · 0 · 2 | 1 · 1 · 1 | 3 · 0 · 0 | 2 · 0 · 1 | 8 · 1 · 6 |

v1 유형별 n = 10 · 5 · 5 · 5 · 5 / H1 = 3 · 3 · 3 · 3 · 3.

| 실행 | 환각 ↔ 과잉 거절 | 근거 유효 | 번복 앵커(자동) | reversal 오답(채점) | 폐기안 채택(판단) | 호출 실패 | 형식 오류 | 검색 초(평균 · 중앙값) | 답변 초(평균 · 중앙값) | 토큰(입력 · 출력) | 달러(추정) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 기준선 v1 | 1 ↔ 11 | 6 / 14 | 0 | 2 | 0 | 0 | 0 | 0.172 · 0.155 | 1.068 · 0.973 | 76,127 · 1,144 | 0.0323 |
| 후보 v1 | 0 ↔ 10 | 6 / 15 | 0 | 4 | 0 | 0 | 0 | 0.314 · 0.305 | 1.121 · 1.041 | 73,336 · 1,634 | 0.0319 |
| 기준선 H1 | 0 ↔ 3 | 4 / 9 | 0 | 0 | 0 | 0 | 0 | 0.173 · 0.151 | 1.050 · 0.932 | 38,860 · 813 | 0.0168 |
| 후보 H1 | 0 ↔ 5 | 5 / 7 | 0 | 1 | 0 | 0 | 0 | 0.497 · 0.306 | 1.008 · 0.878 | 34,530 · 675 | 0.0149 |

- 후보의 검색 초 = 답변 단계 검색(원 질문 + 캐시된 재작성 질의 임베딩 2회 + 벡터 검색). 재작성 생성 시간은 들어 있지 않다(검색 평가 때 한 번 생성 · 캐시).
- 번복 세 칸 정의는 v1 결과의 정정과 같다. 폐기안 채택(판단) — reversal 부분 · 오답 행: 후보 v1 4행(Q16 다른 상수를 답함 · Q18 거절 · Q19 정규화 여부를 미검증으로만 답함 · Q20 거절) · 후보 H1 2행(H08 거절 · H09 폐기안을 기각으로 바르게 서술하고 나머지 누락) — 모두 폐기안을 지금 사실로 답하지 않아 해당 0. 판단자 = 결과 v2를 쓴 Claude 세션(채점 뒤 · 블라인드 아님).
- false_premise는 번복 지표 대상이 아니다 — 후보 v1 Q26은 폐기된 사양을 그대로 답했다(⑦ G-폐기안).

### v2 비용 합계

| 항목 | 달러 | 근거 |
|---|---|---|
| E5 인덱스 임베딩(1,331청크 · 759,402토큰) | 0.0987 | 로컬 tiktoken 토큰 × 0.13 |
| 생성 — v1 hyde 30회 | 0.0059 | API usage(입력 3,912 · 출력 2,717) |
| 생성 — v1 rewrite 30회 | 0.0682 | API usage(입력 588,072 중 캐시 564,224 · 출력 1,394) |
| 생성 — H1 rewrite 15회 | 0.0314 | API usage(입력 293,971 중 캐시 291,840 · 출력 860) |
| 답변 — 후보 v1 30 · H1 30 | 0.0636 | 로컬 tiktoken 추정(0.0319 + 0.0168 + 0.0149) |
| **합계** | **0.2678** | 질의 임베딩 호출(검색마다 1~2회)은 빠짐(⑨ (c)) |

## ⑦ 오답 분석

부분 + 오답 행을 범주로 나눴다(v1과 같은 방법). 정답 청크 순위 = 답변에 쓴 상위 5(열쇠 `retrieved`) 안의 순위 — 60행 모두 검색 평가의 순위(5위 이내)와 같았다.
자동 결합(판정 × 순위 × 거절 × 호출 실패 × 폐기안 앵커) 먼저, 자동으로 갈리지 않는 행만 사람 판단(근거 1줄 · 「판단」 표시).

- R = 검색 실패(상위 5에 정답 청크 없음): R-거절 · R-오답 · R-전제수용
- G = 검색 성공인데 생성 실패: G-거절 · G-오답 · G-폐기안 · G-틀린 말 섞임
- H = not_in_doc에서 지어냄 · C = 호출 실패(빈 답 — 오답 채점)

| 범주 | 기준선 v1(재사용) | 후보 v1 | 기준선 H1 | 후보 H1 |
|---|---|---|---|---|
| R-거절 | 12 (판단 1) | 9 | 3 | 5 |
| R-오답 | 5 (판단 3) | 6 (판단 2) | 3 (판단 2) | 1 |
| R-전제수용 | 2 | 1 | 0 | 0 |
| G-거절 | 0 | 1 | 0 | 0 |
| G-오답 | 1 (판단 1) | 2 (판단 1) | 0 | 1 (판단 1) |
| G-폐기안 | 0 | 1 (판단 1) | 0 | 0 |
| G-틀린 말 섞임 | 0 | 0 | 0 | 0 |
| H | 1 | 0 | 0 | 0 |
| C | 0 | 0 | 0 | 0 |
| 합계(부분 + 오답) | 21 | 20 | 6 | 7 |

- **검색 개선이 답으로 이어졌나(v1)**: 기준선의 R 19문항 중 후보에서 정답 청크가 상위 5에 든 문항 = 4(Q11 3위 · Q29 3위 · Q18 2위 · Q26 2위). 그중 정답 = 2(Q11 · Q29). 나머지 2는 G-거절(Q18) · G-폐기안(Q26).
- 반대 방향: 기준선에서 정답 청크가 상위 5 안이던 Q09(2위)는 후보에서 10위로 밀려 정답 → R-거절.
- 후보 v1의 G 4건(G-거절 1 · G-오답 2 · G-폐기안 1)은 정답 청크가 상위 5에 있는데 답이 틀린 행 — 기준선 v1 G 1건보다 많다.
- H1에서 기준선 · 후보 모두 부분 + 오답 대부분이 R(6 중 6 · 7 중 6). 과잉 거절은 후보가 더 많다(3 → 5).

### 문항별 — 후보 v1

| 문항 | 유형 | 판정 | 정답 청크 순위 | 범주 | 근거(판단만) |
|---|---|---|---|---|---|
| Q01 | fact | 오답 | 없음 | R-거절 | |
| Q02 | fact | 오답 | 없음 | R-오답 | |
| Q03 | fact | 오답 | 없음 | R-오답 | |
| Q04 | fact | 오답 | 없음 | R-거절 | |
| Q05 | fact | 오답 | 없음 | R-거절 | |
| Q06 | fact | 부분 | 2 | G-오답 (판단) | 정답 청크 2위 · 핵심 값(총 개수)을 빠뜨림 — 틀린 말은 없어 「섞임」 아님(v1 hybrid Q06과 같은 꼴) |
| Q07 | fact | 오답 | 없음 | R-거절 | |
| Q09 | fact | 오답 | 없음 | R-거절 | |
| Q10 | fact | 부분 | 없음 | R-오답 (판단) | 결론은 맞으나 근거가 틀림 — 정답 청크가 없어 R 쪽 |
| Q12 | identifier | 부분 | 없음 | R-오답 (판단) | 일부 맞힘 + 틀린 말 섞임 — 정답 청크가 없어 R 쪽 |
| Q14 | identifier | 오답 | 없음 | R-오답 | |
| Q15 | identifier | 오답 | 없음 | R-거절 | |
| Q16 | reversal | 오답 | 4 | G-오답 | |
| Q18 | reversal | 오답 | 2 | G-거절 | |
| Q19 | reversal | 오답 | 없음 | R-오답 | |
| Q20 | reversal | 오답 | 없음 | R-거절 | |
| Q26 | false_premise | 오답 | 2 | G-폐기안 (판단) | 정답 청크 2위 · 계획 단계의 옛 사양(폐기안 앵커와 같은 문자열)을 지금 사양으로 답함 = 전제 수용이자 폐기안 채택 |
| Q27 | false_premise | 오답 | 없음 | R-거절 | |
| Q28 | false_premise | 오답 | 없음 | R-거절 | |
| Q30 | false_premise | 오답 | 없음 | R-전제수용 | |

### 문항별 — 기준선 H1

| 문항 | 유형 | 판정 | 정답 청크 순위 | 범주 | 근거(판단만) |
|---|---|---|---|---|---|
| H01 | fact | 부분 | 없음 | R-오답 (판단) | 단위는 맞음 + 원 데이터셋의 나눔을 우리 나눔처럼 섞음 — 정답 청크가 없어 R 쪽 |
| H02 | fact | 오답 | 없음 | R-거절 | |
| H03 | fact | 오답 | 없음 | R-오답 | |
| H04 | identifier | 부분 | 없음 | R-오답 (판단) | 뜻만 답하고 처리(기록 · 알림 차단) 누락 — 정답 청크가 없어 R 쪽 |
| H06 | identifier | 오답 | 없음 | R-거절 | |
| H15 | false_premise | 오답 | 없음 | R-거절 | |

### 문항별 — 후보 H1

| 문항 | 유형 | 판정 | 정답 청크 순위 | 범주 | 근거(판단만) |
|---|---|---|---|---|---|
| H01 | fact | 오답 | 없음 | R-오답 | |
| H02 | fact | 오답 | 없음 | R-거절 | |
| H04 | identifier | 오답 | 없음 | R-거절 | |
| H06 | identifier | 오답 | 없음 | R-거절 | |
| H08 | reversal | 오답 | 없음 | R-거절 | |
| H09 | reversal | 부분 | 1 | G-오답 (판단) | 정답 청크 1위 · 기각된 쪽만 답하고 실제 녹음 경로를 빠뜨림 — 폐기안 채택 아님(G에 누락 칸이 없어 G-오답) |
| H15 | false_premise | 오답 | 없음 | R-거절 | |

기준선 v1 문항별 표는 v1 결과 문서(`eval/results_v1.md`)와 기준선 오답 분석(`~/ddingdong-rag/runs/2026-10-07_baseline_score/error_analysis.md`)과 같다.

## ⑧ 실패 사례

순위 = 검색 평가의 상위 10 안 순위(「없음」 = 10위 밖).

1. **Q09 · fact · 후보 v1** — 기준선은 정답, 후보는 거절(오답). 범주 R-거절. 원인: 정답 청크가 dense 2위였는데 재작성 질의와 평균한 벡터에서 10위로 밀려 답변 상위 5에서 빠졌다. E4의 Hit@3 +2는 4문항을 얻고 2문항(Q09 · Q16 — Q16은 2위 → 4위)을 내준 결과다.
2. **Q26 · false_premise · 후보 v1** — 정답 청크가 2위로 들어왔는데도 계획 단계의 옛 사양을 지금 사양으로 답함(「AWS EC2 t3.small (서울, 2GB RAM)」). 범주 G-폐기안(판단). 같은 상위 5에 옛 사양을 적은 청크가 함께 있었다 — 정답 청크 진입만으로는 바로잡히지 않은 사례(v1 hybrid Q30과 같은 꼴).
3. **Q18 · reversal · 후보 v1** — 기준선 R(10위 밖)이 후보에서 2위로 올라왔지만 모델이 거절. 범주 G-거절. 검색은 고쳐졌는데 답변 단계에서 놓친 사례.
4. **H08 · reversal · 후보 H1** — 기준선은 정답 청크가 10위 밖인데도 정답, 후보는 거절(오답). 범주 R-거절. 두 실행 모두 정답 청크가 상위 5 밖 — 상위 5 구성이 바뀌면서 답에 쓸 정보가 빠졌다. 후보 H1 정답 8 < 기준선 9를 만든 두 문항(H08 · H09) 중 하나.

## ⑨ 사전 등록과 달라진 점

- (a) 채점 절차 — Claude 1차 판정(조건 이름 없는 블라인드 시트 60행) → 판단이 갈릴 수 있는 5행에 권고 판정을 붙여 사용자에게 제시 → 사용자가 권고 그대로 수용(2026-10-07 14:46). 기준 = PREREG 판정 기준 + v1과 같은 판정 규칙 4개(메모 칸 머리 「규칙1~4」).
- (b) 제목 목록에서 코드 블록 안 템플릿 예시 6줄을 뺐다(정규식만으로는 573줄 → 567줄). 사전 등록 문구 「제목 줄」의 해석이며, 결과를 보기 전에 코드(84535c9 — 청커와 같은 코드 블록 규칙)로 고정했다.
- (c) 질의 임베딩 호출 비용(검색마다 원 질문 · 생성문 1~2회)은 실행 단위 예상 비용 상한 계산에서 뺐다. 생성 · 답변 · 인덱스 임베딩은 넣었다.
- (d) 기준선 v1 답변은 다시 돌리지 않고 v1 결과(다른 채점 회차)를 재사용했다(사전 등록 문구대로). 일관성 점검: 기준선 · 2라운드 · v2 세 시트에서 같은 문항 · 같은 답 본문 · 같은 거절 · 같은 호출 실패 여부인 쌍 189(같은 답 50 · 빈 답 139) 중 판정 불일치 0.
- (e) E5도 1단계를 통과했으나 동점 규칙(MRR@10)으로 2단계에 가지 않았다 — E5의 H1 검색 · 답변 성능은 측정하지 않았다.
- (f) 합산 결함 수정(388825c) — 실행 이름이 설정 · 조건 · 모델이라 평가셋을 보지 않아, 합친 시트의 후보 v1 30행과 후보 H1 15행이 한 실행(45행)으로 합쳐졌다. 열쇠에 평가셋 이름을 기록하고, 그 칸이 없는 열쇠는 qid가 속한 평가셋 파일로 판별하도록 고쳤다. 평가셋이 하나뿐인 기준선 · 2라운드 열쇠의 재합산 summary.json · summary.md는 바이트 동일. 판정 · 채점은 바꾸지 않았다.
- (g) 2단계 답변 판정 명령(`adopt-v2-answers`, 25b5fb9)은 채점 뒤에 넣었다. 판정 함수(`adopt_v2_answers`)는 결과 전 84535c9에 있던 것 그대로 쓴다.
- (h) 생성문은 문항마다(not_in_doc 포함 v1 30 · H1 15) 만들었다 — 답변 단계 검색이 30 · 15문항 모두 필요하기 때문. E3 hyde는 1단계 미통과라 H1 생성 0.
- (i) 정정 — 사전 등록 커밋 f919fe5의 메시지에 적은 H1 sha256 약칭은 뒷부분이 v1 sha의 꼬리로 잘못 적혔다. 파일 자체 · `configs/eval_h1.json` 등록값 · ②의 값은 `7dd7e268d3b8…bd679`로 정확하다(커밋 메시지는 고치지 않았다 — amend 금지).

## ⑩ 한계

- 표본: v1 검색 n = 25 · H1 검색 n = 12 · 답변 v1 30 · H1 15. 실행 1회 — 온도 0 · seed 고정이어도 API 결과는 완전히 결정적이지 않다.
- 2단계 답변 조건의 차이는 1문항(8 vs 9)이다 — 이 표본에서 방향 이상의 판단 근거가 아니다.
- 채점자 = Claude 1차 + 사용자 확인. 독립 채점자가 아니다. 기준선 v1은 다른 회차에 채점했다(⑨ (d)).
- 확인 세트 15문항 중 10개는 v1과 같은 시기에 같은 작성자가 쓴 후보에서 남은 것이다(5개만 새로 씀) — v1과 완전히 독립된 표본이 아니다.
- E4는 문서 자체의 제목 목록을 매 질의 프롬프트에 넣는다 — 문서가 커지면 생성 비용이 늘어난다. 이번 rewrite 생성 45회 입력 882,043토큰(1회 약 1.96만) 중 856,064토큰(97.1%)이 캐시 적중이었고, 생성 비용은 0.0996달러였다. 캐시 할인이 없으면 입력만 약 0.35달러.
- 비용 중 답변 · 인덱스는 로컬 토큰 추정 × 단가표 — 청구액이 아니다. 생성 비용만 API usage 기준이다.
- 정답 청크 판정은 정답 조각 문자열 포함 여부다 — H08 기준선처럼 정답 청크가 상위 5 밖인데 정답인 경우가 있다.

## ⑪ 다음 후보 (탐색적 · 사전 등록 아님 · 결정 아님)

- 검색 쪽이 여전히 먼저 — 후보 v1 부분 + 오답 20 중 R 16 · 후보 H1 7 중 R 6 · 기준선 H1 6 중 R 6.
  - E4 + E5 조합: v1 적중 문항 겹침 4(합집합 12 — 상한일 뿐). 두 방법이 서로 다른 문항을 맞힌다.
  - 재정렬: E4는 정답 청크를 위로 올린 문항(Q11 · Q18 · Q26 · Q29)과 아래로 민 문항(Q09 2 → 10위 · Q16 2 → 4위)이 함께 있다.
- 정답 청크가 들어와도 답이 틀리는 쪽 — 후보 v1 G 4건(G-거절 1 · G-오답 2 · G-폐기안 1). 폐기된 사양과 정답이 같은 상위 5에 있을 때(Q26) 옛 값을 고르는 꼴이 v1 hybrid에 이어 또 나왔다 → 폐기 표시 + 정답 청크 진입을 함께 보는 후보.
- 정답 조각 보강 — H08 기준선처럼 정답 청크 밖의 청크로 맞힌 경우가 있어, 정답 조각을 하나만 두면 검색 지표가 답 품질을 덜 반영한다.

## ⑫ 재현

repo = `tools/decisions-rag`, 실행은 `PYTHONDONTWRITEBYTECODE=1` + `.venv/bin/python -B`. 산출은 repo 밖 `~/ddingdong-rag/` 아래.

```sh
R=~/ddingdong-rag/runs; M=gpt-4.1-mini-2025-04-14
# ── 호출 있음(OpenAI) ──
# E5 인덱스
.venv/bin/python -B index.py --commit e471052 --config configs/e5_large.json \
  --persist-dir ~/ddingdong-rag/index-e471052-e5 --embed-cache ~/ddingdong-rag/embed-cache
# v1 검색 — E3 · E4(생성문 → $R/2026-10-07_v2_e34_retrieval/generated.jsonl) · E5
.venv/bin/python -B evaluate.py retrieval --commit e471052 --config configs/baseline.json --eval-config configs/eval_v1.json \
  --conditions hyde,rewrite,gold_removed:hyde,gold_removed:rewrite --persist-dir ~/ddingdong-rag/index-e471052-baseline \
  --out-dir $R/2026-10-07_v2_e34_retrieval --max-usd 1.00
.venv/bin/python -B evaluate.py retrieval --commit e471052 --config configs/e5_large.json --eval-config configs/eval_v1.json \
  --conditions dense,gold_removed:dense --persist-dir ~/ddingdong-rag/index-e471052-e5 --out-dir $R/2026-10-07_v2_e5_retrieval
# H1 검색
.venv/bin/python -B evaluate.py retrieval --commit e471052 --config configs/baseline.json --eval-config configs/eval_h1.json \
  --conditions bm25,random,dense,gold_removed:dense,rewrite,gold_removed:rewrite \
  --persist-dir ~/ddingdong-rag/index-e471052-baseline --out-dir $R/2026-10-07_v2_h1_retrieval --max-usd 1.00
# 답변(생성문은 캐시만 읽는다)
.venv/bin/python -B evaluate.py answer --commit e471052 --config configs/baseline.json --eval-config configs/eval_v1.json \
  --conditions rewrite --persist-dir ~/ddingdong-rag/index-e471052-baseline \
  --gen-cache $R/2026-10-07_v2_e34_retrieval/generated.jsonl --out-dir $R/2026-10-07_v2_answer_v1 --max-usd 1.00
.venv/bin/python -B evaluate.py answer --commit e471052 --config configs/baseline.json --eval-config configs/eval_h1.json \
  --conditions rewrite,dense --persist-dir ~/ddingdong-rag/index-e471052-baseline \
  --gen-cache $R/2026-10-07_v2_h1_retrieval/generated.jsonl --out-dir $R/2026-10-07_v2_answer_h1 --max-usd 1.00
# ── 호출 0 ──
.venv/bin/python -B evaluate.py merge --keys $R/2026-10-07_v2_answer_v1/key.jsonl,$R/2026-10-07_v2_answer_h1/key.jsonl \
  --config configs/baseline.json --eval-config configs/eval_v1.json --out-dir $R/2026-10-07_v2_sheet
.venv/bin/python -B evaluate.py adopt-v2 --stage 1 --base-retrieval $R/2026-10-07_baseline_retrieval/summary.json --base-cond dense \
  --cands E3,E4,E5 --cand-retrievals $R/2026-10-07_v2_e34_retrieval/summary.json,$R/2026-10-07_v2_e34_retrieval/summary.json,$R/2026-10-07_v2_e5_retrieval/summary.json \
  --cand-conds hyde,rewrite,dense --out-dir $R/2026-10-07_v2_stage1_adopt
.venv/bin/python -B evaluate.py adopt-v2 --stage 2 --base-retrieval $R/2026-10-07_v2_h1_retrieval/summary.json --base-cond dense \
  --cands E4 --cand-retrievals $R/2026-10-07_v2_h1_retrieval/summary.json --cand-conds rewrite --out-dir $R/2026-10-07_v2_stage2_retrieval_adopt
.venv/bin/python -B evaluate.py score --sheet $R/2026-10-07_v2_sheet/sheet_graded_v1.csv --key $R/2026-10-07_v2_sheet/key.jsonl \
  --out-dir $R/2026-10-07_v2_score
.venv/bin/python -B evaluate.py adopt-v2-answers --score $R/2026-10-07_v2_score/summary.json \
  --cand-v1-run "baseline · rewrite · $M · eval_v1" --cand-h1-run "baseline · rewrite · $M · eval_h1" \
  --base-h1-run "baseline · dense · $M · eval_h1" --out-dir $R/2026-10-07_v2_stage2_answer_adopt
.venv/bin/python -B evaluate.py consistency \
  --sheets $R/2026-10-07_baseline_answer/sheet_graded_v1.csv,$R/2026-10-07_round2_answer/sheet_graded_v1.csv,$R/2026-10-07_v2_sheet/sheet_graded_v1.csv \
  --keys $R/2026-10-07_baseline_answer/key.jsonl,$R/2026-10-07_round2_answer/key.jsonl,$R/2026-10-07_v2_sheet/key.jsonl \
  --out-dir $R/2026-10-07_v2_consistency
```

## 부록 — 문항별

순위 = 검색 평가의 정답 청크 순위(상위 10 안, 「없음」 = 10위 밖). 판정 = 각 실행.

### v1

| 문항 | 유형 | 순위 dense | 순위 hyde | 순위 rewrite | 순위 e5 | 기준선 | 후보(rewrite) |
|---|---|---|---|---|---|---|---|
| Q01 | fact | 없음 | 없음 | 없음 | 없음 | 오답 | 오답 |
| Q02 | fact | 없음 | 없음 | 없음 | 6 | 오답 | 오답 |
| Q03 | fact | 없음 | 없음 | 없음 | 없음 | 오답 | 오답 |
| Q04 | fact | 없음 | 없음 | 없음 | 없음 | 오답 | 오답 |
| Q05 | fact | 없음 | 없음 | 없음 | 없음 | 오답 | 오답 |
| Q06 | fact | 2 | 2 | 2 | 3 | 오답 | 부분 |
| Q07 | fact | 없음 | 없음 | 없음 | 없음 | 부분 | 오답 |
| Q08 | fact | 1 | 1 | 1 | 3 | 정답 | 정답 |
| Q09 | fact | 2 | 1 | 10 | 2 | 정답 | 오답 |
| Q10 | fact | 없음 | 없음 | 없음 | 1 | 오답 | 부분 |
| Q11 | identifier | 없음 | 없음 | 3 | 없음 | 오답 | 정답 |
| Q12 | identifier | 없음 | 없음 | 8 | 8 | 부분 | 부분 |
| Q13 | identifier | 3 | 3 | 1 | 3 | 정답 | 정답 |
| Q14 | identifier | 없음 | 없음 | 없음 | 없음 | 오답 | 오답 |
| Q15 | identifier | 없음 | 없음 | 없음 | 없음 | 오답 | 오답 |
| Q16 | reversal | 2 | 1 | 4 | 1 | 정답 | 오답 |
| Q17 | reversal | 3 | 4 | 1 | 1 | 정답 | 정답 |
| Q18 | reversal | 없음 | 없음 | 2 | 없음 | 부분 | 오답 |
| Q19 | reversal | 없음 | 없음 | 없음 | 없음 | 오답 | 오답 |
| Q20 | reversal | 없음 | 없음 | 없음 | 없음 | 오답 | 오답 |
| Q21 | not_in_doc | — | — | — | — | 정답 | 정답 |
| Q22 | not_in_doc | — | — | — | — | 정답 | 정답 |
| Q23 | not_in_doc | — | — | — | — | 정답 | 정답 |
| Q24 | not_in_doc | — | — | — | — | 오답 | 정답 |
| Q25 | not_in_doc | — | — | — | — | 정답 | 정답 |
| Q26 | false_premise | 없음 | 6 | 2 | 9 | 오답 | 오답 |
| Q27 | false_premise | 없음 | 없음 | 없음 | 3 | 오답 | 오답 |
| Q28 | false_premise | 없음 | 없음 | 없음 | 없음 | 오답 | 오답 |
| Q29 | false_premise | 없음 | 없음 | 3 | 없음 | 부분 | 정답 |
| Q30 | false_premise | 10 | 없음 | 없음 | 없음 | 오답 | 오답 |

### H1

| 문항 | 유형 | 순위 bm25 | 순위 dense | 순위 rewrite | 기준선(dense) | 후보(rewrite) |
|---|---|---|---|---|---|---|
| H01 | fact | 4 | 7 | 없음 | 부분 | 오답 |
| H02 | fact | 없음 | 없음 | 없음 | 오답 | 오답 |
| H03 | fact | 없음 | 없음 | 2 | 오답 | 정답 |
| H04 | identifier | 없음 | 없음 | 없음 | 부분 | 오답 |
| H05 | identifier | 4 | 4 | 8 | 정답 | 정답 |
| H06 | identifier | 없음 | 없음 | 없음 | 오답 | 오답 |
| H07 | reversal | 4 | 없음 | 2 | 정답 | 정답 |
| H08 | reversal | 없음 | 없음 | 없음 | 정답 | 오답 |
| H09 | reversal | 5 | 4 | 1 | 정답 | 부분 |
| H10 | not_in_doc | — | — | — | 정답 | 정답 |
| H11 | not_in_doc | — | — | — | 정답 | 정답 |
| H12 | not_in_doc | — | — | — | 정답 | 정답 |
| H13 | false_premise | 1 | 1 | 1 | 정답 | 정답 |
| H14 | false_premise | 3 | 4 | 2 | 정답 | 정답 |
| H15 | false_premise | 없음 | 없음 | 없음 | 오답 | 오답 |
