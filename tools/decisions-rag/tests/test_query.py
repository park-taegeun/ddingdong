"""질의 · 답변 경로 테스트 — 모델 호출 없음(네트워크 0)."""
import json
import tempfile
import unittest
from pathlib import Path

import common
import query

CFG_PATH = Path(__file__).resolve().parent.parent / "configs" / "baseline.json"


def meta(i):
    return {"commit": "e471052db1ea", "section": f"33.{i}", "heading_path": f"카테고리 33 > 33.{i}",
            "line_start": 10 * i, "line_end": 10 * i + 5}


METAS = [meta(i) for i in (1, 2, 3)]


class ParseAnswerTest(unittest.TestCase):
    def test_citations_come_from_metadata(self):
        raw = json.dumps({"answer": "5초", "evidence": [2], "refused": False,
                          # 모델이 근거 문자열을 지어내도 쓰지 않는다
                          "citations": [{"ref": "deadbee@L1-L2", "section": "99.9"}]})
        r = query.parse_answer(raw, METAS)
        self.assertEqual(r["answer"], "5초")
        self.assertEqual(r["citations"], [{"chunk": 2, "section": "33.2", "heading_path": "카테고리 33 > 33.2",
                                           "ref": "e471052@L20-L25"}])
        self.assertNotIn("deadbee", json.dumps(r))

    def test_bad_evidence_numbers_are_dropped(self):
        raw = json.dumps({"answer": "x", "evidence": [0, 4, "1", True, 1, 1, 3], "refused": False})
        r = query.parse_answer(raw, METAS)
        self.assertEqual([c["chunk"] for c in r["citations"]], [1, 3])
        self.assertEqual(r["dropped_evidence"], [0, 4, "1", True])

    def test_refusal_blanks_answer(self):
        r = query.parse_answer(json.dumps({"answer": "추측", "evidence": [], "refused": True}), METAS)
        self.assertTrue(r["refused"])
        self.assertEqual(r["answer"], "")

    def test_non_json_fails(self):
        for raw in ("그냥 문장", "[1, 2]"):
            with self.assertRaises(ValueError):
                query.parse_answer(raw, METAS)

    def test_prompt_numbers_chunks_and_states_rule(self):
        p = query.build_prompt("질문?", METAS, ["본문1", "본문2", "본문3"])
        self.assertIn("없는 내용은 답하지 말고 거절", p)
        self.assertIn("[3] (카테고리 33 > 33.3)\n본문3", p)
        self.assertNotIn("e471052", p)                                 # 근거 표기는 프롬프트에도 맡기지 않는다


class ManifestTest(unittest.TestCase):
    def test_config_hash_mismatch_is_refused(self):
        cfg = common.load_config(CFG_PATH)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / common.MANIFEST).write_text(json.dumps({"config_name": "baseline",
                                                         "config_hash": common.config_hash(cfg)}))
            query.load_manifest(d, cfg)                                 # 같은 설정 = 통과
            with self.assertRaises(ValueError):
                query.load_manifest(d, dict(cfg, mark_superseded=True))


class LlmGuardTest(unittest.TestCase):
    def test_reasoning_model_is_refused(self):
        cfg = common.load_config(CFG_PATH)
        with self.assertRaises(ValueError):
            query.make_llm(dict(cfg, answer_model="gpt-5.4-mini"), "sk-test-not-a-real-key")


if __name__ == "__main__":
    unittest.main()
