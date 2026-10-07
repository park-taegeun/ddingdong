# decisions-rag — `docs/decisions.md` 검색기 (개발 도구)

위임 전에 과거 결정(폐기안 포함)을 찾아보는 RAG 검색기다. 제품(서버 · 대시보드 · 펌웨어 · ml)과 무관한 개발 도구다.

## 🔴 규칙

- **평가 질문 · 정답을 `docs/decisions.md`에 쓰지 않는다.** 인덱스가 오염된다 — 질문이 자기 답을 검색하게 된다.
- **검색 결과는 힌트다.** 위임 Step 0 인용은 원문을 `grep`으로 다시 확인한 뒤에만 쓴다.
- 아래 시운전 질문 3개는 시운전용이다. 평가셋에 넣지 않는다.
  「마이크 SCK는 몇 번 GPIO에 물렸나」 · 「카카오 비즈 앱 심사를 피한 이유」 · 「clangd 잔존 진단은 몇 건이었나」

## 설치

python 3.11 또는 3.12(3.13 이상은 의존 패키지 바퀴가 없을 수 있다).

```sh
cd "<repo>/tools/decisions-rag"
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

OpenAI 키는 `tools/decisions-rag/.env`에 `OPENAI_API_KEY=...` 한 줄로 넣는다(`.gitignore`가 막는다). 키가 없어도 `--dry-run` · `--mock-embed` · 테스트는 돈다.

## 명령

모든 실행은 `-B` + `PYTHONDONTWRITEBYTECODE=1`. 인덱스 · 임베딩 캐시 경로는 **repo 밖만** 허용한다(심볼릭 링크를 풀고 비교).

```sh
export PYTHONDONTWRITEBYTECODE=1
# 청크 통계 · 비밀값 점검 · 토큰 수 · 예상 비용만(네트워크 0 · 저장 0)
.venv/bin/python -B index.py --commit <커밋> --config configs/baseline.json \
  --persist-dir ~/ddingdong-rag/index-<커밋 7자리>-baseline --embed-cache ~/ddingdong-rag/embed-cache --dry-run

# 인덱스 생성(OpenAI 임베딩 — 청크 해시 캐시, 같은 청크는 다시 임베딩하지 않는다)
.venv/bin/python -B index.py --commit <커밋> --config configs/baseline.json \
  --persist-dir ~/ddingdong-rag/index-<커밋 7자리>-baseline --embed-cache ~/ddingdong-rag/embed-cache

# 질의(상위 k 청크) · --answer = 답변 모델 호출
.venv/bin/python -B query.py --persist-dir ~/ddingdong-rag/index-<커밋 7자리>-baseline \
  --config configs/baseline.json -k 5 "<질문>" [--answer]

# 테스트(stdlib unittest, 네트워크 0)
.venv/bin/python -B -m unittest discover -s tests
```

`--mock-embed`는 가짜 임베딩(상수 벡터)으로 배관만 확인한다. 검색 순위는 의미가 없고 `--answer`는 거부된다.

## 설계 결정

| 항목 | 결정 | 이유 |
|---|---|---|
| 원문 | `git show <커밋>:docs/decisions.md` | 작업 트리가 아니라 커밋에 고정. 같은 커밋 + 같은 설정 = 같은 청크(해시로 검사). 줄 번호는 늘 `<커밋>@L시작-L끝`으로만 쓴다 |
| 청킹 | 직접 짠 구조 인식 청커(`chunker.py`) | 제목(`##` 카테고리 · `###` 절 · `####` 이하 · 줄 머리 `**(a)` 소절) → 목록 최상위 항목(중첩 줄 포함) · 문단 · 표 · 인용 · 코드 블록 단위 → 목표 글자 수로 묶기 |
| 큰 단위 | 중첩 항목 경계 → 줄 → 문장 경계 | 문장 경계에서 자를 때만 약 `overlap_chars` 겹침. 표는 행 단위로 자르고 머리 두 줄을 반복. 크기는 본문 기준(제목 경로 줄 제외) |
| 오인 방지 | 코드 블록 안 `#` · `|`는 구조로 보지 않는다 · `### 5/12 …` 같은 날짜 제목은 절 번호가 아니다 | 실문서에 코드 블록 안 `## ` 6줄 · 날짜 제목 3개가 있다 |
| 커버리지 | 청크는 원문 줄 조각(span)으로만 만든다 | 「비어 있지 않은 모든 줄이 어떤 청크에 들어간다」를 테스트로 증명 |
| 임베딩 본문 | 제목 경로 한 줄 + 본문 | 메타데이터 키 · 값은 임베딩 · 답변 본문에서 뺀다(`excluded_*_metadata_keys`) |
| 근거 표기 | 코드가 메타데이터에서 붙인다 | 모델 출력은 근거 청크 **번호**만 신뢰하고 범위 밖 번호는 버린다 |
| 답변 모델 | `gpt-4.1-mini-2025-04-14`(스냅샷 고정 — 별칭은 가리키는 대상이 바뀔 수 있다) · temperature 0 · JSON | 현행 소형 추론 모델(`gpt-5.4-mini` 등)은 `llama-index-llms-openai`가 temperature를 조용히 1.0으로 바꾼다 → 설정하면 거부 |
| E1 스위치 | `mark_superseded` | 참이면 `~~X~~` → `[폐기] X [/폐기]`로 바꾼 본문을 임베딩 · 답변에 쓴다(표시 원문 보존). 기준선 = 거짓 |
| 설정 | `configs/*.json` — 모든 손잡이 명시, 빠지면 실패(기본값 금지) | manifest에 설정 해시 · 커밋 · 청커 버전 · 패키지 버전을 남기고, 질의 때 해시가 다르면 거부 |
| 비밀값 | 인덱싱 전 OpenAI 키 · `Bearer` 긴 토큰 · quick tunnel 주소를 센다 | 키 · 토큰이 나오면 인덱싱 중단, 터널 주소는 인덱스 본문에서만 마스킹. md5 같은 16진 해시는 세지 않는다 |
| 개인정보 | 개인통관고유번호 · 메일 주소 · AWS 계정 ID(`Account ID` 뒤) · 휴대폰(하이픈 형식)을 센다 | 인덱싱은 막지 않고 인덱스 본문에서만 마스킹(원문 수정 0). 메일은 `@` 뒤 첫 글자가 영문일 때만 — `pkg@1.2.3.tgz` 같은 버전 문자열 제외. 출력은 종류별 개수 · 절 위치뿐 |
| 절 표기 | `6.2` · `33.30(f)` · `카테고리 3` · 번호 없는 제목은 `카테고리 23 › 결정`(바깥 제목 이름을 붙임) | 같은 표기가 두 곳을 가리키지 않게(실문서 0건을 테스트로 고정) |
| 중첩 소절 | 소절이 열린 채 `(a)`가 다시 시작하면 그 안의 중첩 → `6.3(s)(a)` | 해제 = 다음 제목 줄 또는 바깥보다 뒤 글자인 소문자 소절. 역순(`(g)` 뒤 `(f)`) · 대문자 체계(`(F)`)는 중첩이 아니다 |
| 비용 | 임베딩 전 토큰 수 출력 · `max_embed_tokens` 넘으면 중단 | 단가 = `configs/prices.json`(달러 / 100만 토큰). 설정의 모델이 없으면 실패(기본값 금지) · 임베딩 단가가 `embed_price_usd_per_1m_tokens`와 다르면 실패 |
| 저장 | Chroma 로컬 영속(`--persist-dir`, 비어 있지 않으면 거부) | 익명 통계는 `Settings(anonymized_telemetry=False)`로 끈다. 컬렉션은 `embedding_function=None`(Chroma 기본 ONNX 모델을 받지 않는다) |

`-k`는 출력 개수다. 설정의 `top_k`와 다르면 경고만 한다(평가 조건 = `top_k`).

### 패키지가 받는 데이터

- tiktoken 인코딩(`cl100k_base`): `llama-index-core`에 동봉된 `_static/tiktoken_cache`를 `TIKTOKEN_CACHE_DIR`로 가리켜 내려받지 않는다.
- NLTK(stopwords · punkt_tab): `llama-index-core`의 `_static/nltk_cache`에 동봉돼 있어 내려받지 않는다.

## 설정 손잡이 (`configs/baseline.json`)

`name` · `chunk_target_chars`(묶기 목표) · `chunk_max_chars`(이보다 큰 단위를 쪼갬) · `overlap_chars`(문장 경계 조각 겹침) · `mark_superseded`(E1) · `embed_model` · `embed_price_usd_per_1m_tokens` · `max_embed_tokens` · `top_k` · `answer_model`.

## 평가 (`evaluate.py`)

규칙은 `eval/PREREG.md`(결과 전 등록 — 이 파일 · `eval/eval_set_v1.jsonl` · `configs/eval_v1.json`은 바꾸지 않는다). 출력은 `--out-dir`(repo 밖 · 빈 폴더)에만 쓴다.

```sh
# 검색 평가 — bm25 · random · gold_removed:bm25는 네트워크 0. dense는 --persist-dir 인덱스(실임베딩)
.venv/bin/python -B evaluate.py retrieval --commit e471052 --config configs/baseline.json \
  --eval-config configs/eval_v1.json --conditions bm25,random,gold_removed:bm25 --out-dir ~/ddingdong-rag/eval-<이름>

# 답변 평가(OpenAI 답변 모델) → sheet.csv(블라인드) + key.jsonl(열쇠 — 채점 전에 열지 않는다)
# 프롬프트를 모두 만든 뒤 예상 비용 > --max-usd면 호출 없이 중단
.venv/bin/python -B evaluate.py answer (위와 같은 인자) --max-usd 1.00

# 채점 합산 — sheet.csv의 판정 칸에 정답 · 부분 · 오답 중 하나를 채운 뒤
.venv/bin/python -B evaluate.py score --sheet <sheet.csv> --key <key.jsonl> --out-dir ~/ddingdong-rag/score-<이름>
```

| 항목 | 결정 |
|---|---|
| 적중 | 정답 조각 하나의 **전체 문자열**을 담은 청크(표시 원문 · 마스킹 반영). 청크 경계에 걸쳐 잘린 조각은 적중 아님 |
| BM25 | 표준 라이브러리 구현. 문서 = 임베딩 본문(제목 경로 줄 + 본문). idf = log(1 + (N − df + 0.5) / (df + 0.5)), 점수 0 문서는 결과에서 뺀다 |
| gold_removed | bm25는 정답 청크를 뺀 문서로 인덱스를 다시 만든다(df · 평균 길이 포함). dense는 넉넉히 받아 뺀 청크를 거른다(벡터 유사도는 다른 문서와 무관). 뺀 청크가 상위 `mrr_cutoff` 안에 나오면 실행 실패 |
| random | 문항마다 `random.Random("<random_seed>:<qid>")` — 실행 순서와 무관하게 고정 |
| 근거 유효 | 답한(거절 안 한) · 답 있는 문항만 센다(not_in_doc은 정답 조각이 없다) |
| 토큰 · 달러 | 답변 모델 인코딩(tiktoken, 동봉 캐시)으로 프롬프트 · 출력을 센다 = **추정**(채팅 형식 오버헤드 · 캐시 할인 미반영). 달러 = 토큰 × `configs/prices.json`. 호출 전 예상은 출력 300토큰/회를 가정 |

## 다음 PR

- ③ 기준선 측정 · 오답 분류 · 실험 E1(취소선 폐기 표시) · E2(하이브리드 검색) · 로컬 모델(Ollama) 비교
- ④(선택) MCP 서버
