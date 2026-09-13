import importlib.util
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


spec = importlib.util.spec_from_file_location(
    "checkpoint_runner", Path(__file__).resolve().parents[1] / "scripts/07_run_search.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def configure(monkeypatch, tmp_path):
    queries = [{"query_id": f"q{i}", "query_text": "user text", "image_url": "unused", "target_product_id": "p",
                "transformation_type": "material", "difficulty": "easy"} for i in range(100)]
    args = SimpleNamespace(queries_csv=tmp_path / "queries.csv", results_csv=tmp_path / "results.csv",
                           responses_jsonl=tmp_path / "responses.jsonl", run_id="test", base_url="http://test", endpoint=None,
                           variant="fusion", expect_rerank="disabled", top_k=20, timeout=1, download_timeout=1)
    monkeypatch.setattr(runner, "parse_args", lambda: args)
    monkeypatch.setattr(runner, "read_csv", lambda _: queries)
    monkeypatch.setattr(runner.urllib.request, "urlopen", lambda *a, **kw: BytesIO(b'{"effective_features":{"reranker_enabled":false}}'))
    monkeypatch.setattr(runner, "image_payload", lambda *a: ({"data_base64": "test"}, 1))
    return args


def test_completed_queries_survive_interruption(monkeypatch, tmp_path):
    args = configure(monkeypatch, tmp_path)
    calls = []
    def search(*a, **kw):
        calls.append(kw)
        if len(calls) == 4:
            raise KeyboardInterrupt()
        return 200, {"results": [{"product_id": "p", "score": 1}]}, 1
    monkeypatch.setattr(runner, "call_search", search)
    with pytest.raises(KeyboardInterrupt):
        runner.main()
    rows = [json.loads(line) for line in args.responses_jsonl.read_text().splitlines()]
    assert [row["query_id"] for row in rows] == ["q0", "q1", "q2"]
    assert args.results_csv.read_text().count("test,") == 3
    assert all(set(call) == {"query", "image", "top_k", "timeout"} for call in calls)


def test_existing_evidence_is_not_overwritten(monkeypatch, tmp_path):
    args = configure(monkeypatch, tmp_path)
    args.results_csv.write_text("prior evidence", encoding="utf-8")
    with pytest.raises(FileExistsError):
        runner.main()
    assert args.results_csv.read_text() == "prior evidence"
