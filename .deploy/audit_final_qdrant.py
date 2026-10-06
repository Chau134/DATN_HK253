#!/usr/bin/env python3
import json
import urllib.request


BASE = "http://10.148.0.4:6333/collections"
TEXT = "product_text_vectors_qwen3_embedding_8b_4096_metadata_v4_1000_products"
IMAGE = "product_image_vectors_qwen3_vl_embedding_2b_2048_1000_products"


def get(path):
    with urllib.request.urlopen(path, timeout=60) as response:
        return json.load(response)["result"]


def scroll(collection):
    product_ids = set()
    image_urls = set()
    offset = None
    while True:
        body = {"limit": 1000, "with_payload": True, "with_vector": False}
        if offset is not None:
            body["offset"] = offset
        request = urllib.request.Request(
            f"{BASE}/{collection}/points/scroll",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)["result"]
        for point in result["points"]:
            payload = point.get("payload") or {}
            if payload.get("product_id") is not None:
                product_ids.add(str(payload["product_id"]))
            if payload.get("image_url"):
                image_urls.add((str(payload["product_id"]), payload["image_url"]))
        offset = result.get("next_page_offset")
        if offset is None:
            return product_ids, image_urls


text_info = get(f"{BASE}/{TEXT}")
image_info = get(f"{BASE}/{IMAGE}")
text_products, _ = scroll(TEXT)
image_products, image_urls = scroll(IMAGE)

print(f"TEXT_STATUS={text_info['status']}")
print(f"TEXT_VECTOR_SIZE={text_info['config']['params']['vectors']['size']}")
print(f"TEXT_POINT_COUNT={text_info['points_count']}")
print(f"TEXT_UNIQUE_PRODUCT_COUNT={len(text_products)}")
print(f"IMAGE_STATUS={image_info['status']}")
print(f"IMAGE_VECTOR_SIZE={image_info['config']['params']['vectors']['size']}")
print(f"IMAGE_POINT_COUNT={image_info['points_count']}")
print(f"IMAGE_UNIQUE_PRODUCT_COUNT={len(image_products)}")
print(f"IMAGE_UNIQUE_URL_COUNT={len(image_urls)}")
print("TEXT_ONLY_PRODUCTS=" + json.dumps(sorted(text_products - image_products)))
print("IMAGE_ONLY_PRODUCTS=" + json.dumps(sorted(image_products - text_products)))
