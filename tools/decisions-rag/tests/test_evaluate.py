"""평가기 테스트 — 적중 정의 · 지표 · 대조군 자기 검증 · 블라인드 시트 · 설정 가드(네트워크 0)."""
import contextlib
import csv
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import chunker
import common
import evaluate
import query

COMMIT = "e471052"
TOOL = Path(__file__).resolve().parent.parent
CFG_PATH = TOOL / "configs" / "baseline.json"
ECFG_PATH = TOOL / "configs" / "eval_v1.json"


def chunk(display):
    return SimpleNamespace(display=display, embed_text=display, body=display,
                           meta={"commit": "e471052db1ea", "section": "1.1", "heading_path": "h",
                                 "line_start": 1, "line_end": 1, "chunk_hash": "x"})


def row(qid, typ, question, anchors=(), traps=()):
    return {"qid": qid, "type": typ, "question": question, "expected_answer": f"기대 {qid}",
            "gold_anchors": list(anchors), "trap_anchors": list(traps), "gold_match": "any"}


def write_json(d, obj):
    path = Path(d) / "cfg.json"
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return path


class HitDefinitionTest(unittest.TestCase):
    def test_anchor_cut_at_chunk_boundary_is_not_a_hit(self):
        chunks = [chunk("앞부분 정확히 0.70"), chunk("= 발송 뒷부분"), chunk("정확히 0.70 = 발송 전체")]
        self.assertEqual(evaluate.gold_chunks(chunks, ["정확히 0.70 = 발송"]), {2})
        self.assertEqual(evaluate.gold_chunks(chunks[:2], ["정확히 0.70 = 발송"]), set())

    def test_any_of_several_anchors(self):
        chunks = [chunk("가나다"), chunk("라마바"), chunk("사아자")]
        self.assertEqual(evaluate.gold_chunks(chunks, ["라마바", "사아"]), {1, 2})


class MetricTest(unittest.TestCase):
    ECFG = {"hit_k": 3, "mrr_cutoff": 10}

    def run_eval(self, rankings):
        chunks = [chunk(f"문서{i} gold" if i == 0 else f"문서{i}") for i in range(20)]
        rows = [row(f"Q{n}", "fact", f"q{n}", ["gold"]) for n in range(len(rankings))]
        rows.append(row("QX", "not_in_doc", "없는 것"))
        retr = {"bm25": lambda r, k, exclude=frozenset(): rankings[int(r["qid"][1:])][:k]}
        recs = evaluate.evaluate_retrieval(rows, chunks, self.ECFG, retr, ["bm25"])
        return recs, evaluate.summarize_retrieval(recs, ["bm25"])

    def test_hit_and_mrr(self):
        # 정답 청크 0의 순위: 1 · 3 · 4 · 10 · 없음(11위는 잘림)
        rankings = [[0, 1, 2], [5, 6, 0], [5, 6, 7, 0], [1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
                    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0]]
        recs, summary = self.run_eval(rankings)
        self.assertEqual([r["rank"] for r in recs], [1, 3, 4, 10, None])
        self.assertEqual([r["hit"] for r in recs], [True, True, False, False, False])
        total = summary[0]
        self.assertEqual((total["scope"], total["n"], total["hits"]), ("전체", 5, 2))   # not_in_doc은 빠진다
        self.assertAlmostEqual(total["mrr"], (1 + 1 / 3 + 1 / 4 + 1 / 10) / 5)
        self.assertEqual({s["scope"]: s["n"] for s in summary}["reversal"], 0)


class Bm25Test(unittest.TestCase):
    def test_tokenizer(self):
        self.assertEqual(evaluate.tokenize("GPIO_12 핀 표, 마이크"), ["gpio_12", "핀", "표", "마이", "이크"])

    def test_ranks_matching_doc_first_and_drops_zero_scores(self):
        bm = evaluate.BM25(["사과 바나나", "마이크 핀 번호 GPIO", "포도"], 1.5, 0.75)
        self.assertEqual(bm.search("마이크 GPIO", 10), [1])


class GoldRemovedTest(unittest.TestCase):
    """정답 청크를 뺀 인덱스에서 그 문항이 맞으면 평가기 결함."""

    def setUp(self):
        self.chunks = [chunk("마이크 SCK 핀은 GPIO 41"), chunk("카카오 메시지"), chunk("마이크 소음")]
        self.rows = [row("Q1", "fact", "마이크 SCK 핀", ["GPIO 41"])]
        self.ecfg = {"hit_k": 3, "mrr_cutoff": 10, "bm25_k1": 1.5, "bm25_b": 0.75, "random_seed": 1}
        self.retr = {"bm25": evaluate.bm25_retriever(self.chunks, self.ecfg)}

    def test_original_hits_then_removed_is_zero(self):
        recs = evaluate.evaluate_retrieval(self.rows, self.chunks, self.ecfg, self.retr, ["bm25", "gold_removed:bm25"])
        self.assertEqual([(r["condition"], r["rank"]) for r in recs], [("bm25", 1), ("gold_removed:bm25", None)])
        self.assertNotIn(0, recs[1]["ranking"])

    def test_leak_fails_the_run(self):
        leaky = {"bm25": lambda r, k, exclude=frozenset(): [0, 1, 2]}     # 뺄 청크를 무시하는 검색기
        with self.assertRaises(evaluate.EvalError):
            evaluate.evaluate_retrieval(self.rows, self.chunks, self.ecfg, leaky, ["gold_removed:bm25"])


class RandomTest(unittest.TestCase):
    def test_seeded_and_deterministic(self):
        chunks = [chunk(str(i)) for i in range(100)]
        r = row("Q1", "fact", "q")
        a = evaluate.random_retriever(chunks, {"random_seed": 7})
        b = evaluate.random_retriever(chunks, {"random_seed": 7})
        self.assertEqual(a(r, 10), b(r, 10))
        self.assertNotEqual(a(r, 10), evaluate.random_retriever(chunks, {"random_seed": 8})(r, 10))
        self.assertNotIn(3, a(r, 99, frozenset({3})))


def fake_items(n=6):
    return [{"qid": f"Q{i}", "type": "fact", "condition": "bm25" if i % 2 else "random", "model": "gpt-test",
             "question": f"질문{i}", "expected_answer": f"기대{i}", "answer": f"답{i}", "refused": False}
            for i in range(n)]


class SheetTest(unittest.TestCase):
    def test_shuffle_is_deterministic_and_seeded(self):
        a, _ = evaluate.make_sheet(fake_items(), 20261007)
        b, _ = evaluate.make_sheet(fake_items(), 20261007)
        c, _ = evaluate.make_sheet(fake_items(), 1)
        self.assertEqual(a, b)
        self.assertNotEqual([r[1] for r in a], [r[1] for r in c])
        self.assertNotEqual([r[1] for r in a], [f"질문{i}" for i in range(6)])   # 실제로 섞였다

    def test_sheet_is_blind_and_key_is_separate(self):
        items = fake_items()
        sheet, key = evaluate.make_sheet(items, 20261007)
        with tempfile.TemporaryDirectory() as d:
            evaluate.write_sheet(Path(d), sheet, key)
            text = (Path(d) / "sheet.csv").read_text(encoding="utf-8-sig")
            key_rows = [json.loads(x) for x in (Path(d) / "key.jsonl").read_text(encoding="utf-8").splitlines()]
        header = next(csv.reader(io.StringIO(text)))
        self.assertEqual(tuple(header), evaluate.SHEET_COLS)
        for hidden in list(evaluate.CONDITIONS) + ["gpt-test", "Q1", "조건", "모델 이름"]:
            self.assertNotIn(hidden, text)
        by_no = {k["sheet_no"]: k for k in key_rows}
        for s in sheet:                                                 # 열쇠로 시트 행 → 문항 · 조건 복원
            self.assertEqual(by_no[s[0]]["question"], s[1])
        self.assertEqual({(k["qid"], k["condition"]) for k in key_rows}, {(i["qid"], i["condition"]) for i in items})


class VerdictTest(unittest.TestCase):
    def write(self, d, verdicts):
        path = Path(d) / "sheet.csv"
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(evaluate.SHEET_COLS)
            for n, v in enumerate(verdicts, 1):
                w.writerow([n, "질문\n두 줄", "기대", "답", "아니오", v, ""])
        return path

    def test_three_words_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(evaluate.read_sheet(self.write(d, ["정답", " 부분 ", "오답"])), {1: "정답", 2: "부분", 3: "오답"})

    def test_other_values_refused_with_line_numbers(self):
        for bad in ("O", "X", "", "맞음", "정답?"):
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(ValueError) as cm:
                    evaluate.read_sheet(self.write(d, ["정답", bad]))
                self.assertIn("4줄", str(cm.exception), bad)              # 행마다 질문이 두 줄 → 2번 행 = 4줄


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.base = common.load_config(CFG_PATH)
        self.ecfg = json.loads(ECFG_PATH.read_text(encoding="utf-8"))

    def test_registered_config_loads(self):
        self.assertEqual(evaluate.load_eval_config(ECFG_PATH, self.base)["answer_top_k"], self.base["top_k"])

    def test_missing_key_fails(self):
        for k in self.ecfg:
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(ValueError, msg=k):
                    evaluate.load_eval_config(write_json(d, {kk: v for kk, v in self.ecfg.items() if kk != k}), self.base)

    def test_answer_top_k_must_match_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                evaluate.load_eval_config(write_json(d, dict(self.ecfg, answer_top_k=4)), self.base)

    def test_eval_set_sha_mismatch_fails(self):
        rows = evaluate.load_eval_set(self.ecfg)
        self.assertEqual(len(rows), 30)
        with self.assertRaises(ValueError):
            evaluate.load_eval_set(dict(self.ecfg, eval_set_sha256="0" * 64))

    def test_out_dir_guards(self):
        with self.assertRaises(ValueError):
            evaluate.prepare_out_dir(str(TOOL / "out"))
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x").write_text("")
            with self.assertRaises(ValueError):
                evaluate.prepare_out_dir(d)


class AnswerPathTest(unittest.TestCase):
    def test_fake_model_end_to_end(self):
        chunks = [chunk("임계값 8이 양측에서 분리됨"), chunk("8→20 상향 제안"), chunk("배터리 무관")]
        rows = [row("Q1", "reversal", "임계값 8 양측", ["임계값 8이 양측에서 분리됨"], ["8→20 상향"]),
                row("Q2", "not_in_doc", "배터리 며칠"), row("Q3", "fact", "상향 제안", ["8→20 상향 제안"])]
        ecfg = {"answer_top_k": 2, "bm25_k1": 1.5, "bm25_b": 0.75, "random_seed": 1}
        retr = {"bm25": evaluate.bm25_retriever(chunks, ecfg)}
        prompts = []

        def fake(prompt):
            prompts.append(prompt)
            if "임계값 8 양측" in prompt:
                return json.dumps({"answer": "8→20 상향", "evidence": [1], "refused": False})
            if "배터리" in prompt:
                return json.dumps({"answer": "3일", "evidence": [], "refused": False})
            return json.dumps({"answer": "", "evidence": [], "refused": True})

        cfg = common.load_config(CFG_PATH)
        items = evaluate.run_answers(rows, chunks, cfg, ecfg, retr, ["bm25"], fake, common.load_prices(cfg), 1.0)
        self.assertEqual(prompts[0], query.build_prompt(rows[0]["question"], [chunks[0].meta, chunks[1].meta],
                                                        [chunks[0].body, chunks[1].body]))
        q1, q2, q3 = items
        self.assertEqual((q1["evidence_valid"], q1["trap_in_answer"]), (True, True))
        self.assertIsNone(q2["evidence_valid"])
        self.assertTrue(q3["refused"])
        sheet, key = evaluate.make_sheet(items, 3)
        with tempfile.TemporaryDirectory() as d:
            evaluate.write_sheet(Path(d), sheet, key)
            filled = {"Q1": "오답", "Q2": "오답", "Q3": "부분"}
            by_no = {k["sheet_no"]: k["qid"] for k in key}
            path = Path(d) / "sheet.csv"
            with open(path, encoding="utf-8-sig", newline="") as f:
                rows_csv = list(csv.reader(f))
            for r in rows_csv[1:]:
                r[5] = filled[by_no[int(r[0])]]
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerows(rows_csv)
            [s] = evaluate.score(evaluate.read_sheet(path), key)
        self.assertEqual(s["verdicts"]["전체"], {"오답": 2, "부분": 1})
        self.assertEqual((s["hallucination"], s["over_refusal"]), (1, 1))
        self.assertEqual(s["evidence_valid"], [1, 1])
        self.assertEqual((s["reversal_trap_auto"], s["reversal_wrong"]), (1, 1))
        self.assertGreater(s["prompt_tokens"], 0)
        self.assertAlmostEqual(s["cost_usd_est"], (0.40 * s["prompt_tokens"] + 1.60 * s["completion_tokens"]) / 1e6)

    def test_over_cap_stops_before_any_call(self):
        chunks = [chunk("가나다"), chunk("라마바")]
        ecfg = {"answer_top_k": 2, "bm25_k1": 1.5, "bm25_b": 0.75, "random_seed": 1}
        retr = {"bm25": evaluate.bm25_retriever(chunks, ecfg)}
        cfg = common.load_config(CFG_PATH)
        calls = []
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                evaluate.run_answers([row("Q1", "fact", "가나다", ["가나다"])], chunks, cfg, ecfg, retr, ["bm25"],
                                     lambda p: calls.append(p) or '{"refused": true}', common.load_prices(cfg), 0.0)
        self.assertEqual(calls, [])


class PriceTest(unittest.TestCase):
    def setUp(self):
        self.cfg = common.load_config(CFG_PATH)
        self.prices = common.load_prices(self.cfg)

    def test_cost(self):
        m = self.cfg["answer_model"]
        self.assertAlmostEqual(common.usd(self.prices, m, input=1_000_000, output=500_000), 0.40 + 0.80)
        self.assertAlmostEqual(common.usd(self.prices, self.cfg["embed_model"], input=760_000), 0.0152)

    def test_unknown_model_fails_not_zero(self):
        with self.assertRaises(ValueError):
            common.usd(self.prices, "gpt-unknown", input=1000)
        with self.assertRaises(ValueError):
            common.load_prices(dict(self.cfg, answer_model="gpt-4.1-mini"))     # 별칭은 가격표에 없다

    def test_embed_price_mismatch_fails(self):
        with self.assertRaises(ValueError):
            common.load_prices(dict(self.cfg, embed_price_usd_per_1m_tokens=0.03))


class RealEvalSetTest(unittest.TestCase):
    """등록된 평가셋 × e471052 실문서."""

    @classmethod
    def setUpClass(cls):
        cls.base = common.load_config(CFG_PATH)
        cls.ecfg = evaluate.load_eval_config(ECFG_PATH, cls.base)
        cls.rows = evaluate.load_eval_set(cls.ecfg)
        cls.raw = common.read_doc_at(COMMIT)
        cls.chunks = chunker.chunk(common.mask_secrets(cls.raw), COMMIT, cls.base)

    def test_no_contamination(self):
        self.assertEqual(evaluate.contaminated(self.rows, self.raw), [])
        line = next(x for x in self.raw.split("\n") if len(x.strip()) > 40)
        planted = dict(self.rows[0], question=line.strip()[:40])
        self.assertEqual(evaluate.contaminated([planted], self.raw), [self.rows[0]["qid"]])

    def test_every_answerable_question_has_gold_chunk(self):
        n = {r["qid"]: len(evaluate.gold_chunks(self.chunks, r["gold_anchors"]))
             for r in self.rows if r["type"] != evaluate.NO_ANSWER}
        self.assertEqual(len(n), 25)
        self.assertEqual([q for q, c in n.items() if c == 0], [])

    def test_gold_removed_on_questions_bm25_hits(self):
        """정답 청크가 원래 상위 3 안이던 문항에서도 빼면 0 — 우연한 0이 아니다."""
        retr = {"bm25": evaluate.bm25_retriever(self.chunks, self.ecfg)}
        recs = evaluate.evaluate_retrieval(self.rows, self.chunks, self.ecfg, retr, ["bm25", "gold_removed:bm25"])
        hit_before = {r["qid"] for r in recs if r["condition"] == "bm25" and r["hit"]}
        self.assertTrue(hit_before)
        self.assertFalse(any(r["hit"] for r in recs if r["condition"] == "gold_removed:bm25"))

    def test_cli_retrieval_writes_only_to_out_dir(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "run"
            args = ["retrieval", "--commit", COMMIT, "--config", str(CFG_PATH), "--eval-config", str(ECFG_PATH),
                    "--conditions", "random", "--out-dir", str(out)]
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                evaluate.main(args)
            self.assertEqual(sorted(os.listdir(out)), ["retrieval.jsonl", "run.json", "summary.json", "summary.md"])
            self.assertIn("n = 25 중", buf.getvalue())
            with self.assertRaises(SystemExit):                         # 비어 있지 않은 폴더 = 거부
                with contextlib.redirect_stdout(io.StringIO()):
                    evaluate.main(args)

    def test_dense_path_on_mock_index(self):
        import index
        with tempfile.TemporaryDirectory() as d:
            persist = Path(d) / "idx"
            with contextlib.redirect_stdout(io.StringIO()):
                index.main(["--commit", COMMIT, "--config", str(CFG_PATH), "--persist-dir", str(persist),
                            "--embed-cache", str(Path(d) / "cache"), "--mock-embed"])
            dense = evaluate.dense_retriever(self.chunks, self.base, common.resolve_commit(COMMIT), str(persist), True)
            r = next(r for r in self.rows if r["type"] == "fact")
            gold = evaluate.gold_chunks(self.chunks, r["gold_anchors"])
            self.assertEqual(len(dense(r, 10)), 10)
            self.assertFalse(set(dense(r, 10, gold)) & gold)
            with self.assertRaises(ValueError):                         # 답변 평가는 가짜 임베딩을 거부
                evaluate.dense_retriever(self.chunks, self.base, common.resolve_commit(COMMIT), str(persist), False)


if __name__ == "__main__":
    unittest.main()
