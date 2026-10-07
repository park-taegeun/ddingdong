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

# v2 질의 확장 — hyde · rewrite는 검색 평가가 문항마다 한 번 생성해 <out-dir>/generated.jsonl에 남긴다(--max-usd 필요),
# 답변 평가는 --gen-cache로 그 파일만 읽는다(캐시에 없는 문항 = 실패, 다시 생성 0)
.venv/bin/python -B evaluate.py retrieval (위와 같은 인자 · --persist-dir) --conditions rewrite,gold_removed:rewrite --max-usd 1.00
.venv/bin/python -B evaluate.py answer (위와 같은 인자 · --persist-dir) --conditions rewrite --max-usd 1.00 \
  --gen-cache <검색 평가 out-dir>/generated.jsonl

# 답변 모델만 로컬(Ollama, http://localhost:11434)로 — 검색 · 프롬프트 · 파서는 같다(비용 0)
.venv/bin/python -B evaluate.py answer (위와 같은 인자) --max-usd 0 --local-model llama3.1:8b

# 여러 답변 실행의 열쇠(key.jsonl)를 한 블라인드 시트로 다시 섞기(sheet_shuffle_seed)
.venv/bin/python -B evaluate.py merge --keys <a/key.jsonl>,<b/key.jsonl> --config configs/baseline.json \
  --eval-config configs/eval_v1.json --out-dir ~/ddingdong-rag/<이름>

# 채점 합산 — sheet.csv의 판정 칸에 정답 · 부분 · 오답 중 하나를 채운 뒤
.venv/bin/python -B evaluate.py score --sheet <sheet.csv> --key <key.jsonl> --out-dir ~/ddingdong-rag/score-<이름>

# 채택 판정 — PREREG 「실험」 절 E1 · E2 규칙을 조항별로(기준선 · 실험의 score · retrieval summary.json + 읽을 실행 · 조건 이름, 인자 전부 필수)
.venv/bin/python -B evaluate.py adopt --experiment E1 \
  --base-score <score/summary.json> --base-run "<실행 이름>" --base-retrieval <retrieval/summary.json> --base-cond <조건> \
  --exp-score <score/summary.json> --exp-run "<실행 이름>" --exp-retrieval <retrieval/summary.json> --exp-cond <조건> \
  --out-dir ~/ddingdong-rag/adopt-<이름>

# v2 채택 판정(eval/PREREG_v2.md) — 1단계 = v1 검색 후보들(Hit@3 → MRR@10 → E5 · E3 · E4 순으로 하나 선택) · 2단계 = H1 검색 후보 1개
.venv/bin/python -B evaluate.py adopt-v2 --stage 1 --base-retrieval <retrieval/summary.json> --base-cond dense \
  --cands E3,E4,E5 --cand-retrievals <json>,<json>,<json> --cand-conds hyde,rewrite,dense --out-dir ~/ddingdong-rag/adopt-<이름>

# v2 2단계 답변 조건 — score summary.json 한 파일의 실행 3개(이름 = score 표의 조건 칸)
.venv/bin/python -B evaluate.py adopt-v2-answers --score <score/summary.json> --cand-v1-run "<이름>" \
  --cand-h1-run "<이름>" --base-h1-run "<이름>" --out-dir ~/ddingdong-rag/adopt-<이름>

# 채점 일관성 — 같은 문항 · 같은 답(앞뒤 공백 제거) · 같은 거절 · 같은 호출 실패 여부인 행끼리 판정이 같은지(시트 안 · 시트 사이)
.venv/bin/python -B evaluate.py consistency --sheets <a.csv>,<b.csv> --keys <a/key.jsonl>,<b/key.jsonl> \
  --out-dir ~/ddingdong-rag/consistency-<이름>
```

결과 v1(검색 · 답변 · 채택 판정 · 로컬 모델 비교 · 오답 분석) = [`eval/results_v1.md`](eval/results_v1.md).
결과 v2(검색 개선 E3 · E4 · E5 · 확인 세트 H1 · 2단계 채택 판정 · 오답 분석) = [`eval/results_v2.md`](eval/results_v2.md).

| 항목 | 결정 |
|---|---|
| 적중 | 정답 조각 하나의 **전체 문자열**을 담은 청크(표시 원문 · 마스킹 반영). 청크 경계에 걸쳐 잘린 조각은 적중 아님 |
| BM25 | 표준 라이브러리 구현. 문서 = 임베딩 본문(제목 경로 줄 + 본문). idf = log(1 + (N − df + 0.5) / (df + 0.5)), 점수 0 문서는 결과에서 뺀다 |
| gold_removed | bm25는 정답 청크를 뺀 문서로 인덱스를 다시 만든다(df · 평균 길이 포함). dense는 넉넉히 받아 뺀 청크를 거른다(벡터 유사도는 다른 문서와 무관). 뺀 청크가 상위 `mrr_cutoff` 안에 나오면 실행 실패 |
| hybrid | dense + bm25를 RRF(점수 = Σ 1 / (`rrf_k` + 순위), 동점은 청크 번호순)로 합친다. 각 목록 깊이 = 상위 50(사전 등록에 없어 결과 전에 고정 — `mrr_cutoff`의 5배). gold_removed:hybrid는 양쪽 목록에서 정답 청크를 뺀다 |
| hyde · rewrite | 답변 모델 · 온도 0 · seed = `random_seed`로 PREREG_v2 프롬프트 원문(테스트가 문자 단위 대조)을 채워 문항마다 한 번 생성 → 검색 벡터 = 원 질문 임베딩과 생성문 임베딩의 산술 평균(llama-index `custom_embedding_strs` → `mean_agg`). retrieval이 `<out-dir>/generated.jsonl`에 남기고(예상 비용 > `--max-usd`면 호출 0), answer는 `--gen-cache`로 그 파일만 읽는다(없는 문항 = 실패). rewrite 제목 목록 = `##` · `###` · 소절 제목을 문서 순서로 각 80자 — 코드 블록 안 줄은 제외(청커와 같은 규칙) |
| 로컬 모델 | Ollama 채팅 API(표준 라이브러리 HTTP) · 온도 0 · seed = `random_seed` · JSON 형식 · `num_ctx` 16384. Ollama는 `num_ctx`를 넘는 프롬프트를 오류 없이 잘라내므로, 서버가 센 입력 토큰이 절반을 넘으면 호출 실패로 처리. 모델 = 「태그@다이제스트 12자」로 기록 |
| 형식 오류 · 호출 실패 | 모델 출력이 JSON이 아니면 거절로 치지 않고 원문을 답으로 남긴다(`format_error`). 로컬 호출 실패는 `call_failed`로 따로 기록하고 10회면 중단 |
| 실행 구분 | 열쇠에 설정 이름(`config`) · 평가셋 이름(`eval_set`)을 남긴다. 합산은 설정 · 조건 · 모델로 실행을 가르고, 평가셋이 둘 이상 섞인 열쇠는 평가셋으로도 가른다(`eval_set`이 없는 이전 열쇠는 qid가 속한 평가셋 파일로 판별) |
| random | 문항마다 `random.Random("<random_seed>:<qid>")` — 실행 순서와 무관하게 고정 |
| 근거 유효 | 답한(거절 안 한) · 답 있는 문항만 센다(not_in_doc은 정답 조각이 없다) |
| 환각 · 호출 실패 | 환각 = not_in_doc에서 거절 없이 오답. 호출 실패 행은 오답으로 채점하되 환각에서 뺀다(지어낸 답이 아님). score는 호출 실패 · 형식 오류 개수와 지연 중앙값도 낸다 |
| 채택 판정 | 규칙 = `evaluate.py`의 상수 + PREREG 원문 인용 주석. 「정답 수」는 개수 비교(「부분」은 정답 아님) · 문항별 뒤집힘은 참고 칸 |
| 토큰 · 달러 | 답변 모델 인코딩(tiktoken, 동봉 캐시)으로 프롬프트 · 출력을 센다 = **추정**(채팅 형식 오버헤드 · 캐시 할인 미반영). 달러 = 토큰 × `configs/prices.json`. 호출 전 예상은 출력 300토큰/회를 가정 |

## MCP 서버

`mcp_server.py` = 이 검색기를 MCP 서버(stdio · 읽기 전용)로 내놓는다. Claude Code 같은 MCP 클라이언트가 decisions.md를 직접 찾는다.
서버는 검색 · 탐색만 하고 **답은 만들지 않는다**(답은 호출한 LLM 몫 — 답변 모델 호출 0). 검색은 기준선(dense · `baseline` 설정) 그대로다.

| 도구 | 입력 | 출력 | 키 |
|---|---|---|---|
| `search_decisions` | `query` · `k`(1~10) | 커밋 · 설정 · 임베더 + 결과[순위 · 점수 · 절 라벨 · 제목 경로 · 근거 표기 `<커밋7>@L시작-L끝` · 본문] + 「결과는 힌트」 안내 | 필요(질의 임베딩 1회). 없으면 도구 오류 — 다른 검색으로 바꾸지 않는다 |
| `list_sections` | `contains`(라벨 · 제목 경로 부분 문자열, 대소문자 무시 · 빈 문자열 = 전부) | 절 라벨을 문서 순서로(라벨 · 첫 제목 경로 · 줄 범위) · 최대 200개 + `truncated` | 불필요 |
| `get_section` | `section`(라벨) · `offset`(≥ 0) | 그 라벨 + 하위 라벨(`6.3(a)` · `6.3 › …` — `6.30` · `16.3`은 아님) 청크를 8개씩 + 전체 수 · `next_offset` | 불필요 |

- **결과는 힌트다** — 인용 전에 원문(`git show <커밋>:docs/decisions.md`)과 대조한다. 본문은 마스킹한 원문에서만 나온다.
- 검색어가 문서 용어와 어긋나면 `list_sections`로 제목을 보고 그 용어로 다시 검색하거나 `get_section`으로 펼친다. `list_sections`는 제목만 찾는다(본문 단어는 `search_decisions`).
- 범위 밖 · 빠진 인자 · 없는 라벨은 도구 오류로 돌아온다(서버는 계속 돈다). stdout은 MCP 프로토콜 전용 — 로그는 stderr.
- 시연 기록(Claude Code 대화 원문 · 근거 줄 대조) = [`docs/mcp_demo.md`](docs/mcp_demo.md)
- 기동 인자 `--commit` · `--config` · `--persist-dir`는 전부 필수(기본값 없음). 기동 검사 — 설정 해시 = 인덱스 manifest · manifest 커밋 = `--commit` · 인덱스는 repo 밖 · 그 커밋의 마스킹 원문 청크(개수 · 해시) = 인덱스 청크. 하나라도 어긋나면 기동 거부. 가짜 임베딩 인덱스는 `--allow-mock-index`(테스트용)일 때만 연다.

등록(사용자 몫 — 자리표시자를 채운다. `<index>`는 `<commit>` · `baseline`으로 만든 인덱스):

```sh
# Claude Code(사용자 범위)
claude mcp add --scope user decisions-rag -e PYTHONDONTWRITEBYTECODE=1 -- \
  <repo>/tools/decisions-rag/.venv/bin/python -B <repo>/tools/decisions-rag/mcp_server.py \
  --commit <commit> --config <repo>/tools/decisions-rag/configs/baseline.json --persist-dir <index>
```

Claude Desktop(`claude_desktop_config.json`의 `mcpServers`):

```json
{
  "mcpServers": {
    "decisions-rag": {
      "command": "<repo>/tools/decisions-rag/.venv/bin/python",
      "args": ["-B", "<repo>/tools/decisions-rag/mcp_server.py", "--commit", "<commit>",
               "--config", "<repo>/tools/decisions-rag/configs/baseline.json", "--persist-dir", "<index>"],
      "env": {"PYTHONDONTWRITEBYTECODE": "1"}
    }
  }
}
```

키는 서버가 `tools/decisions-rag/.env`에서 읽는다(설정 파일에 키를 넣지 않는다). 키가 없어도 `list_sections` · `get_section`은 돈다.

## 다음 PR

- ③ 기준선 측정 · 오답 분류 · 실험 E1(취소선 폐기 표시) · E2(하이브리드 검색) · 로컬 모델(Ollama) 비교 — 결과 = `eval/results_v1.md`
- ④ MCP 서버 — `mcp_server.py`(위 「MCP 서버」 절)
