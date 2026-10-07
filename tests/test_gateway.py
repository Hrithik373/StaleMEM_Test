import json

import pytest

from stale_repro.llm.gateway import parse_json_loose


def test_cache_hit_skips_backend(make_gateway):
    gw, backend = make_gateway(lambda m, msgs, p: "hello")
    a = gw.chat("hi", tag="t")
    b = gw.chat("hi", tag="t")
    assert a.text == b.text == "hello"
    assert not a.cached and b.cached
    assert len(backend.calls) == 1
    s = gw.summary()["t"]
    assert s["calls"] == 2 and s["cached_calls"] == 1


def test_cache_key_depends_on_params(make_gateway):
    gw, backend = make_gateway(lambda m, msgs, p: "x")
    gw.chat("hi", temperature=0.0)
    gw.chat("hi", temperature=0.7)
    gw.chat("hi", model="other")
    assert len(backend.calls) == 3


def test_cache_persists_across_gateways(tmp_path, make_gateway):
    gw1, b1 = make_gateway(lambda m, msgs, p: "persisted")
    gw1.chat("q")
    gw2, b2 = make_gateway(lambda m, msgs, p: "SHOULD NOT BE CALLED")
    assert gw2.chat("q").text == "persisted"
    assert len(b2.calls) == 0


def test_json_mode_parses_fenced_output(make_gateway):
    gw, backend = make_gateway(lambda m, msgs, p: '```json\n{"a": 1}\n```')
    r = gw.chat("give json", json_mode=True)
    assert r.parsed == {"a": 1}
    assert backend.calls[0]["params"]["response_format"] == {"type": "json_object"}


def test_json_repair_retry_then_failure_is_counted(make_gateway):
    replies = iter(["not json at all", "still not json"])
    gw, backend = make_gateway(lambda m, msgs, p: next(replies))
    r = gw.chat("give json", json_mode=True, tag="x")
    assert not r.ok_json
    assert len(backend.calls) == 2
    assert gw.summary()["x"]["json_failures"] == 1


def test_json_repair_retry_succeeds(make_gateway):
    replies = iter(["oops", '{"ok": true}'])
    gw, _ = make_gateway(lambda m, msgs, p: next(replies))
    assert gw.chat("give json", json_mode=True).parsed == {"ok": True}


def test_json_schema_sets_response_format(make_gateway):
    gw, backend = make_gateway(lambda m, msgs, p: '{"label": "KEEP"}')
    schema = {"title": "adj", "type": "object", "properties": {"label": {"type": "string"}},
              "required": ["label"], "additionalProperties": False}
    gw.chat("x", json_schema=schema)
    rf = backend.calls[0]["params"]["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["schema"] == schema


def test_usage_log_written(make_gateway, tmp_path):
    gw, _ = make_gateway(lambda m, msgs, p: "hi")
    gw.chat("a", tag="stage.one")
    lines = (tmp_path / "calls.jsonl").read_text().splitlines()
    assert json.loads(lines[0])["tag"] == "stage.one"


@pytest.mark.parametrize("text,expected", [
    ('{"a": 1}', {"a": 1}),
    ('Sure! Here it is: {"a": [1, 2]} hope that helps', {"a": [1, 2]}),
    ("```\n[1, 2]\n```", [1, 2]),
])
def test_parse_json_loose(text, expected):
    assert parse_json_loose(text) == expected


def test_parse_json_loose_raises():
    with pytest.raises(ValueError):
        parse_json_loose("no json here")


def test_tpm_limiter_waits_when_window_full(monkeypatch):
    import stale_repro.llm.gateway as g
    clock = {"t": 0.0}
    slept = []
    monkeypatch.setattr(g.time, "monotonic", lambda: clock["t"])

    def fake_sleep(s):
        slept.append(s)
        clock["t"] += s
    monkeypatch.setattr(g.time, "sleep", fake_sleep)
    lim = g.TPMLimiter(tpm=100)
    lim.acquire(60)
    lim.acquire(30)          # fits (90 <= 100)
    assert slept == []
    lim.acquire(50)          # must wait for the first event to leave the window
    assert slept and clock["t"] >= 60.0


def test_estimate_request_tokens_matches_openai_style():
    from stale_repro.llm.gateway import estimate_request_tokens
    assert estimate_request_tokens([{"role": "user", "content": "x" * 400}], {}) == 100 + 16384
    assert estimate_request_tokens([{"role": "user", "content": "x" * 400}], {"max_tokens": 50}) == 150
