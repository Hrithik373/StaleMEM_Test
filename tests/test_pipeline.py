import json
import random

import yaml

from stale_repro.data.loader import load_stale, select_subset
from stale_repro.eval.judge import Judge, build_judge_user_prompt
from stale_repro.eval.judge_prompts import SYSTEM_PROMPT_ALL_IN_ONE_JUDGE
from stale_repro.eval.stats import bootstrap_ci, cell_accuracies, mcnemar_exact
from stale_repro.eval.judge import Verdict
from stale_repro.memory.full_context import FullContext, format_haystack, trim_evidence_preserving
from stale_repro.runner import run_system_on_instance

from conftest import BROKEN_LEG, SEATTLE, judge_all_pass


def test_loader_roundtrip(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps([SEATTLE, BROKEN_LEG]))
    insts = load_stale(p)
    assert [x.type for x in insts] == ["T1", "T2"]
    s = insts[0]
    assert s.evidence_indices == (1, 4)
    assert "Seattle" in s.sessions[1].turns[0]["content"]
    assert s.probes["dim3"].is_task and not s.probes["dim2"].is_task


def test_subset_is_deterministic_and_stratified(toy_instances):
    many = []
    for i in range(10):
        for base in toy_instances:
            x = type(base)(**{**base.__dict__, "uid": f"{base.uid}-{i}"})
            many.append(x)
    a = select_subset(many, n_per_type=3, seed=1)
    b = select_subset(list(reversed(many)), n_per_type=3, seed=1)
    assert [x.uid for x in a] == [x.uid for x in b]
    assert sum(x.type == "T1" for x in a) == 3 and sum(x.type == "T2" for x in a) == 3


def test_format_haystack_matches_official():
    out = format_haystack([[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]],
                          ["2025-01-01 10:00"])
    assert out == "\n=== Session 1 [Time: 2025-01-01 10:00] ===\nUser: hi\nAssistant: yo\n"


def test_truncation_preserves_evidence(toy_instances):
    inst = toy_instances[0]
    big = [[{"role": "user", "content": "filler " * 400}] for _ in range(20)]
    big[3] = [{"role": "user", "content": "OLD_EVIDENCE"}]
    big[15] = [{"role": "user", "content": "NEW_EVIDENCE"}]
    ts = [f"t{i}" for i in range(20)]
    sessions, _, tokens, removed = trim_evidence_preserving(
        big, ts, 3, 15, inst.probes["dim1"], "gpt-4o-mini", 4000, random.Random(0))
    text = format_haystack(sessions)
    assert "OLD_EVIDENCE" in text and "NEW_EVIDENCE" in text
    assert removed > 0 and tokens <= 4000


def test_b0_sends_official_prompts(make_gateway, toy_instances):
    gw, backend = make_gateway(lambda m, msgs, p: "answer")
    rec = run_system_on_instance(FullContext(gw), toy_instances[1])
    assert set(rec["answers"]) == {"dim1", "dim2", "dim3"}
    sys_msgs = [c["messages"][0]["content"] for c in backend.calls]
    assert "accurately answer the question" in sys_msgs[0]
    assert "respond to the user's latest query directly" in sys_msgs[2]
    assert "[Latest Query]" in backend.calls[2]["messages"][1]["content"]
    assert "leg in a cast" in backend.calls[0]["messages"][1]["content"]


def test_relevant_only_mode_ingests_two_sessions(make_gateway, toy_instances):
    gw, backend = make_gateway(lambda m, msgs, p: "a")
    run_system_on_instance(FullContext(gw), toy_instances[0], session_mode="relevant_only")
    assert backend.calls[0]["messages"][1]["content"].count("=== Session") == 2


def test_judge_prompt_and_parse(make_gateway, toy_instances):
    gw, backend = make_gateway(judge_all_pass)
    v = Judge(gw).judge(toy_instances[0], {"dim1": "a", "dim2": "b", "dim3": "c"})
    assert v.passed == {"dim1": True, "dim2": True, "dim3": True} and v.error is None
    assert backend.calls[0]["messages"][0]["content"] == SYSTEM_PROMPT_ALL_IN_ONE_JUDGE
    assert backend.calls[0]["params"]["temperature"] == 0
    assert '- M_old: "User lives in Seattle."' in build_judge_user_prompt(
        toy_instances[0], {"dim1": "a", "dim2": "b", "dim3": "c"})


def test_judge_malformed_output_is_error_not_silent(make_gateway, toy_instances):
    gw, _ = make_gateway(lambda m, msgs, p: '{"dim1_eval": {"pass": true}}')
    v = Judge(gw).judge(toy_instances[0], {"dim1": "a", "dim2": "b", "dim3": "c"})
    assert v.error is not None and not any(v.passed.values())


def _v(uid, t, p1, p2, p3):
    return Verdict(uid, t, {"dim1": p1, "dim2": p2, "dim3": p3})


def test_overall_is_mean_of_six_cells():
    vs = [_v("a", "T1", True, False, True), _v("b", "T1", True, False, False),
          _v("c", "T2", False, False, True), _v("d", "T2", False, False, False)]
    acc = cell_accuracies(vs)
    assert acc["T1.dim1"] == 1.0 and acc["T1.dim3"] == 0.5 and acc["T2.dim3"] == 0.5
    assert abs(acc["overall"] - (1 + 0 + .5 + 0 + 0 + .5) / 6) < 1e-9
    ci = bootstrap_ci(vs, n_boot=200)
    assert ci["T1.dim1"] == (1.0, 1.0)


def test_mcnemar():
    assert mcnemar_exact([True] * 5, [True] * 5)["p_value"] == 1.0
    r = mcnemar_exact([True] * 10 + [False] * 10, [False] * 10 + [False] * 10)
    assert r["a_only"] == 10 and r["p_value"] < 0.01


def test_runner_end_to_end(tmp_path, monkeypatch, toy_instances):
    """Full config-driven run with a fake backend patched into the gateway factory."""
    import stale_repro.runner as runner
    from stale_repro.llm.gateway import Gateway
    from conftest import FakeBackend

    data = tmp_path / "d.json"
    data.write_text(json.dumps([SEATTLE, BROKEN_LEG]))

    def fake_factory(cfg, cache_dir, log_path=None):
        fn = judge_all_pass if cfg["model"] == "judge" else (lambda m, msgs, p: "sys answer")
        return Gateway(FakeBackend(fn), model=cfg["model"], cache_path=tmp_path / "c.sqlite", log_path=log_path)

    monkeypatch.setattr(runner, "gateway_from_config", fake_factory)
    cfg = {"name": "e2e", "data": str(data), "workers": 2,
           "system": {"kind": "full_context", "llm": {"model": "sys"}, "args": {}},
           "judge": {"llm": {"model": "judge"}}}
    s = runner.run(cfg, out_root=tmp_path / "runs")
    assert s["n_instances"] == 2 and s["accuracy"]["overall"] == 1.0
    # resume: nothing new to do, same result
    s2 = runner.run(cfg, out_root=tmp_path / "runs")
    assert s2["accuracy"] == s["accuracy"]
    assert (tmp_path / "runs" / "e2e" / "summary.md").exists()
    assert yaml.safe_load((tmp_path / "runs" / "e2e" / "config.yaml").read_text())["name"] == "e2e"
