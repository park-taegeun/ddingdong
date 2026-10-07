"""decisions.md(커밋 고정) → 청크 → 임베딩(캐시) → Chroma 저장 + manifest.json.

  python -B index.py --commit <해시> --config configs/baseline.json --persist-dir <repo 밖> \
      --embed-cache <repo 밖> [--dry-run] [--mock-embed]

--dry-run   = 청크 통계 · 비밀값 점검 · 토큰 수 · 예상 비용만(네트워크 0, 저장 0).
--mock-embed = 가짜 임베딩(네트워크 0) — 배관 스모크 전용. manifest에 embedder=mock으로 남는다.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import chunker
import common

MOCK_DIM = 8


def chunk_stats(chunks, cfg):
    sizes = sorted(len(c.display) for c in chunks)
    over = [c for c in chunks if len(c.display) > cfg["chunk_max_chars"]]
    return {
        "chunks": len(chunks),
        "chars_min": sizes[0], "chars_median": statistics.median(sizes),
        "chars_p90": sizes[int(len(sizes) * 0.9)], "chars_max": sizes[-1],
        "strikethrough_chunks": sum(c.meta["has_strikethrough"] for c in chunks),
        "over_max_chunks": [f"{c.meta['section']} L{c.meta['line_start']}-L{c.meta['line_end']} ({len(c.display)}자)"
                            for c in over],
    }


def build_nodes(chunks):
    from llama_index.core.schema import TextNode
    nodes = []
    for i, c in enumerate(chunks):
        meta = dict(c.meta, display=c.display)
        nodes.append(TextNode(
            id_=f"c{i:05d}-{c.meta['chunk_hash']}",
            text=c.embed_text,
            metadata=meta,
            # 메타데이터 키 · 값은 임베딩 · 답변 본문에 넣지 않는다.
            excluded_embed_metadata_keys=list(meta),
            excluded_llm_metadata_keys=list(meta),
        ))
    return nodes


def embed_with_cache(texts, hashes, emb, cache_dir):
    """청크 해시 기준 캐시 — 같은 청크는 다시 임베딩하지 않는다."""
    cache_file = cache_dir / f"{emb.model_name}.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    todo = [(h, t) for h, t in zip(hashes, texts) if h not in cache]
    if todo:
        vectors = emb.get_text_embedding_batch([t for _, t in todo])
        for (h, _), v in zip(todo, vectors):
            cache[h] = v
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache), encoding="utf-8")
    return [cache[h] for h in hashes], len(todo)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--persist-dir", required=True)
    ap.add_argument("--embed-cache", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock-embed", action="store_true")
    a = ap.parse_args(argv)

    t0 = time.monotonic()
    try:
        cfg = common.load_config(a.config)
        persist = common.check_outside_repo(a.persist_dir)
        cache_dir = common.check_outside_repo(a.embed_cache)
        commit = common.resolve_commit(a.commit)
    except ValueError as e:
        common.fail(str(e))

    text = common.read_doc_at(commit)
    secrets = common.scan_secrets(text)
    chunks = chunker.chunk(common.mask_secrets(text), commit, cfg)
    print(f"원문: docs/decisions.md@{commit[:7]} · {len(text.splitlines())}줄 · {len(text)}자")

    def where(lines):
        return sorted({c.meta["section"] for c in chunks for n in lines
                       if c.meta["line_start"] <= n <= c.meta["line_end"]})
    print("비밀값 · 개인정보 점검(개수 · 위치=절, 값 출력 없음):")
    for kind, lines in secrets.items():
        print(f"  {kind}: {len(lines)}" + (f" — {', '.join(where(lines))}" if lines else ""))
    blocking = [k for k in common.BLOCKING_SECRETS if secrets[k]]
    if blocking:
        common.fail(f"실제 키 · 토큰 형태 발견({', '.join(blocking)}) — 인덱싱 중단", code=3)

    stats = chunk_stats(chunks, cfg)
    stats["split_units"] = chunker.count_oversized_units(common.mask_secrets(text), cfg)
    print("청크 통계:", json.dumps(stats, ensure_ascii=False, indent=2))

    common.use_bundled_tiktoken_cache()
    import tiktoken
    enc = tiktoken.encoding_for_model(cfg["embed_model"])
    tokens = sum(len(enc.encode(c.embed_text)) for c in chunks)
    cost = tokens / 1_000_000 * cfg["embed_price_usd_per_1m_tokens"]
    print(f"임베딩 토큰 수: {tokens} (상한 {cfg['max_embed_tokens']}) · 예상 비용 ${cost:.4f} (캐시 적중분 미차감)")
    if tokens > cfg["max_embed_tokens"]:
        common.fail("임베딩 토큰 수가 설정 상한을 넘는다 — 호출 전 중단", code=4)
    if a.dry_run:
        print("dry-run: 네트워크 · 저장 없이 종료")
        return 0

    if persist.exists() and any(persist.iterdir()):
        common.fail(f"--persist-dir가 비어 있지 않다(덮어쓰기 금지): {a.persist_dir}")

    nodes = build_nodes(chunks)
    from llama_index.core.schema import MetadataMode
    texts = [n.get_content(metadata_mode=MetadataMode.EMBED) for n in nodes]
    if texts != [c.embed_text for c in chunks]:   # python -O에서도 살아 있도록 assert를 쓰지 않는다
        common.fail("임베딩 본문에 메타데이터가 섞였다")

    if a.mock_embed:
        from llama_index.core.embeddings import MockEmbedding
        embed_model, embedder, new_embeds = MockEmbedding(embed_dim=MOCK_DIM), "mock", 0
    else:
        key = common.openai_key()
        if not key:
            common.fail("OPENAI_API_KEY가 없다 — tools/decisions-rag/.env에 넣거나 --mock-embed/--dry-run을 쓸 것")
        from llama_index.embeddings.openai import OpenAIEmbedding
        embed_model, embedder = OpenAIEmbedding(model=cfg["embed_model"], api_key=key, max_retries=1), "openai"
        vectors, new_embeds = embed_with_cache(texts, [c.meta["chunk_hash"] for c in chunks], embed_model, cache_dir)
        for n, v in zip(nodes, vectors):
            n.embedding = v   # 이미 임베딩이 있는 노드는 인덱스가 다시 임베딩하지 않는다

    from llama_index.core import StorageContext, VectorStoreIndex
    from llama_index.vector_stores.chroma import ChromaVectorStore
    persist.mkdir(parents=True, exist_ok=True)
    col = common.chroma_client(persist).get_or_create_collection(common.COLLECTION, embedding_function=None)
    storage = StorageContext.from_defaults(vector_store=ChromaVectorStore(chroma_collection=col))
    VectorStoreIndex(nodes, storage_context=storage, embed_model=embed_model)

    manifest = {
        "source": "docs/decisions.md", "commit": commit,
        "config_name": cfg["name"], "config_hash": common.config_hash(cfg), "config": cfg,
        "chunker_version": chunker.CHUNKER_VERSION,
        "embedder": embedder, "embed_model": cfg["embed_model"] if embedder == "openai" else f"mock-{MOCK_DIM}",
        "chunks": len(chunks), "embed_tokens": tokens, "newly_embedded_chunks": new_embeds,
        "packages": common.package_versions(),
        "secret_scan": {k: len(v) for k, v in secrets.items()},
        "elapsed_sec": round(time.monotonic() - t0, 2),
    }
    (persist / common.MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장 완료: 청크 {len(chunks)} · 새 임베딩 {new_embeds} · {manifest['elapsed_sec']}초")
    return 0


if __name__ == "__main__":
    sys.exit(main())
