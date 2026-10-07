"""평가기 테스트 — 적중 정의 · 지표 · 대조군 자기 검증 · 블라인드 시트 · 설정 가드(네트워크 0)."""
import contextlib
import csv
import io
import json
import os
import tempfile
import unittest
from collections import Counter
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


class HybridTest(unittest.TestCase):
    def test_rrf_uses_reciprocal_rank_with_k(self):
        # 순위가 엇갈린 예: 20은 양쪽 3위, 10 · 40은 한쪽 1위. k = 60이면 20이 앞, k를 무시하면 10 · 40이 앞
        a, b = [10, 30, 20], [40, 50, 20]
        self.assertEqual(evaluate.rrf([a, b], 60), [20, 10, 40, 30, 50])
        self.assertEqual(evaluate.rrf([a, b], 0), [10, 40, 20, 30, 50])

    def test_hybrid_reads_rrf_k_from_eval_config(self):
        dense = lambda r, k, exclude=frozenset(): [10, 30, 20][:k]
        bm25 = lambda r, k, exclude=frozenset(): [40, 50, 20][:k]
        r = row("Q1", "fact", "q")
        self.assertEqual(evaluate.hybrid_retriever(dense, bm25, {"rrf_k": 60})(r, 2), [20, 10])
        self.assertEqual(evaluate.hybrid_retriever(dense, bm25, {"rrf_k": 0})(r, 2), [10, 40])

    def test_gold_removed_hybrid_removes_from_both_lists(self):
        chunks = [chunk("마이크 SCK 핀은 GPIO 41"), chunk("카카오 메시지"), chunk("마이크 소음")]
        rows = [row("Q1", "fact", "마이크 SCK 핀", ["GPIO 41"])]
        ecfg = {"hit_k": 3, "mrr_cutoff": 10, "bm25_k1": 1.5, "bm25_b": 0.75, "rrf_k": 60}
        bm25 = evaluate.bm25_retriever(chunks, ecfg)

        def dense(r, k, exclude=frozenset()):                          # 정답 청크를 맨 위로 내는 가짜 dense
            return [i for i in (0, 2, 1) if i not in exclude][:k]
        retr = {"hybrid": evaluate.hybrid_retriever(dense, bm25, ecfg)}
        recs = evaluate.evaluate_retrieval(rows, chunks, ecfg, retr, ["hybrid", "gold_removed:hybrid"])
        self.assertEqual([r["rank"] for r in recs], [1, None])
        self.assertNotIn(0, recs[1]["ranking"])


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


class LocalAnswerTest(unittest.TestCase):
    def setUp(self):
        self.chunks = [chunk("가나다"), chunk("라마바")]
        self.ecfg = {"answer_top_k": 2, "bm25_k1": 1.5, "bm25_b": 0.75, "random_seed": 1}
        self.retr = {"bm25": evaluate.bm25_retriever(self.chunks, self.ecfg)}
        self.cfg = common.load_config(CFG_PATH)
        self.rows = [row(f"Q{n}", "fact", "가나다", ["가나다"]) for n in range(3)]

    def run_local(self, complete, rows=None):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return evaluate.run_answers(rows or self.rows, self.chunks, self.cfg, self.ecfg, self.retr, ["bm25"], complete,
                                        common.load_prices(self.cfg), 0.0, "llama-test@abc")

    def test_format_error_is_not_refusal_and_keeps_raw_text(self):
        outs = iter([("그냥 문장", 50, 3), (json.dumps({"answer": "", "evidence": [], "refused": True}), 50, 9),
                     (json.dumps({"answer": "가나다", "evidence": [1], "refused": False}), 50, 9)])
        items = self.run_local(lambda p: next(outs))                   # 비용 상한 0이어도 로컬은 비용 0이라 돈다
        bad, refused, ok = items
        self.assertEqual((bad["format_error"], bad["refused"], bad["answer"], bad["evidence_valid"]),
                         (True, False, "그냥 문장", None))
        self.assertEqual((refused["format_error"], refused["refused"]), (False, True))
        self.assertEqual((ok["format_error"], ok["evidence_valid"], ok["model"], ok["cost_usd_est"]),
                         (False, True, "llama-test@abc", 0.0))
        self.assertEqual((ok["prompt_tokens"], ok["completion_tokens"]), (50, 9))   # 서버가 센 값

    def test_call_failure_is_recorded_then_stops_at_limit(self):
        def broken(p):
            raise query.LocalCallError("URLError")
        [item] = self.run_local(broken, self.rows[:1])
        self.assertEqual((item["call_failed"], item["format_error"], item["refused"]), (True, False, False))
        many = [row(f"Q{n}", "fact", "가나다", ["가나다"]) for n in range(evaluate.MAX_CALL_FAILURES)]
        with self.assertRaises(evaluate.EvalError):
            self.run_local(broken, many)


class MergeTest(unittest.TestCase):
    def test_merged_sheet_is_blind_and_runs_stay_apart(self):
        runs = [("e1_superseded", "dense", "gpt-4.1-mini-2025-04-14"), ("baseline", "hybrid", "gpt-4.1-mini-2025-04-14"),
                ("baseline", "dense", "llama3.1:8b@46e0c10c039e"), ("baseline", "dense", "exaone3.5:7.8b@c7c4e3d1ca22")]
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for n, (cfg, cond, model) in enumerate(runs):
                items = [dict(it, config=cfg, condition=cond, model=model) for it in fake_items(3)]
                sub = Path(d) / str(n)
                sub.mkdir()
                evaluate.write_sheet(sub, *evaluate.make_sheet(items, 1))
                paths.append(str(sub / "key.jsonl"))
            items = evaluate.merge_keys(paths)
            self.assertEqual(len(items), 12)
            sheet, key = evaluate.make_sheet(items, 20261007)
            out = Path(d) / "merged"
            out.mkdir()
            evaluate.write_sheet(out, sheet, key)
            text = (out / "sheet.csv").read_text(encoding="utf-8-sig")
            with self.assertRaises(ValueError):                          # 같은 실행을 두 번 넣으면 거부
                evaluate.merge_keys(paths[:1] * 2)
        self.assertEqual(tuple(next(csv.reader(io.StringIO(text)))), evaluate.SHEET_COLS)
        for hidden in ("llama", "exaone", "gpt-4.1", "46e0c10c039e", "e1_superseded", "baseline", "hybrid", "dense", "Q1"):
            self.assertNotIn(hidden, text)
        self.assertEqual(len({evaluate.run_label(k) for k in key}), 4)  # 같은 dense도 설정 · 모델로 갈린다
        verdicts = {k["sheet_no"]: "정답" for k in key}
        self.assertEqual([s["n"] for s in evaluate.score(verdicts, [dict(k, retrieval_sec=0, answer_sec=0, prompt_tokens=0,
                          completion_tokens=0, cost_usd_est=0, evidence_valid=None, trap_in_answer=None) for k in key])],
                         [3, 3, 3, 3])


def key_item(no, qid, typ, answer="답", refused=False, call_failed=False, format_error=False, answer_sec=1.0):
    return {"sheet_no": no, "qid": qid, "type": typ, "condition": "dense", "model": "m", "answer": answer, "refused": refused,
            "call_failed": call_failed, "format_error": format_error, "evidence_valid": None, "trap_in_answer": None,
            "retrieval_sec": 0.1, "answer_sec": answer_sec, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd_est": 0.0}


class ScoreFieldsTest(unittest.TestCase):
    def test_call_failure_is_wrong_but_not_hallucination(self):
        # not_in_doc · 호출 실패 · 오답 행이 없으면 환각 정의 검사가 늘 통과한다 — 반드시 넣는다
        key = [key_item(1, "Q1", "not_in_doc", "", call_failed=True, answer_sec=100.0),
               key_item(2, "Q2", "not_in_doc", "지어낸 답", answer_sec=1.0),
               key_item(3, "Q3", "fact", "형식 밖 원문", format_error=True, answer_sec=2.0)]
        [s] = evaluate.score({1: "오답", 2: "오답", 3: "부분"}, key)
        self.assertEqual(s["verdicts"]["not_in_doc"], {"오답": 2})          # 채점은 그대로 오답
        self.assertEqual(s["hallucination"], 1)
        self.assertEqual((s["call_failed"], s["format_error"], s["over_refusal"]), (1, 1, 0))
        self.assertEqual(s["answer_sec_median"], 2.0)                      # 적재 시간이 낀 첫 호출이 평균만 끈다
        self.assertAlmostEqual(s["answer_sec_mean"], 103 / 3)
        self.assertEqual(s["correct_qids"], [])

    def test_old_keys_without_new_fields_count_zero(self):
        old = [{k: v for k, v in key_item(1, "Q1", "fact").items() if k not in ("call_failed", "format_error")}]
        [s] = evaluate.score({1: "정답"}, old)
        self.assertEqual((s["call_failed"], s["format_error"], s["correct_qids"]), (0, 0, ["Q1"]))


def score_summary(by_type, qids=()):
    """by_type = {유형: {판정: 개수}} → score 결과 한 실행(전체 = 합)."""
    total = Counter()
    for c in by_type.values():
        total.update(c)
    return {"condition": "run", "n": sum(total.values()), "verdicts": {"전체": dict(total), **by_type},
            "correct_qids": list(qids)}


def ret_summary(hits, n=None):
    n = n or {"fact": 10, "identifier": 5, "reversal": 5, "false_premise": 5}
    return [{"condition": "c", "scope": "전체", "n": sum(n.values()), "hits": sum(hits.values())}] + \
        [{"condition": "c", "scope": t, "n": n[t], "hits": hits[t]} for t in n]


BASE_TYPES = {"fact": {"정답": 3, "오답": 7}, "identifier": {"정답": 1, "오답": 4}, "reversal": {"정답": 2, "오답": 3},
              "not_in_doc": {"정답": 4, "오답": 1}, "false_premise": {"오답": 5}}
BASE_HITS = {"fact": 3, "identifier": 1, "reversal": 2, "false_premise": 0}


def with_types(**changes):
    return {t: changes.get(t, c) for t, c in BASE_TYPES.items()}


class AdoptTest(unittest.TestCase):
    def judge(self, exp, exp_types, exp_hits=BASE_HITS, base_qids=(), exp_qids=()):
        r = evaluate.adopt(exp, score_summary(BASE_TYPES, base_qids), score_summary(exp_types, exp_qids),
                           ret_summary(BASE_HITS), ret_summary(exp_hits))
        return r, {c["clause"]: c for c in r["clauses"]}

    def test_e1_adopted_when_reversal_plus_one(self):
        r, c = self.judge("E1", with_types(reversal={"정답": 3, "오답": 2}))
        self.assertTrue(r["adopted"])
        self.assertEqual([(x["base"], x["exp"], x["diff"]) for x in r["clauses"]], [(2, 3, 1), (8, 8, 0), (6, 6, 0)])
        self.assertEqual(c["나머지 25문항 정답 수 감소 0"]["n"], 25)

    def test_e1_reversal_unchanged_is_not_adopted(self):
        # 차이가 정확히 0 — 「+1 이상」을 「≥ 0」으로 잘못 두면 통과해 버린다
        r, c = self.judge("E1", BASE_TYPES)
        self.assertEqual(c["reversal 정답 수 +1 이상"]["diff"], 0)
        self.assertFalse(c["reversal 정답 수 +1 이상"]["pass"])
        self.assertFalse(r["adopted"])

    def test_partial_is_not_correct(self):
        # reversal 정답 2 그대로 + 오답 1 → 부분 1. 부분을 정답으로 세면 +1이 돼 채택돼 버린다
        r, c = self.judge("E1", with_types(reversal={"정답": 2, "부분": 1, "오답": 2}))
        self.assertEqual(c["reversal 정답 수 +1 이상"]["exp"], 2)
        self.assertFalse(r["adopted"])
        r, c = self.judge("E2", with_types(fact={"정답": 2, "부분": 2, "오답": 6}),
                          dict(BASE_HITS, fact=5, identifier=2))
        self.assertEqual((c["정답 수 감소 0"]["diff"], c["정답 수 감소 0"]["pass"]), (-1, False))

    def test_e2_type_clause_uses_each_type(self):
        # 전체는 +3 늘었는데 reversal만 2 줄었다 → 미채택. fact −1은 경계 안(통과)
        hits = dict(BASE_HITS, reversal=0, fact=2, identifier=5, false_premise=2)
        r, c = self.judge("E2", BASE_TYPES, hits)
        self.assertEqual((c["전체 Hit@3 +2문항 이상"]["diff"], c["전체 Hit@3 +2문항 이상"]["pass"]), (3, True))
        self.assertEqual((c["reversal Hit@3 2문항 이상 감소 없음"]["diff"], c["reversal Hit@3 2문항 이상 감소 없음"]["pass"]),
                         (-2, False))
        self.assertTrue(c["fact Hit@3 2문항 이상 감소 없음"]["pass"])
        self.assertFalse(r["adopted"])
        r, _ = self.judge("E2", BASE_TYPES, dict(hits, reversal=1))
        self.assertTrue(r["adopted"])

    def test_flips_are_reference_only(self):
        # 개수는 같고 문항만 바뀌었다 — 뒤집힘이 있어도 판정은 개수로
        r, _ = self.judge("E1", with_types(reversal={"정답": 3, "오답": 2}), base_qids=["Q01", "Q16"], exp_qids=["Q16", "Q17"])
        self.assertTrue(r["adopted"])
        self.assertEqual((r["ref_correct_lost"], r["ref_correct_gained"]), (["Q01"], ["Q17"]))

    def test_cli_requires_names_and_writes_out_dir(self):
        with tempfile.TemporaryDirectory() as d:
            paths = {}
            for name, obj in (("bs", [dict(score_summary(BASE_TYPES), condition="dense")]),
                              ("es", [dict(score_summary(with_types(reversal={"정답": 3, "오답": 2})), condition="e1")]),
                              ("br", ret_summary(BASE_HITS)), ("er", ret_summary(BASE_HITS))):
                paths[name] = Path(d) / f"{name}.json"
                paths[name].write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            args = ["adopt", "--experiment", "E1", "--base-score", str(paths["bs"]), "--base-run", "dense",
                    "--base-retrieval", str(paths["br"]), "--base-cond", "c", "--exp-score", str(paths["es"]),
                    "--exp-run", "e1", "--exp-retrieval", str(paths["er"]), "--exp-cond", "c", "--out-dir", str(Path(d) / "out")]
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                evaluate.main(args)
            self.assertIn("E1 — 채택", buf.getvalue())
            self.assertTrue(json.loads((Path(d) / "out" / "summary.json").read_text(encoding="utf-8"))["adopted"])
            bad = list(args)
            bad[bad.index("--exp-run") + 1] = "없는 실행"
            bad[-1] = str(Path(d) / "out2")
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                evaluate.main(bad)
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                evaluate.main(args[:2] + args[4:])                      # 인자 하나라도 빠지면 거부(기본값 없음)


class ConsistencyTest(unittest.TestCase):
    def check(self, a, b, va, vb):
        return evaluate.consistency([("A", {1: va}, [dict(a, sheet_no=1)]), ("B", {1: vb}, [dict(b, sheet_no=1)])])

    def test_same_answer_same_verdict_is_a_consistent_pair(self):
        r = self.check(key_item(1, "Q1", "fact", "GPIO 41"), key_item(1, "Q1", "fact", " GPIO 41\n"), "정답", "정답")
        self.assertEqual((r["pairs"], r["empty_pairs"], r["mismatches"]), (1, 0, []))

    def test_same_answer_different_verdict_is_reported(self):
        r = self.check(key_item(1, "Q1", "fact", "GPIO 41"), key_item(1, "Q1", "fact", "GPIO 41 "), "정답", "부분")
        self.assertEqual(r["mismatches"], [[{"qid": "Q1", "sheet": "A", "sheet_no": 1, "verdict": "정답"},
                                            {"qid": "Q1", "sheet": "B", "sheet_no": 1, "verdict": "부분"}]])

    def test_same_qid_different_answer_is_not_a_pair(self):
        # qid만으로 짝지으면 다른 답의 다른 판정을 불일치로 잘못 센다
        r = self.check(key_item(1, "Q1", "fact", "GPIO 41"), key_item(1, "Q1", "fact", "GPIO 42"), "정답", "오답")
        self.assertEqual((r["pairs"], r["mismatches"]), (0, []))

    def test_empty_call_failure_is_not_paired_with_empty_answer(self):
        # 빈 거절(정답) ↔ 빈 호출 실패(오답)는 거절 여부부터 달라 호출 실패 칸이 없어도 갈린다.
        # 호출 실패 칸을 지키려면 거절 여부까지 같은 예 — 거절 없이 빈 답(정답) ↔ 빈 호출 실패(오답) — 가 있어야 한다
        refusal = key_item(1, "Q24", "not_in_doc", "", refused=True)
        failed = key_item(1, "Q24", "not_in_doc", "", call_failed=True)
        blank = key_item(1, "Q24", "not_in_doc", "")
        self.assertEqual(self.check(refusal, failed, "정답", "오답")["mismatches"], [])
        r = self.check(blank, failed, "정답", "오답")
        self.assertEqual((r["pairs"], r["empty_pairs"], r["mismatches"]), (0, 0, []))
        r = self.check(failed, dict(failed), "오답", "오답")
        self.assertEqual((r["pairs"], r["empty_pairs"]), (0, 1))


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



# ---------- v2: 질의 확장(hyde · rewrite) · 채택 판정 ----------

class PromptTextTest(unittest.TestCase):
    def test_prompts_match_prereg_v2_blocks(self):
        import re
        doc = (TOOL / "eval" / "PREREG_v2.md").read_text(encoding="utf-8")
        for label, kind in (("E3", "hyde"), ("E4", "rewrite")):
            [block] = re.findall(rf"^{label}:\n\n```\n(.*?)\n```$", doc, re.S | re.M)
            self.assertEqual(evaluate.GEN_PROMPTS[kind], block)


class HeadingListTest(unittest.TestCase):
    def test_levels_subsections_cut_and_fences(self):
        raw = "\n".join(["# 문서", "## 1 가", "본문", "### 1.1 나", "#### 1.1.1 깊은 제목", "**(a) 소절** 설명",
                         "```", "## 코드 안 예시", "```", "**(B-2) " + "다" * 100 + "**"])
        self.assertEqual(evaluate.heading_list(raw), ["## 1 가", "### 1.1 나", "**(a) 소절** 설명", ("**(B-2) " + "다" * 100)[:80]])

    def test_real_doc(self):
        h = evaluate.heading_list(common.read_doc_at(COMMIT))
        self.assertEqual(len(h), 567)                         # 정규식만으로는 573 — 코드 블록 안 템플릿 6줄 제외
        self.assertLessEqual(max(map(len, h)), evaluate.HEADING_CUT)


def keyword_index(chunks):
    """「알파」 · 「베타」 포함 여부 → 2차원 벡터. 메모리 인덱스(코사인)."""
    from llama_index.core import VectorStoreIndex
    from llama_index.core.embeddings import BaseEmbedding
    import index as index_mod

    class KeywordEmbedding(BaseEmbedding):
        def _vec(self, text):
            return [float("알파" in text), float("베타" in text)]

        def _get_text_embedding(self, text):
            return self._vec(text)

        def _get_query_embedding(self, query):
            return self._vec(query)

        async def _aget_query_embedding(self, query):
            return self._vec(query)

    return VectorStoreIndex(index_mod.build_nodes(chunks), embed_model=KeywordEmbedding())


class ExpandTest(unittest.TestCase):
    """질문만 → 0(알파) 1위 · 생성문만 → 1(베타) 1위 · 둘의 평균 → 2(알파 베타) 1위. 어느 한쪽을 버리면 순위가 바뀐다."""

    def setUp(self):
        self.chunks = [chunk("알파 문단"), chunk("베타 문단"), chunk("알파 베타 정답")]
        self.idx = keyword_index(self.chunks)
        self.row = row("Q1", "fact", "알파 질문", ["알파 베타 정답"])
        self.gen = lambda r: "베타 생성문"

    def test_vector_is_mean_of_question_and_generated(self):
        self.assertEqual(evaluate.dense_search(self.idx, self.chunks)(self.row, 3)[0], 0)
        self.assertEqual(evaluate.dense_search(self.idx, self.chunks, self.gen)(self.row, 3)[0], 2)

    def test_gold_removed_expanded(self):
        ecfg = {"hit_k": 3, "mrr_cutoff": 10}
        retr = {k: evaluate.dense_search(self.idx, self.chunks, self.gen) for k in ("hyde", "rewrite")}
        conds = ["hyde", "gold_removed:hyde", "rewrite", "gold_removed:rewrite"]
        recs = evaluate.evaluate_retrieval([self.row], self.chunks, ecfg, retr, conds)
        self.assertEqual([r["rank"] for r in recs], [1, None, 1, None])
        self.assertTrue(all(2 not in r["ranking"] for r in recs if r["condition"].startswith("gold_removed:")))


def fake_gen_factory(calls):
    def make(cfg, seed):
        def complete(prompt):
            calls.append(prompt)
            return f"생성 {len(calls)}", 100, 0, 10
        return complete
    return make


class GenerationCacheTest(unittest.TestCase):
    """검색 평가가 문항마다 한 번 만들고, 답변 단계는 그 파일만 읽는다."""

    @classmethod
    def setUpClass(cls):
        import index
        cls.tmp = tempfile.TemporaryDirectory()
        cls.persist = Path(cls.tmp.name) / "idx"
        with contextlib.redirect_stdout(io.StringIO()):
            index.main(["--commit", COMMIT, "--config", str(CFG_PATH), "--persist-dir", str(cls.persist),
                        "--embed-cache", str(Path(cls.tmp.name) / "cache"), "--mock-embed"])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def args(self, cmd, out, conditions, **kw):
        return SimpleNamespace(cmd=cmd, commit=COMMIT, config=str(CFG_PATH), eval_config=str(ECFG_PATH), conditions=conditions,
                               out_dir=str(Path(self.tmp.name) / out), persist_dir=str(self.persist), **kw)

    def test_retrieval_generates_once_per_question_then_answer_reads_cache(self):
        calls = []
        with contextlib.redirect_stdout(io.StringIO()):
            _, _, rows, _, retr, _, out = evaluate.prepare(
                self.args("retrieval", "r1", "hyde,gold_removed:hyde", max_usd=1.0), True, fake_gen_factory(calls))
        self.assertEqual(len(calls), len(rows))                 # gold_removed 변형도 같은 생성문
        self.assertTrue(all(c.startswith(evaluate.GEN_PROMPTS["hyde"].split("{")[0]) for c in calls))
        cache = out / evaluate.GEN_FILE
        self.assertEqual(len(cache.read_text(encoding="utf-8").splitlines()), len(rows))
        run = json.loads((out / "run.json").read_text(encoding="utf-8"))
        self.assertEqual((run["generation"]["hyde"]["n"], run["rewrite_headings"]["lines"]), (len(rows), 567))

        calls.clear()
        _, _, _, _, retr, _, _ = evaluate.prepare(self.args("answer", "a1", "hyde", gen_cache=str(cache)), True,
                                                  fake_gen_factory(calls))
        self.assertEqual(len(calls), 0)
        self.assertEqual(len(retr["hyde"](rows[0], 5)), 5)

        lines = cache.read_text(encoding="utf-8").splitlines()
        short = Path(self.tmp.name) / "short.jsonl"
        short.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")
        with self.assertRaises(ValueError):                      # 캐시에 없는 문항 = 실패(다시 생성하지 않는다)
            evaluate.prepare(self.args("answer", "a2", "hyde", gen_cache=str(short)), True, fake_gen_factory(calls))
        self.assertEqual(len(calls), 0)

    def test_cost_cap_stops_before_any_call(self):
        calls = []
        with self.assertRaises(ValueError), contextlib.redirect_stdout(io.StringIO()):
            evaluate.prepare(self.args("retrieval", "r2", "rewrite", max_usd=0.0001), True, fake_gen_factory(calls))
        self.assertEqual(calls, [])


def v2_ret(hits, mrr=0.1):
    return [dict(r, mrr=mrr) for r in ret_summary(hits)]


BASE_V2_HITS = {"fact": 3, "identifier": 1, "reversal": 2, "false_premise": 0}   # 전체 6


class AdoptV2Test(unittest.TestCase):
    def test_stage1_boundary_plus_two(self):
        r = evaluate.adopt_v2(1, v2_ret(BASE_V2_HITS), {"E3": v2_ret(dict(BASE_V2_HITS, fact=5)),     # +2 = 통과
                                                       "E4": v2_ret(dict(BASE_V2_HITS, fact=4))})    # +1 = 미통과
        self.assertEqual([(x["experiment"], x["clauses"][0]["diff"], x["pass"]) for x in r["results"]],
                         [("E3", 2, True), ("E4", 1, False)])
        self.assertEqual(r["chosen"], "E3")

    def test_stage1_type_drop_of_two_fails(self):
        r = evaluate.adopt_v2(1, v2_ret(BASE_V2_HITS), {"E5": v2_ret(dict(BASE_V2_HITS, fact=8, reversal=0))})
        self.assertFalse(r["results"][0]["pass"])
        self.assertIsNone(r["chosen"])
        r = evaluate.adopt_v2(1, v2_ret(BASE_V2_HITS), {"E5": v2_ret(dict(BASE_V2_HITS, fact=8, reversal=1))})
        self.assertEqual(r["chosen"], "E5")

    def test_stage1_tie_order(self):
        same = v2_ret(dict(BASE_V2_HITS, fact=5), mrr=0.3)
        for cands, want in ((("E3", "E4", "E5"), "E5"), (("E4", "E3"), "E3"), (("E4",), "E4")):
            r = evaluate.adopt_v2(1, v2_ret(BASE_V2_HITS), {c: same for c in cands})
            self.assertEqual(r["chosen"], want)
        r = evaluate.adopt_v2(1, v2_ret(BASE_V2_HITS), {"E5": same, "E3": v2_ret(dict(BASE_V2_HITS, fact=5), mrr=0.31)})
        self.assertEqual(r["chosen"], "E3")                     # Hit@3 같으면 MRR이 먼저
        r = evaluate.adopt_v2(1, v2_ret(BASE_V2_HITS), {"E5": same, "E4": v2_ret(dict(BASE_V2_HITS, fact=6), mrr=0.1)})
        self.assertEqual(r["chosen"], "E4")                     # Hit@3가 가장 먼저

    def test_stage2_retrieval_and_answers(self):
        n = {"fact": 3, "identifier": 3, "reversal": 3, "false_premise": 3}
        base = [dict(x, mrr=0.1) for x in ret_summary({"fact": 1, "identifier": 1, "reversal": 1, "false_premise": 0}, n)]
        same = [dict(x, mrr=0.1) for x in ret_summary({"fact": 0, "identifier": 2, "reversal": 1, "false_premise": 0}, n)]
        self.assertEqual(evaluate.adopt_v2(2, base, {"E3": same})["chosen"], "E3")             # 차이 0 = 통과
        less = [dict(x, mrr=0.1) for x in ret_summary({"fact": 0, "identifier": 1, "reversal": 1, "false_premise": 0}, n)]
        self.assertIsNone(evaluate.adopt_v2(2, base, {"E3": less})["chosen"])
        with self.assertRaises(ValueError):
            evaluate.adopt_v2(2, base, {"E3": same, "E5": same})
        s = lambda c, p=0: score_summary({"fact": {"정답": c, "부분": p, "오답": 1}})
        self.assertTrue(evaluate.adopt_v2_answers(s(9), s(5), s(5))["pass"])
        self.assertFalse(evaluate.adopt_v2_answers(s(8, 1), s(5), s(5))["pass"])              # 부분은 정답이 아니다
        self.assertFalse(evaluate.adopt_v2_answers(s(9), s(4), s(5))["pass"])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for name, obj in (("b", v2_ret(BASE_V2_HITS)), ("e", v2_ret(dict(BASE_V2_HITS, fact=5)))):
                paths.append(Path(d) / f"{name}.json")
                paths[-1].write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            args = ["adopt-v2", "--stage", "1", "--base-retrieval", str(paths[0]), "--base-cond", "c", "--cands", "E3,E5",
                    "--cand-retrievals", f"{paths[1]},{paths[1]}", "--cand-conds", "c,c", "--out-dir", str(Path(d) / "out")]
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                evaluate.main(args)
            self.assertIn("선택 = E5", buf.getvalue())
            bad = [x if x != "E3,E5" else "E3,E9" for x in args[:-1]] + [str(Path(d) / "out2")]
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                evaluate.main(bad)


class V2ConfigTest(unittest.TestCase):
    def test_h1_set_loads_and_e5_price_matches(self):
        base = common.load_config(CFG_PATH)
        rows = evaluate.load_eval_set(evaluate.load_eval_config(TOOL / "configs" / "eval_h1.json", base))
        self.assertEqual(Counter(r["type"] for r in rows), Counter({t: 3 for t in evaluate.TYPES}))
        e5 = common.load_config(TOOL / "configs" / "e5_large.json")
        self.assertEqual({k for k in base if base[k] != e5[k]}, {"name", "embed_model", "embed_price_usd_per_1m_tokens"})
        common.load_prices(e5)


if __name__ == "__main__":
    unittest.main()
