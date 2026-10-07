"""MCP 서버 — 도구 출력 · 근거 줄 번호 · 범위 · 접두 함정 · 마스킹 보증 · 기동 검사 · stdio 프로토콜(네트워크 0)."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mcp import Client, StdioServerParameters

import chunker
import common
import index
import mcp_server

TOOL = Path(__file__).resolve().parent.parent
CFG_PATH = TOOL / "configs" / "baseline.json"
COMMIT = "e471052"
OTHER_DOC_COMMIT = "6b73fd5"   # docs/decisions.md가 e471052와 다른 커밋

# 마스킹 대상 원값(common.SECRET_PATTERNS 범주) — 도구 출력 어디에도 나오면 안 된다.
SECRETS = ["dev.kim@example.com", "010-1234-5678", "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWX0123",
           "Bearer abcdefghijklmnopqrstuvwxyz0123", "P123456789012", "abc-def.trycloudflare.com"]
LONG = "\n\n".join(f"긴 문단 {i}번. " + "가나다라마바사 " * 60 for i in range(10))   # 문단마다 청크 1개 → 10청크
DOC = f"""# 결정 문서

## 카테고리 6: 장치

### 6.3 마이크 배선
마이크 SCK 배선 메모. 연락처 {SECRETS[0]} · 휴대폰 {SECRETS[1]}
**(a) 하위 소절**
키 {SECRETS[2]} · 헤더 {SECRETS[3]} · 통관 {SECRETS[4]}

#### 배선 메모
6.3 아래 번호 없는 제목.

### 6.30 다른 절
터널 {SECRETS[5]}

## 카테고리 16: 기타

### 16.3 비슷한 번호
16.3 본문.

### 33.6.3 깊은 번호
33.6.3 본문.

### 7.1 긴 절
{LONG}
"""


def build_mock_index(persist, chunks):
    """index.main의 가짜 임베딩 경로와 같은 방식(build_nodes · Chroma · MockEmbedding)."""
    from llama_index.core import StorageContext, VectorStoreIndex
    from llama_index.core.embeddings import MockEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore
    col = common.chroma_client(persist).get_or_create_collection(common.COLLECTION, embedding_function=None)
    VectorStoreIndex(index.build_nodes(chunks), embed_model=MockEmbedding(embed_dim=index.MOCK_DIM),
                     storage_context=StorageContext.from_defaults(vector_store=ChromaVectorStore(chroma_collection=col)))


def text_of(result):
    return result.content[0].text


class ToolTest(unittest.IsolatedAsyncioTestCase):
    """픽스처 문서를 커밋 원문 자리에 넣고 mcp_server.load(기동 검사 포함)로 연 상태에서 도구를 부른다."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cfg = common.load_config(CFG_PATH)
        cls.commit = common.resolve_commit(COMMIT)
        cls.masked = common.mask_secrets(DOC)
        persist = Path(cls.tmp.name)
        build_mock_index(persist, chunker.chunk(cls.masked, cls.commit, cls.cfg))
        (persist / common.MANIFEST).write_text(json.dumps(
            {"commit": cls.commit, "config_name": cls.cfg["name"], "config_hash": common.config_hash(cls.cfg),
             "embedder": "mock", "embed_model": f"mock-{index.MOCK_DIM}"}), encoding="utf-8")
        cls.doc_patch = mock.patch.object(common, "read_doc_at", return_value=DOC)   # 도구가 원문을 다시 읽어도 픽스처
        cls.doc_patch.start()
        cls.loaded = mcp_server.load(COMMIT, CFG_PATH, persist, allow_mock=True)
        cls.chunks = cls.loaded["chunks"]

    @classmethod
    def tearDownClass(cls):
        cls.doc_patch.stop()
        cls.tmp.cleanup()

    def state(self, embedder="mock"):
        return dict(self.loaded, manifest=dict(self.loaded["manifest"], embedder=embedder), index=None)

    async def call(self, name, args, embedder="mock"):
        async with Client(mcp_server.build_server(self.state(embedder))) as c:
            return await c.call_tool(name, args)

    async def ok(self, name, args):
        r = await self.call(name, args)
        self.assertFalse(r.is_error, text_of(r))
        return json.loads(text_of(r))

    async def err(self, name, args, embedder="mock"):
        r = await self.call(name, args, embedder)
        self.assertTrue(r.is_error)
        return text_of(r)

    def assert_ref_matches_source(self, it):
        """근거 표기 줄 번호 = 마스킹 원문의 그 줄(첫 줄 · 끝 줄)."""
        s, e = (int(x) for x in it["ref"].split("@L")[1].split("-L"))
        lines = self.masked.split("\n")
        self.assertEqual(it["ref"][:7], COMMIT)
        self.assertTrue(it["text"].startswith(lines[s - 1]), it["ref"])
        self.assertTrue(it["text"].endswith(lines[e - 1]), it["ref"])

    async def test_list_sections_in_doc_order(self):
        r = await self.ok("list_sections", {"contains": ""})
        self.assertEqual([s["section"] for s in r["sections"]],
                         ["(머리말)", "카테고리 6", "6.3", "6.3(a)", "6.3 › 배선 메모", "6.30", "카테고리 16",
                          "16.3", "33.6.3", "7.1"])
        self.assertEqual((r["total"], r["truncated"], r["commit"], r["config"]), (10, False, COMMIT, "baseline"))
        s73 = r["sections"][-1]
        self.assertEqual(s73["line_end"], len(self.masked.rstrip("\n").split("\n")))

    async def test_list_sections_filter_is_case_insensitive_and_hits_heading(self):
        r = await self.ok("list_sections", {"contains": "sck"})
        self.assertEqual(r["sections"], [])                                  # 본문은 찾지 않는다
        r = await self.ok("list_sections", {"contains": "마이크"})
        self.assertEqual([s["section"] for s in r["sections"]], ["6.3", "6.3(a)", "6.3 › 배선 메모"])

    async def test_list_sections_truncates_at_200(self):
        many = [chunker.Chunk(spans=[], heading_path=[], section=f"s{i}", display="x",
                              meta={"section": f"s{i}", "heading_path": "h", "line_start": i, "line_end": i,
                                    "commit": self.commit}) for i in range(1, 202)]
        st = dict(self.state(), chunks=many)
        async with Client(mcp_server.build_server(st)) as c:
            r = json.loads(text_of(await c.call_tool("list_sections", {"contains": ""})))
        self.assertEqual((r["total"], r["truncated"], len(r["sections"])), (201, True, 200))

    async def test_get_section_exact_and_children_only(self):
        r = await self.ok("get_section", {"section": "6.3", "offset": 0})
        self.assertEqual([c["section"] for c in r["chunks"]], ["6.3", "6.3(a)", "6.3 › 배선 메모"])
        for it in r["chunks"]:
            self.assert_ref_matches_source(it)
        r = await self.ok("get_section", {"section": "6.3(a)", "offset": 0})
        self.assertEqual([c["section"] for c in r["chunks"]], ["6.3(a)"])
        for label in ("6.30", "16.3", "33.6.3"):
            r = await self.ok("get_section", {"section": label, "offset": 0})
            self.assertEqual({c["section"] for c in r["chunks"]}, {label})

    async def test_get_section_unknown_label_is_tool_error(self):
        self.assertIn("list_sections", await self.err("get_section", {"section": "6", "offset": 0}))
        self.assertIn("list_sections", await self.err("get_section", {"section": "6.", "offset": 0}))

    async def test_get_section_pages(self):
        r = await self.ok("get_section", {"section": "7.1", "offset": 0})
        self.assertEqual((r["total"], len(r["chunks"]), r["next_offset"]), (10, 8, 8))
        r2 = await self.ok("get_section", {"section": "7.1", "offset": 8})
        self.assertEqual((len(r2["chunks"]), r2["next_offset"]), (2, None))
        for it in r["chunks"] + r2["chunks"]:
            self.assert_ref_matches_source(it)
        await self.err("get_section", {"section": "7.1", "offset": 10})
        await self.err("get_section", {"section": "7.1", "offset": -1})

    async def test_search_format_and_k_bounds(self):
        for k in (1, 10):
            r = await self.ok("search_decisions", {"query": "마이크 배선", "k": k})
            self.assertEqual(len(r["results"]), k)
            self.assertEqual([x["rank"] for x in r["results"]], list(range(1, k + 1)))
            self.assertEqual((r["embedder"], r["commit"], r["config"]), ("mock", COMMIT, "baseline"))
            self.assertIn("힌트", r["note"])
            for it in r["results"]:
                self.assert_ref_matches_source(it)
        for k in (0, 11):   # 스키마 검증 거부여야 한다(검색 단계에서 우연히 나는 오류가 아니라)
            self.assertIn("validation error", await self.err("search_decisions", {"query": "마이크", "k": k}))

    async def test_missing_args_are_tool_errors(self):
        await self.err("search_decisions", {"query": "마이크"})
        await self.err("list_sections", {})
        await self.err("get_section", {"section": "6.3"})

    async def test_search_without_key_is_error_not_fallback(self):
        with mock.patch.object(common, "openai_key", return_value=None), \
                mock.patch.object(mcp_server, "open_index", side_effect=AssertionError("열면 안 된다")):
            msg = await self.err("search_decisions", {"query": "마이크", "k": 3}, embedder="openai")
        self.assertIn("OPENAI_API_KEY", msg)

    async def test_no_unmasked_value_in_any_output(self):
        self.assertTrue(all(s in DOC for s in SECRETS))                      # 픽스처에 원값이 실제로 있다
        outs = [text_of(await self.call("list_sections", {"contains": ""})),
                text_of(await self.call("search_decisions", {"query": "키", "k": 10}))]
        for label in ("6.3", "6.30", "7.1"):
            outs.append(text_of(await self.call("get_section", {"section": label, "offset": 0})))
        blob = "\n".join(outs)
        for s in SECRETS:
            self.assertNotIn(s, blob)
        self.assertIn("[MASKED:email]", blob)
        self.assertIn("[MASKED:openai_key]", blob)

    async def test_tool_list_and_schemas(self):
        async with Client(mcp_server.build_server(self.state())) as c:
            tools = {t.name: t.input_schema for t in (await c.list_tools()).tools}
        self.assertEqual(set(tools), {"search_decisions", "list_sections", "get_section"})
        k = tools["search_decisions"]["properties"]["k"]
        self.assertEqual((k["minimum"], k["maximum"]), (1, 10))
        self.assertEqual(tools["get_section"]["properties"]["offset"]["minimum"], 0)
        self.assertEqual(sorted(tools["search_decisions"]["required"]), ["k", "query"])
        self.assertEqual(tools["list_sections"]["required"], ["contains"])


def run_index(persist, cfg_path=CFG_PATH, commit=COMMIT):
    with contextlib.redirect_stdout(io.StringIO()):
        index.main(["--commit", commit, "--config", str(cfg_path), "--persist-dir", str(persist),
                    "--embed-cache", str(persist) + "-cache", "--mock-embed"])


def server_args(persist, commit=COMMIT, cfg_path=CFG_PATH, mock_ok=True):
    args = ["-B", str(TOOL / "mcp_server.py"), "--commit", commit, "--config", str(cfg_path), "--persist-dir", str(persist)]
    return args + (["--allow-mock-index"] if mock_ok else [])


def start(args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL,
                          timeout=120)


class StartupAndProtocolTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.persist = Path(cls.tmp.name) / "idx"
        run_index(cls.persist)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def forged(self, name, **manifest_changes):
        """실인덱스를 복사해 manifest만 바꾼다 — 커밋 · 설정 검사는 통과하고 청크 대조만 남게."""
        dst = Path(self.tmp.name) / name
        shutil.copytree(self.persist, dst)
        m = json.loads((dst / common.MANIFEST).read_text(encoding="utf-8"))
        m.update(manifest_changes)
        (dst / common.MANIFEST).write_text(json.dumps(m), encoding="utf-8")
        return dst

    def assert_refused(self, args, needle):
        p = start(args)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "")
        self.assertIn(needle, p.stderr)

    def test_missing_startup_args_refused(self):
        full = server_args(self.persist)
        for flag in ("--commit", "--config", "--persist-dir"):
            i = full.index(flag)
            p = start(full[:i] + full[i + 2:])
            self.assertNotEqual(p.returncode, 0, flag)
            self.assertEqual(p.stdout, "")

    def test_mock_index_needs_flag(self):
        self.assert_refused(server_args(self.persist, mock_ok=False), "--allow-mock-index")

    def test_other_commit_index_refused(self):
        self.assert_refused(server_args(self.persist, commit=OTHER_DOC_COMMIT), "≠ --commit")
        forged = self.forged("other-commit", commit=common.resolve_commit(OTHER_DOC_COMMIT))
        self.assert_refused(server_args(forged, commit=OTHER_DOC_COMMIT), "청크")

    def test_other_config_index_refused(self):
        e1 = TOOL / "configs" / "e1_superseded.json"
        self.assert_refused(server_args(self.persist, cfg_path=e1), "설정 해시")
        forged = self.forged("other-config", config_hash=common.config_hash(common.load_config(e1)))
        self.assert_refused(server_args(forged, cfg_path=e1), "청크")

    def test_index_inside_repo_refused(self):
        self.assert_refused(server_args(TOOL / "tests"), "repo 안")

    async def test_stdio_protocol_and_clean_stdout(self):
        """SDK 클라이언트로 stdio 기동 → 도구 3개 호출. 서버 stdout 전체를 tee로 떠서 JSON-RPC 줄만 있는지 본다."""
        wire = Path(self.tmp.name) / "stdout.jsonl"
        cmd = 'exec "$0" "$@" | tee "$WIRE"'
        params = StdioServerParameters(command="/bin/sh", args=["-c", cmd, sys.executable, *server_args(self.persist)],
                                       env={"WIRE": str(wire), "PYTHONDONTWRITEBYTECODE": "1"})
        async with Client(params) as c:
            names = {t.name for t in (await c.list_tools()).tools}
            ls = await c.call_tool("list_sections", {"contains": "마이크"})
            first = json.loads(text_of(ls))["sections"][0]["section"]
            gs = await c.call_tool("get_section", {"section": first, "offset": 0})
            ss = await c.call_tool("search_decisions", {"query": "마이크", "k": 3})
            bad = await c.call_tool("search_decisions", {"query": "마이크", "k": 0})
        self.assertEqual(names, {"search_decisions", "list_sections", "get_section"})
        self.assertFalse(ls.is_error or gs.is_error or ss.is_error)
        self.assertTrue(bad.is_error)
        self.assertEqual(json.loads(text_of(ss))["embedder"], "mock")
        self.assertEqual(len(json.loads(text_of(ss))["results"]), 3)
        lines = wire.read_text(encoding="utf-8").splitlines()
        self.assertGreaterEqual(len(lines), 6)
        for line in lines:
            self.assertEqual(json.loads(line).get("jsonrpc"), "2.0", line[:80])


if __name__ == "__main__":
    unittest.main()
