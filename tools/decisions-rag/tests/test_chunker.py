"""청커 단위 테스트 — 작은 가짜 마크다운(네트워크 · git 0)."""
import unittest

import chunker

CFG = {"chunk_target_chars": 800, "chunk_max_chars": 800, "overlap_chars": 100, "mark_superseded": False}

DOC = """# 문서 제목

## 카테고리 6: 서버

### 6.2 수신 경로

머리 문단.

**(f) 소절 제목 (근거유형 = 실측)**

- 최상위 항목 하나
  - 중첩 줄 A
  - 중첩 줄 B
- 최상위 항목 둘

```
## 코드 안 제목 — 제목 아님
| 코드 안 파이프 | 표 아님 |
```

코드 뒤 문단은 여전히 6.2(f)에 속한다.

#### 6.2.1 하위 절

하위 절 본문.

### 5/12 재검토 항목

날짜 제목 아래 본문.

### 번호 없는 제목

마지막 단위는 제목이 아니라 문단이다."""


def by_text(chunks, needle):
    hits = [c for c in chunks if needle in c.display]
    assert len(hits) == 1, (needle, len(hits))
    return hits[0]


class HeadingTest(unittest.TestCase):
    def setUp(self):
        self.chunks = chunker.chunk(DOC, "abc1234", CFG)

    def test_paths_and_sections(self):
        c = by_text(self.chunks, "최상위 항목 하나")
        self.assertEqual(c.heading_path, ["카테고리 6: 서버", "6.2 수신 경로", "(f) 소절 제목 (근거유형 = 실측)"])
        self.assertEqual(c.meta["section"], "6.2(f)")
        self.assertEqual(by_text(self.chunks, "머리 문단").meta["section"], "6.2")
        self.assertEqual(by_text(self.chunks, "하위 절 본문").meta["section"], "6.2.1")
        self.assertEqual(by_text(self.chunks, "## 카테고리 6").meta["section"], "6")

    def test_unnumbered_and_date_headings_use_title(self):
        self.assertEqual(by_text(self.chunks, "날짜 제목 아래").meta["section"], "5/12 재검토 항목")
        self.assertEqual(by_text(self.chunks, "마지막 단위").meta["section"], "번호 없는 제목")

    def test_code_block_hash_and_pipe_are_not_structure(self):
        c = by_text(self.chunks, "코드 뒤 문단")
        self.assertEqual(c.meta["section"], "6.2(f)")
        self.assertTrue(all("코드 안 제목" not in h for ch in self.chunks for h in ch.heading_path))

    def test_embed_text_is_path_line_plus_body(self):
        c = by_text(self.chunks, "하위 절 본문")
        self.assertEqual(c.embed_text, "카테고리 6: 서버 > 6.2 수신 경로 > 6.2.1 하위 절\n" + c.body)
        self.assertNotIn("abc1234", c.embed_text)

    def test_coverage_last_unit_is_paragraph(self):
        self.assertEqual(chunker.uncovered_lines(DOC, self.chunks), [])
        self.assertIn("마지막 단위는 제목이 아니라 문단이다.", self.chunks[-1].display)

    def test_display_is_exact_source_lines(self):
        lines = DOC.split("\n")
        for c in self.chunks:
            self.assertEqual(c.display, "\n".join(lines[n - 1][s:e] for n, s, e in c.spans))


class SplitTest(unittest.TestCase):
    def test_list_item_with_nested_lines_is_one_unit(self):
        doc = "## A\n\n- 위\n  - 아래1\n  - 아래2\n- 다음"
        c = chunker.chunk(doc, "x", CFG)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].display, "## A\n- 위\n  - 아래1\n  - 아래2\n- 다음")

    def test_oversized_list_splits_at_nested_boundary_without_overlap(self):
        nested = ["  - " + ("중" * 300) + str(i) for i in range(3)]
        doc = "## A\n\n- 위 항목\n" + "\n".join(nested)
        cs = chunker.chunk(doc, "x", CFG)
        self.assertTrue(all(len(c.display) <= 800 for c in cs))
        starts = [c.spans[0] for c in cs if c.spans[0][0] >= 4]
        self.assertTrue(all(s == 0 for _, s, _ in starts))           # 중첩 항목 경계 = 줄 머리
        spans = [sp for c in cs for sp in c.spans]
        self.assertEqual(len(spans), len(set(spans)))                 # 겹침 없음
        self.assertEqual(chunker.uncovered_lines(doc, cs), [])

    def test_long_single_line_splits_at_sentences_with_overlap(self):
        line = " ".join(f"문장{i}은 이렇게 끝난다{'가' * 40}." for i in range(40))
        doc = "## A\n\n" + line
        cs = [c for c in chunker.chunk(doc, "x", CFG) if c.spans[0][0] == 3]
        self.assertGreater(len(cs), 1)
        for a, b in zip(cs, cs[1:]):
            (_, s1, e1), (_, s2, _) = a.spans[-1], b.spans[0]
            self.assertLess(s2, e1)                                    # 겹침 존재
            self.assertLessEqual(e1 - s2, 100)                         # 약 100자 이내
            self.assertTrue(line[s1:e1].endswith("."))                # 문장 경계에서 자름
        self.assertTrue(all(len(c.display) <= 800 + 100 for c in cs))
        self.assertEqual(chunker.uncovered_lines(doc, chunker.chunk(doc, "x", CFG)), [])

    def test_oversized_table_repeats_header(self):
        rows = [f"| r{i} | {'값' * 60} |" for i in range(30)]
        doc = "## T\n\n| 열1 | 열2 |\n|---|---|\n" + "\n".join(rows)
        cs = [c for c in chunker.chunk(doc, "x", CFG) if "| r" in c.display]
        self.assertGreater(len(cs), 1)
        for c in cs:
            self.assertIn("| 열1 | 열2 |\n|---|---|\n| r", c.display)       # 조각마다 머리 행 반복
            self.assertLessEqual(len(c.display), 800)
        self.assertEqual(chunker.uncovered_lines(doc, chunker.chunk(doc, "x", CFG)), [])

    def test_size_ignores_heading_path_line(self):
        doc = "## " + "제" * 500 + "\n\n### B\n\n" + "가" * 390 + "\n\n" + "나" * 390
        c = by_text(chunker.chunk(doc, "x", CFG), "가" * 390)
        self.assertIn("나" * 390, c.display)                            # 본문 ≤ 800이면 한 청크
        self.assertLessEqual(len(c.body), 800)
        self.assertGreater(len(c.embed_text), 800)                      # 앞의 제목 경로 줄은 세지 않았다


class SupersededTest(unittest.TestCase):
    DOC = "## A\n\n결정 ~~옛 값 3초~~ → 새 값 5초."

    def test_switch_changes_body_not_display(self):
        off = chunker.chunk(self.DOC, "x", dict(CFG, mark_superseded=False))[0]
        on = chunker.chunk(self.DOC, "x", dict(CFG, mark_superseded=True))[0]
        self.assertEqual(off.display, on.display)
        self.assertIn("~~옛 값 3초~~", on.display)
        self.assertEqual(off.body, off.display)
        self.assertIn("[폐기] 옛 값 3초 [/폐기]", on.body)
        self.assertNotIn("~~", on.body)
        self.assertIn("[폐기]", on.embed_text)
        self.assertNotEqual(off.meta["chunk_hash"], on.meta["chunk_hash"])
        self.assertTrue(on.meta["has_strikethrough"])


class ConfigTest(unittest.TestCase):
    def test_each_missing_key_fails(self):
        for k in CFG:
            cfg = {kk: v for kk, v in CFG.items() if kk != k}
            with self.assertRaises(ValueError, msg=k):
                chunker.chunk("## A\n\n본문", "x", cfg)


class MetaTest(unittest.TestCase):
    def test_pr_and_dates(self):
        doc = "## A\n\nPR #68 `704dded`, (#59 하네스) 2026-09-21 · 2026-09-21 · md5 3f2a#1"
        m = chunker.chunk(doc, "x", CFG)[0].meta
        self.assertEqual(m["pr_numbers"], "59,68")
        self.assertEqual(m["dates"], "2026-09-21")
        self.assertEqual((m["line_start"], m["line_end"]), (1, 3))


if __name__ == "__main__":
    unittest.main()
