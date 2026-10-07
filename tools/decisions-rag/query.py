"""인덱스 질의 — 상위 k 청크 출력, --answer면 답변 모델 호출(근거 표기는 코드가 붙인다).

  python -B query.py --persist-dir <인덱스> --config configs/baseline.json -k 5 "<질문>" [--answer]

검색 결과는 힌트다 — 인용 전에 원문을 grep으로 재확인할 것.
"""
import argparse
import json
import sys
import time
import urllib.request

import common

ANSWER_RULES = (
    "너는 프로젝트 결정 문서 검색 도우미다. 아래 [n] 번호가 붙은 청크만 근거로 답한다.\n"
    "규칙: 주어진 청크에 없는 내용은 답하지 말고 거절한다. 추측 금지.\n"
    '출력은 JSON 하나: {"answer": "<답 또는 빈 문자열>", "evidence": [<근거 청크 번호 정수>], "refused": <true|false>}\n'
)


def load_manifest(persist_dir, cfg):
    manifest = json.loads((persist_dir / common.MANIFEST).read_text(encoding="utf-8"))
    if manifest["config_hash"] != common.config_hash(cfg):
        raise ValueError(f"설정 해시가 인덱스와 다르다 — 인덱스={manifest['config_name']}"
                         f"({manifest['config_hash'][:12]}), 지금={cfg['name']}({common.config_hash(cfg)[:12]})")
    return manifest


def cite(meta):
    """근거 표기 = 코드가 메타데이터에서 만든다(모델 출력 문자열을 쓰지 않는다)."""
    return {"section": meta["section"], "heading_path": meta["heading_path"],
            "ref": f"{meta['commit'][:7]}@L{meta['line_start']}-L{meta['line_end']}"}


def build_prompt(question, metas, bodies):
    parts = [ANSWER_RULES]
    for i, body in enumerate(bodies, 1):
        parts.append(f"[{i}] ({metas[i - 1]['heading_path']})\n{body}\n")
    parts.append(f"질문: {question}")
    return "\n".join(parts)


def parse_answer(raw, metas):
    """모델 출력(JSON) → {answer, refused, citations, dropped_evidence}. 모델의 번호만 신뢰한다."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("모델 출력이 JSON이 아니다")
    if not isinstance(data, dict):
        raise ValueError("모델 출력이 JSON 객체가 아니다")
    refused = data.get("refused") is True
    good, dropped = [], []
    for e in data.get("evidence") or []:
        if isinstance(e, int) and not isinstance(e, bool) and 1 <= e <= len(metas):
            if e not in good:
                good.append(e)
        else:
            dropped.append(e)
    if dropped:
        print(f"경고: 범위 밖 · 잘못된 근거 번호를 버렸다: {dropped}", file=sys.stderr)
    return {
        "answer": "" if refused else str(data.get("answer", "")),
        "refused": refused,
        "citations": [dict(chunk=e, **cite(metas[e - 1])) for e in good],
        "dropped_evidence": dropped,
    }


def make_llm(cfg, key):
    from llama_index.llms.openai import OpenAI
    from llama_index.llms.openai.utils import O1_MODELS
    if cfg["answer_model"] in O1_MODELS:
        # 이 계열은 llama-index-llms-openai가 temperature를 조용히 1.0으로 바꾼다 — 0 보장을 못 한다.
        raise ValueError(f"답변 모델 {cfg['answer_model']}은 temperature 0을 보장하지 못한다(추론 모델)")
    llm = OpenAI(model=cfg["answer_model"], temperature=0, api_key=key, max_retries=1,
                 additional_kwargs={"response_format": {"type": "json_object"}})
    return lambda prompt: llm.complete(prompt).text


OLLAMA_URL = "http://localhost:11434"
# Ollama는 num_ctx를 넘는 프롬프트를 오류 없이 앞을 잘라 약 절반만 남긴다(0.40.0 실측: 256 → 130).
# → 넉넉히 잡고, 서버가 센 입력 토큰이 절반을 넘으면 잘렸을 수 있다고 보고 실패로 처리한다.
LOCAL_NUM_CTX = 16384


class LocalCallError(RuntimeError):
    """로컬 모델 호출 실패(연결 · 시간 초과 · 응답 형식) — 모델 출력의 JSON 형식 오류와 구분한다."""


def local_model_digest(model, opener=urllib.request.urlopen):
    """→ 설치된 모델의 다이제스트(태그 목록 API). 없으면 ValueError."""
    with opener(f"{OLLAMA_URL}/api/tags", timeout=10) as r:
        tags = {m["name"]: m["digest"] for m in json.load(r)["models"]}
    if model not in tags:
        raise ValueError(f"Ollama에 모델이 없다: {model}")
    return tags[model]


def make_local_llm(model, seed, opener=urllib.request.urlopen):
    """Ollama 채팅 API(표준 라이브러리 HTTP) → complete(prompt) = (출력, 입력 토큰, 출력 토큰). 사용자 메시지 1개 = OpenAI 경로와 같은 형태."""
    def complete(prompt):
        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "format": "json",
                "options": {"temperature": 0, "seed": seed, "num_ctx": LOCAL_NUM_CTX}}
        req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with opener(req, timeout=600) as r:
                data = json.load(r)
            text, n_in, n_out = data["message"]["content"], data["prompt_eval_count"], data["eval_count"]
        except (OSError, ValueError, KeyError) as e:
            raise LocalCallError(f"{type(e).__name__}") from e
        if n_in > LOCAL_NUM_CTX // 2:
            raise LocalCallError(f"입력 {n_in}토큰 > num_ctx {LOCAL_NUM_CTX}의 절반 — 잘렸을 수 있다")
        return text, n_in, n_out
    return complete


def open_index(persist, manifest):
    """manifest의 임베더로 Chroma 인덱스를 연다 → (인덱스, OpenAI 키 또는 None). 키가 필요한데 없으면 종료."""
    key = None
    if manifest["embedder"] == "mock":
        from llama_index.core.embeddings import MockEmbedding
        embed_model = MockEmbedding(embed_dim=int(manifest["embed_model"].split("-")[1]))
    else:
        key = common.openai_key()
        if not key:
            common.fail("OPENAI_API_KEY가 없다 — tools/decisions-rag/.env에 넣을 것")
        from llama_index.embeddings.openai import OpenAIEmbedding
        embed_model = OpenAIEmbedding(model=manifest["embed_model"], api_key=key, max_retries=1)

    from llama_index.core import VectorStoreIndex
    from llama_index.vector_stores.chroma import ChromaVectorStore
    col = common.chroma_client(persist).get_collection(common.COLLECTION, embedding_function=None)
    index = VectorStoreIndex.from_vector_store(ChromaVectorStore(chroma_collection=col), embed_model=embed_model)
    return index, key


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--persist-dir", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("-k", type=int, required=True)
    ap.add_argument("question")
    ap.add_argument("--answer", action="store_true")
    a = ap.parse_args(argv)

    try:
        cfg = common.load_config(a.config)
        persist = common.check_outside_repo(a.persist_dir)
        manifest = load_manifest(persist, cfg)
    except (ValueError, FileNotFoundError) as e:
        common.fail(str(e))
    if a.k != cfg["top_k"]:
        print(f"주의: -k {a.k} ≠ 설정 top_k {cfg['top_k']} — 평가 조건과 다른 실행", file=sys.stderr)

    t0 = time.monotonic()
    index, key = open_index(persist, manifest)
    hits = index.as_retriever(similarity_top_k=a.k).retrieve(a.question)
    print(f"질문: {a.question}  (인덱스 {manifest['commit'][:7]} · {manifest['config_name']} · "
          f"{manifest['embedder']} · {time.monotonic() - t0:.2f}초)")
    metas = [h.node.metadata for h in hits]
    for i, h in enumerate(hits, 1):
        m = h.node.metadata
        head = m["display"][:160].replace("\n", " ⏎ ")
        print(f"[{i}] {h.score:.4f}  {m['section']}  {m['commit'][:7]}@L{m['line_start']}-L{m['line_end']}\n"
              f"    {m['heading_path']}\n    {head}")

    if a.answer:
        if manifest["embedder"] == "mock":
            common.fail("--answer는 실임베딩 인덱스에서만 쓴다(가짜 임베딩 검색 결과로 답하지 않는다)")
        try:
            complete = make_llm(cfg, key)
        except ValueError as e:
            common.fail(str(e))
        bodies = [h.node.get_content().split("\n", 1)[1] for h in hits]   # 제목 경로 줄은 프롬프트에 따로 붙인다
        result = parse_answer(complete(build_prompt(a.question, metas, bodies)), metas)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
