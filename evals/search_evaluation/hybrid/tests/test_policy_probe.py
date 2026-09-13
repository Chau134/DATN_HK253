import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


spec = importlib.util.spec_from_file_location(
    "policy_probe", Path(__file__).resolve().parents[1] / "scripts/16_policy_probe.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_composition_accepts_yarn_qualifier_but_rejects_blend():
    case = {"composition": {"cotton": 100}}
    response = {"product_ids": ["a"]}
    assert not probe.violations(case, response, {"a": {"material": "100% Cotton Yarn", "price": "100"}})
    assert probe.violations(case, response, {"a": {"material": "95% Cotton, 5% Elastane", "price": "100"}}) == ["a:composition_cotton"]


def test_empty_response_cannot_pass_positive_probe():
    assert probe.violations({}, {"product_ids": []}, {}) == ["unexpected_empty"]
    assert not probe.violations({"expect_empty": True}, {"product_ids": []}, {})


def test_http_failure_cannot_pass_expected_empty_probe():
    assert probe.violations({"expect_empty": True}, {}, {}, status=500) == ["http_status:500"]
    assert probe.violations({"allow_empty": True}, {}, {}, status=503) == ["http_status:503"]


def test_duplicate_ids_are_detected():
    assert "duplicate_product_id" in probe.violations({}, {"product_ids": ["a", "a"]}, {"a": {"price": "100"}})


def test_price_boundaries_are_independent_of_api_flags():
    response = {"product_ids": ["a"], "results": [{"explicit_constraint_satisfied": True}]}
    products = {"a": {"price": "500000"}}
    assert probe.violations({"max_exclusive": 500000}, response, products) == ["a:max_exclusive"]
    assert not probe.violations({"max_inclusive": 500000}, response, products)


def test_download_recovers_before_measurement(monkeypatch):
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    call = Mock(side_effect=[TimeoutError(), ("image-bytes", "image/jpeg")])
    assert probe.download_image(SimpleNamespace(image_payload=call), "https://example.test/image") == "image-bytes"
    assert call.call_count == 2


def test_download_retry_is_bounded(monkeypatch):
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    call = Mock(side_effect=probe.urllib.error.URLError("network unavailable"))
    with pytest.raises(probe.urllib.error.URLError):
        probe.download_image(SimpleNamespace(image_payload=call), "https://example.test/image")
    assert call.call_count == 3


@pytest.mark.parametrize("usage,passed", [("dạo phố, đi làm", True), ("du lịch", True), ("đi làm", False), ("", False)])
def test_usage_any_probe_is_independent_and_requires_one_match(usage, passed):
    failures = probe.violations({"contains_any": {"usage": ["di choi", "dao pho", "du lich"]}},
                                {"product_ids": ["a"]}, {"a": {"usage": usage, "price": "100"}})
    assert (not failures) is passed
