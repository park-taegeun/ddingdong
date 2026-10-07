"""실문서 불변식(e471052 고정) · 설정 · 경로 가드 · 가짜 임베딩 통합(네트워크 0)."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

import chunker
import common
import index
import query

COMMIT = "e471052"
CFG_PATH = Path(__file__).resolve().parent.parent / "configs" / "baseline.json"


class RealDocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = common.load_config(CFG_PATH)
        cls.text = common.mask_secrets(common.read_doc_at(COMMIT))
        cls.chunks = chunker.chunk(cls.text, COMMIT, cls.cfg)

    def test_every_nonblank_line_is_covered(self):
        self.assertEqual(chunker.uncovered_lines(self.text, self.chunks), [])

    def test_line_ranges_inside_source(self):
        n = len(self.text.split("\n"))
        for c in self.chunks:
            self.assertTrue(1 <= c.meta["line_start"] <= c.meta["line_end"] <= n)

    def test_deterministic(self):
        again = chunker.chunk(self.text, COMMIT, self.cfg)
        self.assertEqual([c.meta["chunk_hash"] for c in self.chunks], [c.meta["chunk_hash"] for c in again])

    def test_over_max_chunks_are_unsplittable(self):
        """최대 초과 청크 = 한 줄의 조각이고, (앞 겹침을 빼면) 문장 하나뿐이어야 한다."""
        lines = self.text.split("\n")
        for c in self.chunks:
            if len(c.display) <= self.cfg["chunk_max_chars"]:
                continue
            self.assertEqual(len(c.spans), 1, c.meta)
            n, s, e = c.spans[0]
            inner = [m.end() for m in chunker.SENTENCE_END_RE.finditer(lines[n - 1], s, e) if m.end() < e]
            self.assertLessEqual(len(inner), 1 if s > 0 else 0, c.meta)

    def line_of(self, prefix, after=1):
        lines = self.text.split("\n")
        return next(n for n in range(after, len(lines) + 1) if lines[n - 1].startswith(prefix))

    def section_at(self, n):
        return [c.meta["section"] for c in self.chunks if c.meta["line_start"] <= n <= c.meta["line_end"]]

    def test_nested_subsection_labels(self):
        s = self.line_of("**(s) M5-c")
        self.assertEqual(self.section_at(s), ["6.3(s)"])
        self.assertEqual(self.section_at(self.line_of("**(a)", s)), ["6.3(s)(a)"])
        self.assertEqual(self.section_at(self.line_of("**(e)", s)), ["6.3(s)(e)"])
        self.assertEqual(self.section_at(self.line_of("**(a)", self.line_of("### 6.3 "))), ["6.3(a)"])
        self.assertEqual(self.section_at(self.line_of("**(f)", self.line_of("**(g)", self.line_of("### 27.8 ")))),
                         ["27.8(f)"])
        self.assertEqual(self.section_at(self.line_of("**(F)", self.line_of("### 9.3 "))), ["9.3(F)"])
        nested = sorted({c.meta["section"] for c in self.chunks if ")(" in c.meta["section"]})
        self.assertEqual(nested, [f"6.3(s)({x})" for x in "abcde"])     # 실문서 중첩 = 6.3(s) 하나

    def test_section_labels_are_unambiguous(self):
        self.assertEqual(self.section_at(self.line_of("## 카테고리 3:")), ["카테고리 3"])
        self.assertEqual(self.section_at(self.line_of("### 결정")), ["카테고리 23 › 결정"])
        self.assertEqual(self.section_at(self.line_of("### 5/12 ")), ["카테고리 15 › 5/12 재검토 항목 (단독 테스트 결과 기반)"])
        paths = {}
        for c in self.chunks:
            paths.setdefault(c.meta["section"], set()).add(c.meta["heading_path"])
        self.assertEqual({k: len(v) for k, v in paths.items() if len(v) > 1}, {})

    def test_personal_info_counts_and_masked(self):
        raw = common.read_doc_at(COMMIT)
        found = common.scan_secrets(raw)
        counts = {k: len(found[k]) for k in ("customs_id", "email", "aws_account_id", "mobile_phone")}
        self.assertEqual(counts, {"customs_id": 1, "email": 3, "aws_account_id": 1, "mobile_phone": 0})
        where = {k: sorted({s for n in found[k] for s in self.section_at(n)}) for k in counts}
        self.assertEqual(where, {"customs_id": ["22.2"], "email": ["30.1", "30.4", "30.7"],
                                 "aws_account_id": ["30.1"], "mobile_phone": []})
        self.assertEqual({k: v for k, v in common.scan_secrets(self.text).items() if v}, {})   # 인덱스 본문엔 0

    def test_no_blocking_secrets(self):
        found = common.scan_secrets(common.read_doc_at(COMMIT))
        self.assertEqual([k for k in common.BLOCKING_SECRETS if found[k]], [])


class SecretTest(unittest.TestCase):
    # 실제 형태의 문자열을 파일에 남기지 않도록 실행 중에 조립한다.
    KEY = "sk-" + "proj-" + "Ab1" * 10
    TOKEN = "Bearer " + "eyJ" + "x9" * 15
    TUNNEL = "https://" + "brave-lion-abc" + ".trycloudflare.com/x"
    MD5 = "d41d8cd98f00b204e9800998ecf8427e"

    def test_scan_counts_and_mask_hides(self):
        text = f"a {self.KEY}\nb {self.TOKEN}\nc {self.TUNNEL}\nmd5 {self.MD5} · Bearer Token 설명"
        found = common.scan_secrets(text)
        self.assertEqual({k: v for k, v in found.items() if v}, {"openai_key": [1], "bearer_token": [2], "quick_tunnel": [3]})
        masked = common.mask_secrets(text)
        for secret in (self.KEY, "x9" * 15, "brave-lion-abc"):
            self.assertNotIn(secret, masked)
        self.assertIn(self.MD5, masked)                                 # 일반 16진 해시는 비밀값이 아니다
        self.assertIn("[MASKED:quick_tunnel]", masked)


class PersonalInfoTest(unittest.TestCase):
    # 실값 금지 — 형태만 같은 가짜 값을 실행 중에 조립한다.
    CUSTOMS = "P" + "1234567890" + "12"
    MAIL = "someone" + "@" + "example.com"
    ACCOUNT = "Account ID `" + "123456789012" + "`"
    PHONE = "010" + "-1234-" + "5678"
    NOT_MAIL = ["platformio/espressif32@7.0.0", "framework@3.20017.241212", "pkg@1.2.3.tgz",
                "lib@2.0.0-beta.zip", "`@app.route`", "medium.com/@name/post", "@ 기호만", "x@9,9kHz"]

    def test_each_kind_counted_and_masked(self):
        text = f"a {self.CUSTOMS}\nb {self.MAIL}\nc {self.ACCOUNT}\nd {self.PHONE}"
        found = common.scan_secrets(text)
        self.assertEqual({k: v for k, v in found.items() if v},
                         {"customs_id": [1], "email": [2], "aws_account_id": [3], "mobile_phone": [4]})
        masked = common.mask_secrets(text)
        for value in (self.CUSTOMS, self.MAIL, "123456789012", self.PHONE):
            self.assertNotIn(value, masked)
        self.assertIn("Account ID `[MASKED:aws_account_id]`", masked)
        self.assertEqual(common.BLOCKING_SECRETS, ("openai_key", "bearer_token"))   # 개인정보는 차단 대상 아님

    def test_version_strings_are_not_mail(self):
        for s in self.NOT_MAIL:
            self.assertEqual(common.SECRET_PATTERNS["email"].findall(s), [], s)
            self.assertEqual(common.mask_secrets(s), s, s)


class ConfigTest(unittest.TestCase):
    def test_missing_key_fails_including_mark_superseded(self):
        cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
        for k in cfg:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump({kk: v for kk, v in cfg.items() if kk != k}, f)
            try:
                with self.assertRaises(ValueError, msg=k):
                    common.load_config(f.name)
            finally:
                os.unlink(f.name)

    def test_baseline_is_e1_off(self):
        self.assertIs(common.load_config(CFG_PATH)["mark_superseded"], False)


class PathGuardTest(unittest.TestCase):
    def test_repo_paths_refused_even_via_symlink(self):
        root = common.repo_root()
        with self.assertRaises(ValueError):
            common.check_outside_repo(str(root / "tools" / "x"))
        with tempfile.TemporaryDirectory() as d:
            link = Path(d) / "link"
            link.symlink_to(root)
            with self.assertRaises(ValueError):
                common.check_outside_repo(str(link / "idx"))
            self.assertEqual(common.check_outside_repo(str(Path(d) / "idx")), Path(os.path.realpath(d)) / "idx")


class MockIndexTest(unittest.TestCase):
    def test_index_then_query(self):
        with tempfile.TemporaryDirectory() as d:
            persist, cache = Path(d) / "idx", Path(d) / "cache"
            with contextlib.redirect_stdout(io.StringIO()):
                index.main(["--commit", COMMIT, "--config", str(CFG_PATH), "--persist-dir", str(persist),
                            "--embed-cache", str(cache), "--mock-embed"])
            m = json.loads((persist / common.MANIFEST).read_text(encoding="utf-8"))
            self.assertEqual(m["commit"][:7], COMMIT)
            self.assertEqual(m["config_hash"], common.config_hash(common.load_config(CFG_PATH)))
            self.assertEqual(m["embedder"], "mock")
            self.assertFalse(cache.exists())                            # 가짜 임베딩은 캐시를 쓰지 않는다
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                query.main(["--persist-dir", str(persist), "--config", str(CFG_PATH), "-k", "5", "핀 표"])
            self.assertEqual(sum(line.startswith("[") for line in out.getvalue().splitlines()), 5)
            with self.assertRaises(SystemExit):                         # 덮어쓰기 금지
                with contextlib.redirect_stdout(io.StringIO()):
                    index.main(["--commit", COMMIT, "--config", str(CFG_PATH), "--persist-dir", str(persist),
                                "--embed-cache", str(cache), "--mock-embed"])


if __name__ == "__main__":
    unittest.main()
