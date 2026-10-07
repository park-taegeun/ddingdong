"""평가기 — eval/PREREG.md에 등록한 규칙대로 검색 · 답변을 잰다.

  # 검색 평가(bm25 · random · gold_removed:bm25 = 네트워크 0)
  python -B evaluate.py retrieval --commit <커밋> --config configs/baseline.json --eval-config configs/eval_v1.json \
      --conditions bm25,random,gold_removed:bm25 --out-dir <repo 밖 빈 폴더> [--persist-dir <dense 인덱스>]
  # 답변 평가 → 블라인드 채점 시트(sheet.csv) + 열쇠(key.jsonl). 답변 모델 = OpenAI 호출
  python -B evaluate.py answer  (위와 같은 인자)
  # 채점 합산 — 사용자가 판정 칸을 채운 시트 + 열쇠
  python -B evaluate.py score --sheet <sheet.csv> --key <key.jsonl> --out-dir <repo 밖 빈 폴더>

조건 = bm25 · random · dense · gold_removed:bm25 · gold_removed:dense. dense는 --persist-dir 인덱스가 필요하다.
"""
import argparse
import csv
import hashlib
import json
import math
import random
import re
import sys
import time
from collections import Counter

import chunker
import common
import query

EVAL_KEYS = ("name", "eval_set", "eval_set_sha256", "hit_k", "mrr_cutoff", "answer_top_k", "bm25_k1", "bm25_b",
             "bm25_tokenizer", "rrf_k", "random_seed", "sheet_shuffle_seed")
TOKENIZER = "word_ascii+hangul_bigram_v1"
TYPES = ("fact", "identifier", "reversal", "not_in_doc", "false_premise")
NO_ANSWER = "not_in_doc"                       # 검색 지표에서 뺀다
CONDITIONS = ("bm25", "random", "dense", "gold_removed:bm25", "gold_removed:dense")
VERDICTS = ("정답", "부분", "오답")
SHEET_COLS = ("시트 번호", "질문", "기대 답", "모델 답", "거절 여부", "판정", "메모")

WORD_RE = re.compile(r"[a-z0-9_]+")
HANGUL_RE = re.compile(r"[가-힣]+")


class EvalError(ValueError):
    """평가기 결함 — 실행 실패로 처리한다."""


def load_eval_config(path, base_cfg):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    missing = [k for k in EVAL_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"평가 설정에 값이 없다(기본값 금지): {', '.join(missing)}")
    unknown = sorted(set(cfg) - set(EVAL_KEYS))
    if unknown:
        raise ValueError(f"알 수 없는 평가 설정 키: {', '.join(unknown)}")
    if cfg["bm25_tokenizer"] != TOKENIZER:
        raise ValueError(f"모르는 토크나이저: {cfg['bm25_tokenizer']}")
    if cfg["answer_top_k"] != base_cfg["top_k"]:
        raise ValueError(f"answer_top_k {cfg['answer_top_k']} ≠ 기준선 top_k {base_cfg['top_k']}")
    return cfg


def load_eval_set(ecfg):
    data = (common.TOOL_DIR / ecfg["eval_set"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != ecfg["eval_set_sha256"]:
        raise ValueError("평가셋 sha256이 등록값과 다르다")
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    bad = [r["qid"] for r in rows if r["type"] not in TYPES or r["gold_match"] != "any"]
    if bad:
        raise ValueError(f"모르는 유형 · 적중 방식: {', '.join(bad)}")
    return rows


def contaminated(rows, doc):
    """질문 문장이 원문에 그대로 있는 문항(질문이 자기 답을 검색하게 된다)."""
    return [r["qid"] for r in rows if r["question"] in doc]


def gold_chunks(chunks, anchors):
    """정답 조각 하나의 전체 문자열을 담은 청크(표시 원문 기준). 경계에 걸쳐 잘린 조각은 적중이 아니다."""
    return frozenset(i for i, c in enumerate(chunks) if any(a in c.display for a in anchors))


def tokenize(text):
    text = text.lower()
    toks = WORD_RE.findall(text)
    for run in HANGUL_RE.findall(text):
        toks += [run] if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)]
    return toks


class BM25:
    """Okapi BM25(idf = log(1 + (N − df + 0.5) / (df + 0.5))). 점수 0인 문서는 돌려주지 않는다."""

    def __init__(self, docs, k1, b):
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokenize(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = sum(self.lens) / len(self.lens)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5))
                    for t, f in Counter(t for tf in self.tfs for t in tf).items()}

    def search(self, text, k):
        q = tokenize(text)
        scored = []
        for i, (tf, dl) in enumerate(zip(self.tfs, self.lens)):
            s = sum(self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
                    for t in q if t in tf)
            if s > 0:
                scored.append((-s, i))
        return [i for _, i in sorted(scored)[:k]]


def bm25_retriever(chunks, ecfg):
    docs = [c.embed_text for c in chunks]
    full = BM25(docs, ecfg["bm25_k1"], ecfg["bm25_b"])

    def search(row, k, exclude=frozenset()):
        if not exclude:
            return full.search(row["question"], k)
        keep = [i for i in range(len(docs)) if i not in exclude]          # 뺀 문서로 인덱스를 다시 만든다(df · 평균 길이 포함)
        return [keep[j] for j in BM25([docs[i] for i in keep], ecfg["bm25_k1"], ecfg["bm25_b"]).search(row["question"], k)]
    return search


def random_retriever(chunks, ecfg):
    def search(row, k, exclude=frozenset()):
        rng = random.Random(f"{ecfg['random_seed']}:{row['qid']}")       # 문항별 고정 — 실행 순서와 무관
        return rng.sample([i for i in range(len(chunks)) if i not in exclude], k)
    return search


def dense_retriever(chunks, cfg, commit, persist_dir, allow_mock):
    persist = common.check_outside_repo(persist_dir)
    manifest = query.load_manifest(persist, cfg)
    if common.resolve_commit(manifest["commit"]) != commit:
        raise ValueError(f"dense 인덱스 커밋 {manifest['commit'][:7]} ≠ 평가 커밋 {commit[:7]}")
    if manifest["embedder"] == "mock" and not allow_mock:
        raise ValueError("가짜 임베딩 인덱스로 답하지 않는다")
    index, _ = query.open_index(persist, manifest)

    def search(row, k, exclude=frozenset()):
        # 벡터 유사도는 다른 문서와 무관 → 넉넉히 받아 뺀 청크를 거르면 「뺀 인덱스」 검색과 같다.
        hits = index.as_retriever(similarity_top_k=k + len(exclude)).retrieve(row["question"])
        out = []
        for h in hits:
            i = int(h.node.node_id[1:6])                                # build_nodes의 id = c{순번:05d}-{해시}
            if h.node.metadata["chunk_hash"] != chunks[i].meta["chunk_hash"]:
                raise EvalError("dense 인덱스 청크가 지금 청크와 다르다")
            if i not in exclude:
                out.append(i)
        return out[:k]
    return search


def prepare(a, need_dense_mock_ok):
    """공통 준비: 설정 · 평가셋 · 커밋 고정 원문 · 청크 · 검색기 · 출력 폴더."""
    cfg = common.load_config(a.config)
    ecfg = load_eval_config(a.eval_config, cfg)
    rows = load_eval_set(ecfg)
    commit = common.resolve_commit(a.commit)
    if {common.resolve_commit(r["doc_commit"]) for r in rows} != {commit}:
        raise ValueError("평가셋의 doc_commit과 --commit이 다르다")
    conditions = a.conditions.split(",")
    unknown = [c for c in conditions if c not in CONDITIONS]
    if unknown:
        raise ValueError(f"모르는 조건: {', '.join(unknown)}")
    raw = common.read_doc_at(commit)
    dirty = contaminated(rows, raw)
    if dirty:
        raise ValueError(f"질문 문장이 원문에 있다(오염): {', '.join(dirty)}")
    chunks = chunker.chunk(common.mask_secrets(raw), commit, cfg)
    retrievers = {"bm25": bm25_retriever(chunks, ecfg), "random": random_retriever(chunks, ecfg)}
    if any(c.endswith("dense") for c in conditions):
        if not a.persist_dir:
            raise ValueError("dense 조건은 --persist-dir가 필요하다")
        retrievers["dense"] = dense_retriever(chunks, cfg, commit, a.persist_dir, need_dense_mock_ok)
    out = prepare_out_dir(a.out_dir)
    run = {"commit": commit, "config": cfg["name"], "config_hash": common.config_hash(cfg),
           "eval_config": ecfg, "conditions": conditions, "chunks": len(chunks),
           "chunker_version": chunker.CHUNKER_VERSION}
    (out / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg, ecfg, rows, chunks, retrievers, conditions, out


def prepare_out_dir(path):
    out = common.check_outside_repo(path)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError(f"--out-dir가 비어 있지 않다(덮어쓰기 금지): {path}")
    out.mkdir(parents=True, exist_ok=True)
    return out


def split_condition(cond):
    return cond.split(":")[-1], cond.startswith("gold_removed:")


# ---------- 검색 평가 ----------

def evaluate_retrieval(rows, chunks, ecfg, retrievers, conditions):
    depth = max(ecfg["hit_k"], ecfg["mrr_cutoff"])
    records = []
    for cond in conditions:
        base, removed = split_condition(cond)
        for r in rows:
            if r["type"] == NO_ANSWER:
                continue
            gold = gold_chunks(chunks, r["gold_anchors"])
            if not gold:
                raise EvalError(f"{r['qid']}: 정답 조각을 담은 청크가 없다")
            t0 = time.monotonic()
            ranking = retrievers[base](r, depth, gold if removed else frozenset())
            sec = time.monotonic() - t0
            rank = next((p for p, i in enumerate(ranking[:ecfg["mrr_cutoff"]], 1) if i in gold), None)
            records.append({"condition": cond, "qid": r["qid"], "type": r["type"], "gold_chunks": sorted(gold),
                            "ranking": ranking, "hit": any(i in gold for i in ranking[:ecfg["hit_k"]]),
                            "rank": rank, "retrieval_sec": round(sec, 4)})
        if removed:
            leaked = [x["qid"] for x in records if x["condition"] == cond and x["rank"] is not None]
            if leaked:
                raise EvalError(f"{cond}: 뺀 정답 청크가 검색됐다 — 평가기 결함 ({', '.join(leaked)})")
    return records


def summarize_retrieval(records, conditions):
    out = []
    for cond in conditions:
        recs = [x for x in records if x["condition"] == cond]
        for scope in ("전체",) + tuple(t for t in TYPES if t != NO_ANSWER):
            sub = recs if scope == "전체" else [x for x in recs if x["type"] == scope]
            n = len(sub)
            out.append({"condition": cond, "scope": scope, "n": n, "hits": sum(x["hit"] for x in sub),
                        "mrr": sum(1 / x["rank"] for x in sub if x["rank"]) / n if n else 0.0})
    return out


def retrieval_table(summary, ecfg):
    k, c = ecfg["hit_k"], ecfg["mrr_cutoff"]
    lines = [f"| 조건 | 범위 | Hit@{k} | MRR@{c} |", "|---|---|---|---|"]
    lines += [f"| {s['condition']} | {s['scope']} | n = {s['n']} 중 {s['hits']} ({s['hits'] / s['n']:.3f}) | {s['mrr']:.3f} |"
              for s in summary]
    return "\n".join(lines)


# ---------- 답변 평가 ----------

EST_COMPLETION_TOKENS = 300   # 호출 전 예상 비용에만 쓰는 답 1회 출력 토큰 가정(실제 출력은 기록에서 센다)


def run_answers(rows, chunks, cfg, ecfg, retrievers, conditions, complete, prices, max_usd):
    """조건 × 문항마다 상위 answer_top_k → 프롬프트를 모두 만든 뒤 예상 비용 > max_usd면 호출 없이 실패 → 답변 모델 → 기록."""
    common.use_bundled_tiktoken_cache()
    import tiktoken
    model = cfg["answer_model"]
    enc = tiktoken.encoding_for_model(model)
    plans = []
    for cond in conditions:
        base, removed = split_condition(cond)
        for r in rows:
            gold = gold_chunks(chunks, r["gold_anchors"])
            t0 = time.monotonic()
            ids = retrievers[base](r, ecfg["answer_top_k"], gold if removed else frozenset())
            sec = time.monotonic() - t0
            metas = [chunks[i].meta for i in ids]
            prompt = query.build_prompt(r["question"], metas, [chunks[i].body for i in ids])
            plans.append((cond, r, gold, ids, metas, prompt, sec, len(enc.encode(prompt))))
    est = sum(common.usd(prices, model, input=p[-1], output=EST_COMPLETION_TOKENS) for p in plans)
    print(f"답변 {len(plans)}회 예상 비용 ${est:.4f} (입력 = 로컬 tiktoken 추정 · 출력 {EST_COMPLETION_TOKENS}토큰/회 가정)"
          f" · 상한 ${max_usd:.2f}")
    if est > max_usd:
        raise ValueError(f"예상 비용 ${est:.4f} > 상한 ${max_usd:.2f} — 호출 없이 중단")
    items = []
    for cond, r, gold, ids, metas, prompt, retrieval_sec, prompt_tokens in plans:
        t1 = time.monotonic()
        raw = complete(prompt)
        t2 = time.monotonic()
        res = query.parse_answer(raw, metas)
        cited = [ids[c["chunk"] - 1] for c in res["citations"]]
        answered = not res["refused"]
        completion_tokens = len(enc.encode(raw))
        items.append({
            "qid": r["qid"], "type": r["type"], "condition": cond, "model": model,
            "question": r["question"], "expected_answer": r["expected_answer"],
            "answer": res["answer"], "refused": res["refused"], "citations": res["citations"],
            "retrieved": ids,
            # 답한 · 답 있는 문항만 판정한다(not_in_doc은 정답 조각이 없다)
            "evidence_valid": any(i in gold for i in cited) if answered and r["type"] != NO_ANSWER else None,
            "trap_in_answer": any(t in res["answer"] for t in r["trap_anchors"]) if r["type"] == "reversal" else None,
            "retrieval_sec": round(retrieval_sec, 4), "answer_sec": round(t2 - t1, 4),
            # 토큰 = 로컬 tiktoken 추정(채팅 형식 오버헤드 · 캐시 할인 미반영)
            "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
            "cost_usd_est": common.usd(prices, model, input=prompt_tokens, output=completion_tokens),
        })
    return items


def make_sheet(items, seed):
    """→ (시트 행, 열쇠). 시트엔 조건 · 모델 · 문항 번호가 없다."""
    order = list(range(len(items)))
    random.Random(seed).shuffle(order)
    sheet, key = [], []
    for no, idx in enumerate(order, 1):
        it = items[idx]
        sheet.append([no, it["question"], it["expected_answer"], it["answer"], "예" if it["refused"] else "아니오", "", ""])
        key.append(dict(sheet_no=no, **it))
    return sheet, key


def write_sheet(out, sheet, key):
    with open(out / "sheet.csv", "w", encoding="utf-8-sig", newline="") as f:   # 엑셀이 한글을 읽도록 BOM
        w = csv.writer(f)
        w.writerow(SHEET_COLS)
        w.writerows(sheet)
    (out / "key.jsonl").write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in key), encoding="utf-8")


# ---------- 채점 합산 ----------

def read_sheet(path):
    """→ {시트 번호: 판정}. 판정이 허용 3단어 밖이면 줄 번호와 함께 거부."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        if tuple(next(reader)) != SHEET_COLS:
            raise ValueError(f"시트 머리줄이 다르다 — {' · '.join(SHEET_COLS)}")
        verdicts, bad, start = {}, [], reader.line_num + 1
        for row in reader:
            v = row[5].strip() if len(row) == len(SHEET_COLS) else None
            if v not in VERDICTS:
                bad.append(f"{start}줄")
            else:
                verdicts[int(row[0])] = v
            start = reader.line_num + 1
    if bad:
        raise ValueError(f"판정 값은 {' · '.join(VERDICTS)}만 허용 — {', '.join(bad)}")
    return verdicts


def score(verdicts, key):
    if set(verdicts) != {k["sheet_no"] for k in key}:
        raise ValueError("시트 번호가 열쇠와 다르다")
    out = []
    for cond in dict.fromkeys(k["condition"] for k in key):
        ks = [dict(k, verdict=verdicts[k["sheet_no"]]) for k in key if k["condition"] == cond]
        ev = [k["evidence_valid"] for k in ks if k["evidence_valid"] is not None]
        out.append({
            "condition": cond, "n": len(ks),
            "verdicts": {t: dict(Counter(k["verdict"] for k in ks if scope_ok(k, t))) for t in ("전체",) + TYPES},
            "hallucination": sum(k["type"] == NO_ANSWER and not k["refused"] and k["verdict"] == "오답" for k in ks),
            "over_refusal": sum(k["type"] != NO_ANSWER and k["refused"] for k in ks),
            "evidence_valid": [sum(ev), len(ev)],
            "reversal_trap_auto": sum(bool(k["trap_in_answer"]) for k in ks),
            "reversal_wrong": sum(k["type"] == "reversal" and k["verdict"] == "오답" for k in ks),
            "retrieval_sec_mean": sum(k["retrieval_sec"] for k in ks) / len(ks),
            "answer_sec_mean": sum(k["answer_sec"] for k in ks) / len(ks),
            "prompt_tokens": sum(k["prompt_tokens"] for k in ks),
            "completion_tokens": sum(k["completion_tokens"] for k in ks),
            "cost_usd_est": sum(k["cost_usd_est"] for k in ks),
        })
    return out


def scope_ok(k, scope):
    return scope == "전체" or k["type"] == scope


def score_table(results):
    lines = ["| 조건 | 범위 | 정답 | 부분 | 오답 |", "|---|---|---|---|---|"]
    for s in results:
        for scope, c in s["verdicts"].items():
            lines.append(f"| {s['condition']} | {scope} | {c.get('정답', 0)} | {c.get('부분', 0)} | {c.get('오답', 0)} |")
    lines += ["", "| 조건 | 환각 | 과잉 거절 | 근거 유효 | 번복 오답(자동 · 채점) | 검색 초(평균) | 답변 초(평균) | 토큰(입력 · 출력, 추정) | 달러(추정) |",
              "|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {s['condition']} | {s['hallucination']} | {s['over_refusal']} | {s['evidence_valid'][0]} / {s['evidence_valid'][1]}"
              f" | {s['reversal_trap_auto']} · {s['reversal_wrong']} | {s['retrieval_sec_mean']:.3f} | {s['answer_sec_mean']:.3f}"
              f" | {s['prompt_tokens']} · {s['completion_tokens']} | {s['cost_usd_est']:.4f} |" for s in results]
    return "\n".join(lines)


# ---------- CLI ----------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("retrieval", "answer"):
        p = sub.add_parser(name)
        p.add_argument("--commit", required=True)
        p.add_argument("--config", required=True)
        p.add_argument("--eval-config", required=True)
        p.add_argument("--conditions", required=True)
        p.add_argument("--out-dir", required=True)
        p.add_argument("--persist-dir")
    sub.choices["answer"].add_argument("--max-usd", type=float, required=True, help="답변 호출 예상 비용 상한(달러)")
    p = sub.add_parser("score")
    p.add_argument("--sheet", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)

    try:
        if a.cmd == "score":
            verdicts = read_sheet(a.sheet)
            with open(a.key, encoding="utf-8") as f:
                key = [json.loads(line) for line in f if line.strip()]
            results = score(verdicts, key)
            out = prepare_out_dir(a.out_dir)
            table = score_table(results)
        elif a.cmd == "retrieval":
            cfg, ecfg, rows, chunks, retrievers, conditions, out = prepare(a, need_dense_mock_ok=True)
            records = evaluate_retrieval(rows, chunks, ecfg, retrievers, conditions)
            results = summarize_retrieval(records, conditions)
            (out / "retrieval.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in records),
                                                 encoding="utf-8")
            table = retrieval_table(results, ecfg)
        else:
            key = common.openai_key()
            if not key:
                common.fail("OPENAI_API_KEY가 없다 — tools/decisions-rag/.env에 넣을 것")
            cfg, ecfg, rows, chunks, retrievers, conditions, out = prepare(a, need_dense_mock_ok=False)
            items = run_answers(rows, chunks, cfg, ecfg, retrievers, conditions, query.make_llm(cfg, key),
                                common.load_prices(cfg), a.max_usd)
            write_sheet(out, *make_sheet(items, ecfg["sheet_shuffle_seed"]))
            print(f"시트 {len(items)}행 → {out / 'sheet.csv'} (열쇠 key.jsonl은 채점 전에 열지 말 것)")
            print(f"토큰(추정) 입력 {sum(i['prompt_tokens'] for i in items)} · 출력 {sum(i['completion_tokens'] for i in items)}"
                  f" · 비용 추정 ${sum(i['cost_usd_est'] for i in items):.4f}"
                  f" · 답변 초(평균) {sum(i['answer_sec'] for i in items) / len(items):.3f}")
            return 0
    except (ValueError, FileNotFoundError) as e:
        common.fail(str(e))
    (out / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(table + "\n", encoding="utf-8")
    print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
