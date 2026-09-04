import pytest

from ecommerce_search_assistant.services.assistant.shop_knowledge import (
    resolve_shop_knowledge,
)


@pytest.mark.parametrize(
    ("message", "topic", "expected"),
    (
        ("Chào bạn, shop mình có tên gì nhỉ?", "shop_identity", "Mystery Closet"),
        ("Hotline của shop là số nào?", "contact_information", "1900 1340"),
        ("Shop ở đâu?", "contact_information", "260 Lý Thường Kiệt"),
        ("Đổi trả được mấy ngày?", "return_policy", "07 ngày"),
        ("Áo được bảo hành bao lâu?", "warranty_policy", "30 ngày"),
        ("Đơn hàng giao trong bao lâu?", "shipping_time_policy", "1-2 ngày"),
        ("Đơn 90k có freeship không?", "shipping_fee_policy", "500.000đ"),
        ("Có thể thanh toán bằng MoMo không?", "payment_methods", "MoMo"),
        ("Shop có các chính sách gì?", "policy_overview", "Chính sách bảo mật"),
    ),
)
def test_resolve_shop_knowledge_uses_published_storefront_facts(
    message: str,
    topic: str,
    expected: str,
) -> None:
    result = resolve_shop_knowledge(message)

    assert result is not None
    assert result.topic == topic
    assert expected in result.answer


def test_resolve_shop_knowledge_does_not_claim_unknown_information() -> None:
    assert resolve_shop_knowledge("Shop có gói quà miễn phí theo yêu cầu không?") is None


def test_resolve_shop_knowledge_answers_compound_identity_and_location_question() -> None:
    result = resolve_shop_knowledge(
        "shop hiện tại có tên là gì? cho tôi vị trí của shop được không?"
    )

    assert result is not None
    assert result.topic == "shop_identity_and_location"
    assert "Mystery Closet" in result.answer
    assert "260 Lý Thường Kiệt" in result.answer


def test_resolve_shop_knowledge_routes_catalog_overview_without_inventing_answer() -> None:
    result = resolve_shop_knowledge(
        "shop hiện tại đang bán những loại sản phẩm nào?"
    )

    assert result is not None
    assert result.topic == "catalog_overview"
    assert result.answer == ""


@pytest.mark.parametrize(
    ("message", "expected_prefix", "grounded_fact"),
    (
        (
            "Shop có cam kết bảo hành trọn đời cho mọi sản phẩm không?",
            "Không, shop không có cam kết bảo hành trọn đời.",
            "30 ngày",
        ),
        (
            "Shop có cam kết hoàn tiền 200 phần trăm trong mọi trường hợp không?",
            "Không, shop không có cam kết hoàn tiền 200% trong mọi trường hợp.",
            "07 ngày",
        ),
    ),
)
def test_policy_contradictions_are_rejected_before_grounded_correction(
    message: str,
    expected_prefix: str,
    grounded_fact: str,
) -> None:
    result = resolve_shop_knowledge(message)

    assert result is not None
    assert result.answer.startswith(expected_prefix)
    assert grounded_fact in result.answer
