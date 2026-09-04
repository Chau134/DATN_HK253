from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import uuid

import httpx
from qdrant_client import QdrantClient, models


DEFAULT_IMAGE_URL = (
    "https://res.cloudinary.com/dhtlzqflg/image/upload/"
    "v1787583152/q86_okf4pg.png"
)
DEFAULT_TEXT_COLLECTION = (
    "product_text_vectors_cohere_embed_v4_1536_metadata_v4_1000_products"
)
INITIAL_QUERY = (
    "tìm sản phẩm nữ giống ảnh, màu trắng, "
    "giá tối đa một triệu đồng"
)
REFINEMENT = (
    "cho tôi các lựa chọn khác nhưng giữ nguyên "
    "màu, giới tính và ngân sách"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the E2E-03 white-color smoke test.")
    parser.add_argument("--ai-url", default="http://127.0.0.1:8000")
    parser.add_argument("--qdrant-url", default="http://127.0.0.1:6333")
    parser.add_argument("--image-url", default=DEFAULT_IMAGE_URL)
    parser.add_argument("--text-collection", default=DEFAULT_TEXT_COLLECTION)
    parser.add_argument("--skip-conversation", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with httpx.Client(timeout=240) as client:
        image_response = client.get(args.image_url)
        image_response.raise_for_status()
        image = {
            "content_type": image_response.headers.get("content-type", "image/png")
            .partition(";")[0],
            "data_base64": base64.b64encode(image_response.content).decode("ascii"),
            "filename": "q86_okf4pg.png",
        }
        filters = {"gender": "women", "colors": ["white"], "max_price": 1_000_000}
        hybrid_response = client.post(
            f"{args.ai_url.rstrip('/')}/search/hybrid",
            json={
                "query": INITIAL_QUERY,
                "image": image,
                "filters": filters,
                "top_k": 5,
            },
        )
        hybrid_response.raise_for_status()
        hybrid = hybrid_response.json()

        conversation: list[dict[str, object]] = []
        if not args.skip_conversation:
            session_id = f"e2e03-white-{uuid.uuid4().hex[:10]}"
            turns = [
                {
                    "session_id": session_id,
                    "user_id": "e2e-validator",
                    "turn_sequence": 1,
                    "message": INITIAL_QUERY,
                    "image": image,
                    "locale": "vi-VN",
                },
                {
                    "session_id": session_id,
                    "user_id": "e2e-validator",
                    "turn_sequence": 2,
                    "message": REFINEMENT,
                    "locale": "vi-VN",
                },
            ]
            for turn in turns:
                response = client.post(
                    f"{args.ai_url.rstrip('/')}/assistant/chat", json=turn
                )
                response.raise_for_status()
                body = response.json()
                conversation.append(
                    {
                        "turn_sequence": turn["turn_sequence"],
                        "filters": body.get("filters"),
                        "product_ids": [
                            item["product_id"] for item in body.get("product_ids", [])
                        ],
                        "warnings": body.get("warnings", []),
                    }
                )

    product_ids = [str(value) for value in hybrid.get("product_ids", [])]
    qdrant = QdrantClient(url=args.qdrant_url)
    points, _ = qdrant.scroll(
        collection_name=args.text_collection,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="product_id", match=models.MatchAny(any=product_ids)
                )
            ]
        ),
        limit=max(len(product_ids), 1),
        with_payload=True,
        with_vectors=False,
    )
    payload_by_id = {
        str((point.payload or {}).get("product_id")): point.payload or {}
        for point in points
    }
    verification = [
        {
            "product_id": product_id,
            "base_colour": payload_by_id.get(product_id, {}).get("base_colour"),
            "color_keys": payload_by_id.get(product_id, {}).get("color_keys"),
            "gender": payload_by_id.get(product_id, {}).get("gender"),
            "selling_price": payload_by_id.get(product_id, {}).get("selling_price"),
        }
        for product_id in product_ids
    ]
    explicit_ok = all(
        item.get("explicit_constraint_satisfied") is True
        for item in hybrid.get("results", [])
    )
    payload_ok = len(verification) == 5 and all(
        "white" in (item.get("color_keys") or [])
        and str(item.get("gender") or "").lower() == "women"
        and float(item.get("selling_price") or float("inf")) <= 1_000_000
        for item in verification
    )
    preserved = all(
        (turn.get("filters") or {}).get("colors") == ["white"]
        and (turn.get("filters") or {}).get("gender") == "women"
        and (turn.get("filters") or {}).get("max_price") == 1_000_000
        for turn in conversation
    ) if conversation else None
    result = {
        "run_id": f"E2E-03-HYBRID-WHITE-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": f"{args.ai_url.rstrip('/')}/search/hybrid",
        "request": {
            "query": INITIAL_QUERY,
            "image_url": args.image_url,
            "filters": filters,
            "refinement": REFINEMENT if conversation else None,
        },
        "hybrid": {
            "product_ids": product_ids,
            "filters": hybrid.get("filters"),
            "relaxed_filters": hybrid.get("relaxed_filters", []),
            "explicit_constraints_satisfied": explicit_ok,
        },
        "payload_verification": verification,
        "conversation": conversation,
        "assertions": {
            "returned_count": len(product_ids),
            "payload_constraints_satisfied": payload_ok,
            "conversation_constraints_preserved": preserved,
            "result": "PASS" if explicit_ok and payload_ok and preserved is not False else "FAIL",
        },
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["assertions"]["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
