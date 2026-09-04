from __future__ import annotations

import argparse
import csv
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVIEW_FIELDS = [
    "query_id",
    "difficulty",
    "query_product_id",
    "query_product_name",
    "query_category",
    "query_image_url",
    "candidate_rank",
    "candidate_product_id",
    "candidate_product_name",
    "candidate_category",
    "candidate_brand",
    "candidate_color",
    "candidate_material",
    "candidate_image_url",
    "candidate_image_urls",
    "retrieval_score",
    "candidate_source",
    "review_priority",
    "suggested_grade",
    "suggestion_reason",
    "relevance_grade",
    "review_status",
    "reviewer_notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def normalize(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().split())


def product_images_by_id(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    preference = {"MAIN": 0, "DETAIL_1": 1, "FLAT_1": 2, "MODEL_1": 3}
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("product_id") and row.get("image_url"):
            grouped[row["product_id"]].append(row)
    resolved: dict[str, list[str]] = {}
    for product_id, images in grouped.items():
        images.sort(
            key=lambda row: (
                preference.get((row.get("image_type") or "").upper(), 10),
                int(row.get("sort_order") or 999),
            )
        )
        resolved[product_id] = list(dict.fromkeys(row["image_url"] for row in images))[:3]
    return resolved


def suggested_grade(query: dict[str, str], product: dict[str, str]) -> tuple[int, str]:
    if product.get("product_id") == query.get("source_product_id"):
        return 3, "source_product_exact_match_requires_visual_verification"
    if normalize(product.get("category")) != normalize(query.get("category")):
        return 0, "different_category"
    matched = [
        field
        for field in ("color", "material", "gender")
        if normalize(query.get(field)) and normalize(query.get(field)) == normalize(product.get(field))
    ]
    if len(matched) >= 2:
        return 2, "same_category+" + "+".join(matched)
    return 1, "same_category" + ("+" + "+".join(matched) if matched else "")


def build_review_rows(
    queries: list[dict[str, str]],
    products: list[dict[str, str]],
    product_images: list[dict[str, str]],
    results: list[dict[str, str]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    product_by_id = {row.get("product_id", ""): row for row in products}
    images_by_product = product_images_by_id(product_images)
    results_by_query: dict[str, list[dict[str, str]]] = defaultdict(list)
    for result in results:
        try:
            rank = int(float(result.get("rank") or "0"))
        except ValueError:
            continue
        if 0 < rank <= top_k and result.get("product_id"):
            results_by_query[result.get("query_id", "")].append(result)
    for query_results in results_by_query.values():
        query_results.sort(key=lambda row: int(float(row.get("rank") or "0")))

    review_rows: list[dict[str, Any]] = []
    for query in queries:
        query_id = query.get("query_id", "")
        source_product_id = query.get("source_product_id", "")
        ranked = list(results_by_query.get(query_id, []))
        ranked_ids = {row.get("product_id", "") for row in ranked}
        if source_product_id and source_product_id not in ranked_ids:
            ranked.append(
                {
                    "query_id": query_id,
                    "rank": "",
                    "product_id": source_product_id,
                    "score": "",
                    "candidate_source": "source_product_not_retrieved",
                }
            )
        for result in ranked:
            product_id = result.get("product_id", "")
            product = product_by_id.get(product_id, {"product_id": product_id})
            grade, reason = suggested_grade(query, product)
            rank_text = result.get("rank", "")
            rank = int(float(rank_text)) if rank_text else None
            is_source = product_id == source_product_id
            if is_source and rank is None:
                priority = "source_mapping_check"
            elif rank is not None and rank <= 5:
                priority = "top5"
            elif rank is not None and rank <= 10:
                priority = "top10"
            else:
                priority = "top20"
            image_urls = images_by_product.get(product_id, [])
            review_rows.append(
                {
                    "query_id": query_id,
                    "difficulty": query.get("difficulty", ""),
                    "query_product_id": source_product_id,
                    "query_product_name": product_by_id.get(source_product_id, {}).get("product_name", ""),
                    "query_category": query.get("category", ""),
                    "query_image_url": query.get("image_url", ""),
                    "candidate_rank": rank_text,
                    "candidate_product_id": product_id,
                    "candidate_product_name": product.get("product_name", ""),
                    "candidate_category": product.get("category", ""),
                    "candidate_brand": product.get("brand", ""),
                    "candidate_color": product.get("color", ""),
                    "candidate_material": product.get("material", ""),
                    "candidate_image_url": image_urls[0] if image_urls else "",
                    "candidate_image_urls": " | ".join(image_urls),
                    "retrieval_score": result.get("score", ""),
                    "candidate_source": result.get("candidate_source") or "retrieval_top_k",
                    "review_priority": priority,
                    "suggested_grade": grade,
                    "suggestion_reason": reason,
                    "relevance_grade": "",
                    "review_status": "pending",
                    "reviewer_notes": "",
                }
            )
    return review_rows


def render_html(rows: list[dict[str, Any]], output_path: Path) -> None:
    payload = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    title = "Image Ground Truth Review"
    document = f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 0; background: #f4f6f8; color: #17202a; }}
    header {{ position: sticky; top: 0; z-index: 2; background: white; padding: 14px 20px; box-shadow: 0 2px 8px #0002; }}
    h1 {{ margin: 0 0 8px; font-size: 22px; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    button, select, input {{ padding: 7px 9px; }}
    #stats {{ font-weight: 600; margin-left: auto; }}
    main {{ padding: 16px; max-width: 1500px; margin: auto; }}
    .guide {{ background: #fffbe6; border: 1px solid #ead68a; padding: 10px; margin-bottom: 12px; }}
    .card {{ background: white; border: 1px solid #d9e0e6; border-radius: 8px; margin: 10px 0; padding: 12px; }}
    .meta {{ display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 8px; font-size: 14px; }}
    .images {{ display: grid; grid-template-columns: minmax(180px, 1fr) minmax(180px, 2fr); gap: 12px; }}
    .query img, .candidate img {{ width: 100%; max-height: 360px; object-fit: contain; background: #eee; }}
    .candidate-grid {{ display: grid; grid-template-columns: repeat(3, minmax(100px, 1fr)); gap: 6px; }}
    .review {{ display: grid; grid-template-columns: 150px 150px 1fr; gap: 8px; margin-top: 10px; }}
    .source_mapping_check {{ border: 3px solid #d33; }}
    .top5 {{ border-left: 5px solid #e69f00; }}
    small {{ color: #59636e; }}
    @media (max-width: 700px) {{ .images, .review {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<header>
  <h1>{html.escape(title)}</h1>
  <div class="controls">
    <input id="queryFilter" placeholder="query ID">
    <select id="difficultyFilter"><option value="">mọi độ khó</option><option>easy</option><option>medium</option><option>hard</option></select>
    <select id="priorityFilter"><option value="">mọi ưu tiên</option><option>source_mapping_check</option><option selected>top5</option><option>top10</option><option>top20</option></select>
    <select id="statusFilter"><option value="">mọi trạng thái</option><option>pending</option><option>approved</option><option>rejected</option></select>
    <button id="export">Xuất CSV đã review</button><span id="stats"></span>
  </div>
</header>
<main>
  <div class="guide"><b>Grade:</b> 3 = đúng SKU; 2 = rất giống, có thể thay thế; 1 = liên quan nhưng giống yếu; 0 = không liên quan.
  Chỉ chọn <b>approved</b> sau khi đã nhìn cả ảnh query và ảnh candidate. Dữ liệu được tự lưu trong trình duyệt.</div>
  <div id="cards"></div>
</main>
<script>
const rows = {payload};
const storageKey = 'image-ground-truth-review-v3|' + window.location.pathname;
const rowKey = row => row.query_id + '|' + row.query_image_url + '|' + row.candidate_product_id;
const saved = JSON.parse(localStorage.getItem(storageKey) || '{{}}');
for (const row of rows) {{
  const key = rowKey(row);
  if (saved[key]) Object.assign(row, saved[key]);
}}
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function persist(row) {{
  const key = rowKey(row);
  saved[key] = {{ relevance_grade: row.relevance_grade, review_status: row.review_status, reviewer_notes: row.reviewer_notes }};
  localStorage.setItem(storageKey, JSON.stringify(saved));
}}
function render() {{
  const query = document.querySelector('#queryFilter').value.trim().toLowerCase();
  const difficulty = document.querySelector('#difficultyFilter').value;
  const priority = document.querySelector('#priorityFilter').value;
  const status = document.querySelector('#statusFilter').value;
  const visible = rows.filter(r => (!query || r.query_id.toLowerCase().includes(query)) && (!difficulty || r.difficulty === difficulty) && (!priority || r.review_priority === priority) && (!status || r.review_status === status));
  document.querySelector('#stats').textContent = `${{visible.length}}/${{rows.length}} dòng · ${{rows.filter(r => r.review_status === 'approved').length}} approved`;
  document.querySelector('#cards').innerHTML = visible.map((r, i) => `
    <section class="card ${{esc(r.review_priority)}}" data-key="${{esc(rowKey(r))}}">
      <div class="meta"><b>${{esc(r.query_id)}}</b><span>${{esc(r.difficulty)}}</span><span>rank ${{esc(r.candidate_rank || 'missing')}}</span><span>priority ${{esc(r.review_priority)}}</span><span>score ${{esc(r.retrieval_score)}}</span></div>
      <div class="images">
        <div class="query"><b>Query · ${{esc(r.query_product_id)}} · ${{esc(r.query_product_name)}}</b><br><small>${{esc(r.query_category)}}</small><img loading="lazy" src="${{esc(r.query_image_url)}}"></div>
        <div class="candidate"><b>Candidate · ${{esc(r.candidate_product_id)}} · ${{esc(r.candidate_product_name)}}</b><br><small>${{esc(r.candidate_category)}} · ${{esc(r.candidate_color)}} · ${{esc(r.candidate_material)}}</small><div class="candidate-grid">${{r.candidate_image_urls.split(' | ').filter(Boolean).map(url => `<img loading="lazy" src="${{esc(url)}}">`).join('')}}</div></div>
      </div>
      <small>Rule gợi ý grade ${{esc(r.suggested_grade)}}: ${{esc(r.suggestion_reason)}}</small>
      <div class="review">
        <select class="grade"><option value="">grade?</option>${{[0,1,2,3].map(g => `<option value="${{g}}" ${{String(r.relevance_grade)===String(g)?'selected':''}}>${{g}}</option>`).join('')}}</select>
        <select class="status"><option ${{r.review_status==='pending'?'selected':''}}>pending</option><option ${{r.review_status==='approved'?'selected':''}}>approved</option><option ${{r.review_status==='rejected'?'selected':''}}>rejected</option></select>
        <input class="notes" value="${{esc(r.reviewer_notes)}}" placeholder="ghi chú reviewer">
      </div>
    </section>`).join('');
  document.querySelectorAll('.card').forEach(card => {{
    const row = rows.find(r => rowKey(r) === card.dataset.key);
    card.querySelector('.grade').onchange = e => {{ row.relevance_grade = e.target.value; persist(row); }};
    card.querySelector('.status').onchange = e => {{ row.review_status = e.target.value; persist(row); render(); }};
    card.querySelector('.notes').onchange = e => {{ row.reviewer_notes = e.target.value; persist(row); }};
  }});
}}
function csvCell(value) {{ const text = String(value ?? ''); return /[",\\n]/.test(text) ? '"'+text.replaceAll('"','""')+'"' : text; }}
document.querySelector('#export').onclick = () => {{
  const fields = {json.dumps(REVIEW_FIELDS, ensure_ascii=False)};
  const csv = [fields.join(','), ...rows.map(row => fields.map(field => csvCell(row[field])).join(','))].join('\\n');
  const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([csv], {{type:'text/csv;charset=utf-8'}})); link.download = 'ground_truth_image_reviewed.csv'; link.click(); URL.revokeObjectURL(link.href);
}};
for (const id of ['queryFilter','difficultyFilter','priorityFilter','statusFilter']) document.querySelector('#'+id).oninput = render;
render();
</script>
</body>
</html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a visual review queue from image-search results.")
    parser.add_argument("--query-set-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "image_queries.csv")
    parser.add_argument("--products-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_snapshot.csv")
    parser.add_argument("--product-images-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_images.csv")
    parser.add_argument("--results-csv", type=Path, default=None)
    parser.add_argument("--input-review-csv", type=Path, default=None)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "reports" / "ground_truth_image_review_candidates.csv")
    parser.add_argument("--output-html", type=Path, default=SCRIPT_DIR.parent / "reports" / "image_ground_truth_review.html")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.input_review_csv:
        rows = read_csv(args.input_review_csv)
        render_html(rows, args.output_html)
        print(f"review_rows={len(rows)} rendered from {args.input_review_csv}")
        print(f"html -> {args.output_html}")
        return 0
    if args.results_csv is None:
        raise ValueError("--results-csv is required unless --input-review-csv is provided")
    rows = build_review_rows(
        read_csv(args.query_set_csv),
        read_csv(args.products_csv),
        read_csv(args.product_images_csv),
        read_csv(args.results_csv),
        top_k=args.top_k,
    )
    write_csv(args.output_csv, rows)
    render_html(rows, args.output_html)
    priorities: dict[str, int] = defaultdict(int)
    for row in rows:
        priorities[str(row["review_priority"])] += 1
    print(f"review_rows={len(rows)} priorities={dict(priorities)}")
    print(f"csv -> {args.output_csv}")
    print(f"html -> {args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
