"""decisions.md 검색 MCP 서버(stdio · 읽기 전용) — 검색 · 탐색만 하고 답은 만들지 않는다(답은 호출한 LLM 몫).

  python -B mcp_server.py --commit <해시> --config configs/baseline.json --persist-dir <인덱스> [--allow-mock-index]

도구: search_decisions(질의 임베딩 1회 — OpenAI 키 필요) · list_sections · get_section(키 불필요).
stdout은 MCP 프로토콜 전용 — 로그 · 오류는 stderr.
기동 검사(하나라도 어긋나면 기동 거부): 설정 해시 = 인덱스 manifest · manifest 커밋 = --commit ·
인덱스는 repo 밖 · 그 커밋의 마스킹 원문을 청커로 돌린 청크(개수 · 해시) = 인덱스 청크 · 가짜 임베딩 인덱스는 --allow-mock-index일 때만.
"""
import argparse
import json
import sys
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

import chunker
import common
from query import cite, load_manifest, open_index

HINT = "검색 결과는 힌트 — 인용 전에 원문(docs/decisions.md@커밋)과 대조할 것"
LIST_MAX = 200
PAGE = 8


def load(commit, config, persist_dir, allow_mock):
    """기동 검사 → 서버 상태. 어긋나면 ValueError."""
    cfg = common.load_config(config)
    persist = common.check_outside_repo(persist_dir)
    manifest = load_manifest(persist, cfg)
    commit = common.resolve_commit(commit)
    if common.resolve_commit(manifest["commit"]) != commit:
        raise ValueError(f"인덱스 커밋 {manifest['commit'][:7]} ≠ --commit {commit[:7]}")
    if manifest["embedder"] == "mock" and not allow_mock:
        raise ValueError("가짜 임베딩 인덱스다 — 테스트용으로만 --allow-mock-index와 함께 연다")
    chunks = chunker.chunk(common.mask_secrets(common.read_doc_at(commit)), commit, cfg)
    ids = common.chroma_client(persist).get_collection(common.COLLECTION, embedding_function=None).get(include=[])["ids"]
    if sorted(ids) != [f"c{i:05d}-{c.meta['chunk_hash']}" for i, c in enumerate(chunks)]:   # index.build_nodes의 id
        raise ValueError(f"인덱스 청크({len(ids)}개)가 이 커밋 · 설정의 청크({len(chunks)}개)와 다르다")
    return {"commit": commit, "cfg": cfg, "manifest": manifest, "persist": persist, "chunks": chunks, "index": None}


def item(c):
    m = c.meta
    return {"section": m["section"], "heading_path": m["heading_path"], "ref": cite(m)["ref"], "text": c.display}


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1)


def build_server(state):
    chunks, manifest = state["chunks"], state["manifest"]
    head = {"commit": state["commit"][:7], "config": state["cfg"]["name"]}
    srv = MCPServer("decisions-rag", instructions=f"docs/decisions.md 검색 · 탐색(읽기 전용). {HINT}.")

    @srv.tool()
    def search_decisions(query: Annotated[str, Field(min_length=1)],
                         k: Annotated[int, Field(ge=1, le=10, description="결과 수 1~10")]) -> str:
        """decisions.md 청크를 의미 검색(dense · 기준선 설정)해 상위 k개를 돌려준다. 결과는 힌트 — 원문 대조 후 인용.
        문서 용어를 모르면 list_sections로 제목을 보고 그 용어로 다시 검색하거나 get_section으로 펼칠 것."""
        if manifest["embedder"] != "mock" and not common.openai_key():
            # query.open_index는 키가 없으면 프로세스를 끝낸다 — 그 전에 도구 오류로 돌려준다.
            raise ToolError("OPENAI_API_KEY가 없다 — tools/decisions-rag/.env에 넣을 것(다른 검색으로 바꾸지 않는다)")
        if state["index"] is None:
            state["index"] = open_index(state["persist"], manifest)[0]
        results = []
        for rank, h in enumerate(state["index"].as_retriever(similarity_top_k=k).retrieve(query), 1):
            c = chunks[int(h.node.node_id[1:6])]
            if h.node.metadata["chunk_hash"] != c.meta["chunk_hash"]:
                raise ToolError("인덱스 청크가 지금 청크와 다르다")
            results.append({"rank": rank, "score": round(h.score, 4), **item(c)})
        return dumps({**head, "embedder": manifest["embedder"], "results": results, "note": HINT})

    @srv.tool()
    def list_sections(contains: Annotated[str, Field(description="절 라벨 · 제목 경로의 부분 문자열(대소문자 무시). 빈 문자열 = 전부")]) -> str:
        """절 라벨을 문서 순서로(라벨 · 첫 제목 경로 · 줄 범위). 최대 200개 — 넘으면 truncated=true, contains로 좁힐 것."""
        sections = {}
        for c in chunks:
            m = c.meta
            s = sections.setdefault(m["section"], {"section": m["section"], "heading_path": m["heading_path"],
                                                   "line_start": m["line_start"], "line_end": m["line_end"]})
            s["line_start"], s["line_end"] = min(s["line_start"], m["line_start"]), max(s["line_end"], m["line_end"])
        q = contains.lower()
        hits = [s for s in sections.values() if q in s["section"].lower() or q in s["heading_path"].lower()]
        return dumps({**head, "total": len(hits), "truncated": len(hits) > LIST_MAX, "sections": hits[:LIST_MAX]})

    @srv.tool()
    def get_section(section: Annotated[str, Field(min_length=1, description="list_sections의 라벨(예: 6.3)")],
                    offset: Annotated[int, Field(ge=0, description="페이지 시작(첫 호출 0, 이후 next_offset)")]) -> str:
        """라벨이 정확히 같거나 하위 라벨(「6.3(a)」 · 「6.3 › …」)인 청크를 문서 순서로 8개씩 돌려준다."""
        found = [c for c in chunks if c.meta["section"] == section
                 or c.meta["section"].startswith((f"{section}(", f"{section} ›"))]
        if not found:
            raise ToolError(f"없는 절 라벨: {section!r} — list_sections로 찾을 것")
        if offset >= len(found):
            raise ToolError(f"offset {offset} ≥ 전체 {len(found)}")
        nxt = offset + PAGE if offset + PAGE < len(found) else None
        return dumps({**head, "section": section, "total": len(found), "offset": offset, "next_offset": nxt,
                      "chunks": [item(c) for c in found[offset:offset + PAGE]], "note": HINT})

    return srv


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--persist-dir", required=True)
    ap.add_argument("--allow-mock-index", action="store_true")
    a = ap.parse_args(argv)
    try:
        state = load(a.commit, a.config, a.persist_dir, a.allow_mock_index)
    except (ValueError, FileNotFoundError) as e:
        common.fail(str(e))
    print(f"decisions-rag MCP 서버: {state['commit'][:7]} · {state['cfg']['name']} · {state['manifest']['embedder']} · "
          f"청크 {len(state['chunks'])}", file=sys.stderr)
    build_server(state).run("stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
