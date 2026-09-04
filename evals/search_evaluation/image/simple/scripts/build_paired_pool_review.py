from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
FIELDS = [
    "query_id",
    "query_product_id",
    "query_product_name",
    "query_category",
    "simple_query_image_url",
    "challenging_query_image_url",
    "candidate_product_id",
    "candidate_product_name",
    "candidate_category",
    "candidate_brand",
    "candidate_color",
    "candidate_material",
    "candidate_image_url",
    "candidate_image_urls",
    "simple_rank",
    "simple_score",
    "challenging_rank",
    "challenging_score",
    "pool_sources",
    "blind_order",
    "relevance_grade",
    "review_status",
    "reviewer_notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def image_map(rows: list[dict[str, str]]) -> dict[str, list[str]]:
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


def ranked(rows: list[dict[str, str]], top_k: int) -> dict[tuple[str, str], dict[str, str]]:
    output: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        rank = int(float(row.get("rank") or 0))
        if 0 < rank <= top_k:
            key = (row.get("query_id", ""), row.get("product_id", ""))
            if key in output:
                raise ValueError(f"duplicate result pair: {key}")
            output[key] = row
    return output


def normalize(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().split())


def metadata_rule_grade(query_product: dict[str, str], candidate: dict[str, str]) -> tuple[int, str]:
    if candidate.get("product_id") == query_product.get("product_id"):
        return 3, "source_product_exact_match"
    if normalize(candidate.get("category")) != normalize(query_product.get("category")):
        return 0, "different_category"
    matched = [
        field
        for field in ("color", "material", "gender")
        if normalize(query_product.get(field))
        and normalize(query_product.get(field)) == normalize(candidate.get(field))
    ]
    if len(matched) >= 2:
        return 2, "same_category+" + "+".join(matched)
    return 1, "same_category" + ("+" + "+".join(matched) if matched else "")


def review_split(
    rows: list[dict[str, Any]],
    products: dict[str, dict[str, str]],
    changed_challenging_query_ids: set[str],
    human_k: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    human = [
        row
        for row in rows
        if str(row["query_id"]) in changed_challenging_query_ids
        and row["challenging_rank"]
        and int(row["challenging_rank"]) <= human_k
    ]
    human.sort(
        key=lambda row: (
            str(row["query_id"]),
            int(row["challenging_rank"]),
            int(row["blind_order"]),
        )
    )
    human_keys = {
        (str(row["query_id"]), str(row["candidate_product_id"]))
        for row in human
    }
    automatic: list[dict[str, Any]] = []
    for row in rows:
        key = (str(row["query_id"]), str(row["candidate_product_id"]))
        if key in human_keys:
            continue
        grade, reason = metadata_rule_grade(
            products.get(str(row["query_product_id"]), {}),
            products.get(str(row["candidate_product_id"]), {}),
        )
        row["relevance_grade"] = grade
        row["review_status"] = "approved"
        row["reviewer_notes"] = f"metadata_rule_v1:{reason}"
        automatic.append(row)
    return human, automatic


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    simple_queries = {row["query_id"]: row for row in read_csv(args.simple_queries)}
    challenging_queries = {row["query_id"]: row for row in read_csv(args.challenging_queries)}
    if simple_queries.keys() != challenging_queries.keys():
        raise ValueError("simple and challenging query IDs differ")
    for query_id in simple_queries:
        if simple_queries[query_id]["source_product_id"] != challenging_queries[query_id]["source_product_id"]:
            raise ValueError(f"source product differs for {query_id}")

    simple = ranked(read_csv(args.simple_results), args.top_k)
    challenging = ranked(read_csv(args.challenging_results), args.top_k)
    known = {
        (row.get("query_id", ""), row.get("relevant_product_id", ""))
        for row in read_csv(args.ground_truth)
    }
    products = {row["product_id"]: row for row in read_csv(args.products)}
    images = image_map(read_csv(args.product_images))

    new_pairs = sorted((set(simple) | set(challenging)) - known)
    rows: list[dict[str, Any]] = []
    for query_id, candidate_id in new_pairs:
        sq = simple_queries[query_id]
        cq = challenging_queries[query_id]
        query_product = products.get(sq["source_product_id"], {})
        candidate = products.get(candidate_id, {})
        candidate_images = images.get(candidate_id, [])
        sr = simple.get((query_id, candidate_id), {})
        cr = challenging.get((query_id, candidate_id), {})
        sources = "+".join(
            name for name, result in (("simple", sr), ("challenging", cr)) if result
        )
        blind_order = int(hashlib.sha256(f"{query_id}|{candidate_id}|paired-pool-v1".encode()).hexdigest()[:8], 16)
        rows.append(
            {
                "query_id": query_id,
                "query_product_id": sq["source_product_id"],
                "query_product_name": query_product.get("product_name", ""),
                "query_category": query_product.get("category", sq.get("category", "")),
                "simple_query_image_url": sq.get("image_url", ""),
                "challenging_query_image_url": cq.get("image_url", ""),
                "candidate_product_id": candidate_id,
                "candidate_product_name": candidate.get("product_name", ""),
                "candidate_category": candidate.get("category", ""),
                "candidate_brand": candidate.get("brand", ""),
                "candidate_color": candidate.get("color", ""),
                "candidate_material": candidate.get("material", ""),
                "candidate_image_url": candidate_images[0] if candidate_images else "",
                "candidate_image_urls": " | ".join(candidate_images),
                "simple_rank": sr.get("rank", ""),
                "simple_score": sr.get("score", ""),
                "challenging_rank": cr.get("rank", ""),
                "challenging_score": cr.get("score", ""),
                "pool_sources": sources,
                "blind_order": blind_order,
                "relevance_grade": "",
                "review_status": "pending",
                "reviewer_notes": "",
            }
        )
    rows.sort(key=lambda row: (row["query_id"], row["blind_order"]))
    return rows


def render_html(
    rows: list[dict[str, Any]],
    output: Path,
    query_ids: list[str] | None = None,
) -> None:
    payload = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    fields = json.dumps(FIELDS, ensure_ascii=False)
    query_ids = sorted(query_ids or {str(row["query_id"]) for row in rows})
    query_options = "".join(
        f'<option value="{html.escape(query_id)}">{html.escape(query_id)}</option>'
        for query_id in query_ids
    )
    document = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Duyệt pool Top-20 Image Search</title><style>
body{{font-family:system-ui,sans-serif;margin:0;background:#f4f6f8;color:#17202a}}header{{position:sticky;top:0;z-index:2;background:#fff;padding:12px 18px;box-shadow:0 2px 8px #0002}}
.controls{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}button,select,input{{padding:7px}}#stats{{font-weight:600;margin-left:auto}}main{{max-width:1500px;margin:auto;padding:14px}}
.guide{{background:#fffbe6;border:1px solid #d8c36d;padding:10px}}.card{{background:#fff;border:1px solid #d8dee4;border-radius:8px;margin:10px 0;padding:12px}}
.meta{{display:flex;gap:14px;flex-wrap:wrap}}.images{{display:grid;grid-template-columns:1fr 1fr 2fr;gap:10px}}img{{width:100%;height:300px;object-fit:contain;background:#eee}}
.candidate-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}}.review{{display:grid;grid-template-columns:140px 140px 1fr;gap:8px;margin-top:9px}}small{{color:#59636e}}@media(max-width:800px){{.images,.review{{grid-template-columns:1fr}}}}
</style></head><body><header><b>Duyệt ứng viên mới trong pooled Top-20</b><div class="controls">
<button id="prev-query" title="Query trước">← Trước</button><select id="query">{query_options}</select><button id="next-query" title="Query sau">Sau →</button><select id="status"><option value="">mọi trạng thái</option><option selected>pending</option><option>approved</option><option>rejected</option></select>
<button id="export">Xuất CSV</button><span id="stats"></span></div></header><main>
<p class="guide"><b>Mỗi query chỉ hiện tối đa 5 ứng viên mới có thứ hạng tốt nhất trong hợp hai run.</b> Chấm độc lập với thứ hạng: 3 = đúng SKU; 2 = rất giống/có thể thay thế; 1 = liên quan yếu; 0 = không liên quan. Hai ảnh query là cùng một sản phẩm. Chỉ chọn approved sau khi xem ảnh query và candidate.</p><div id="cards"></div></main><script>
const rows={payload}; const fields={fields}; const key=r=>r.query_id+'|'+r.candidate_product_id; const storageKey='paired-image-pool-v2|DACN_HK252';
const legacyKeys=['paired-image-pool-v1|'+location.pathname,'paired-image-pool-v1|'+location.pathname.replace('/image/simple/','/image_simple/')];
let saved={{}}; for(const legacyKey of legacyKeys)Object.assign(saved,JSON.parse(localStorage.getItem(legacyKey)||'{{}}'));Object.assign(saved,JSON.parse(localStorage.getItem(storageKey)||'{{}}'));
for(const r of rows)if(saved[key(r)])Object.assign(r,saved[key(r)]);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function persist(r){{saved[key(r)]={{relevance_grade:r.relevance_grade,review_status:r.review_status,reviewer_notes:r.reviewer_notes}};localStorage.setItem(storageKey,JSON.stringify(saved))}}
function render(){{const q=document.querySelector('#query').value.toLowerCase(),s=document.querySelector('#status').value;const visible=rows.filter(r=>(!q||r.query_id.toLowerCase().includes(q))&&(!s||r.review_status===s));
document.querySelector('#stats').textContent=`${{visible.length}}/${{rows.length}} · ${{rows.filter(r=>r.review_status==='approved').length}} approved`;
document.querySelector('#cards').innerHTML=visible.map(r=>`<section class="card" data-key="${{esc(key(r))}}"><div class="meta"><b>${{esc(r.query_id)}}</b><span>query product ${{esc(r.query_product_id)}}</span><span>candidate ${{esc(r.candidate_product_id)}}</span></div>
<div class="images"><div><b>Query detail</b><img loading="lazy" src="${{esc(r.simple_query_image_url)}}"></div><div><b>Query ngoại cảnh/model</b><img loading="lazy" src="${{esc(r.challenging_query_image_url)}}"></div>
<div><b>${{esc(r.candidate_product_name)}}</b><br><small>${{esc(r.candidate_category)}} · ${{esc(r.candidate_color)}} · ${{esc(r.candidate_material)}}</small><div class="candidate-grid">${{r.candidate_image_urls.split(' | ').filter(Boolean).map(u=>`<img loading="lazy" src="${{esc(u)}}">`).join('')}}</div></div></div>
<div class="review"><select class="grade"><option value="">grade?</option>${{[0,1,2,3].map(g=>`<option value="${{g}}" ${{String(r.relevance_grade)===String(g)?'selected':''}}>${{g}}</option>`).join('')}}</select>
<select class="review-status"><option ${{r.review_status==='pending'?'selected':''}}>pending</option><option ${{r.review_status==='approved'?'selected':''}}>approved</option><option ${{r.review_status==='rejected'?'selected':''}}>rejected</option></select><input class="notes" value="${{esc(r.reviewer_notes)}}" placeholder="ghi chú"></div></section>`).join('') || '<p class="guide">Query này không có ứng viên Top-5 mới cần duyệt; toàn bộ cặp đã có nhãn cũ.</p>';
document.querySelectorAll('.card').forEach(c=>{{const r=rows.find(x=>key(x)===c.dataset.key);c.querySelector('.grade').onchange=e=>{{r.relevance_grade=e.target.value;persist(r)}};c.querySelector('.review-status').onchange=e=>{{r.review_status=e.target.value;persist(r);render()}};c.querySelector('.notes').onchange=e=>{{r.reviewer_notes=e.target.value;persist(r)}}}})}}
const csvCell=v=>/[",\\n]/.test(String(v??''))?'"'+String(v??'').replaceAll('"','""')+'"':String(v??'');document.querySelector('#export').onclick=()=>{{const csv=[fields.join(','),...rows.map(r=>fields.map(f=>csvCell(r[f])).join(','))].join('\\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv;charset=utf-8'}}));a.download='paired_top20_pool_reviewed.csv';a.click();URL.revokeObjectURL(a.href)}};
function moveQuery(delta){{const select=document.querySelector('#query');const next=Math.min(Math.max(select.selectedIndex+delta,0),select.options.length-1);select.selectedIndex=next;render()}}
document.querySelector('#prev-query').onclick=()=>moveQuery(-1);document.querySelector('#next-query').onclick=()=>moveQuery(1);
for(const id of ['query','status'])document.querySelector('#'+id).oninput=render;render();</script></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a blind review queue for new pairs in two Top-20 image-search runs.")
    parser.add_argument("--simple-queries", type=Path, default=ROOT / "simple/data/image_queries.csv")
    parser.add_argument("--challenging-queries", type=Path, default=ROOT / "challenging/data/image_queries.csv")
    parser.add_argument("--simple-results", type=Path, default=ROOT / "simple/data/search_results_image_simple.csv")
    parser.add_argument("--challenging-results", type=Path, default=ROOT / "challenging/data/search_results_image_challenging.csv")
    parser.add_argument("--ground-truth", type=Path, default=ROOT / "data/ground_truth_image.csv")
    parser.add_argument("--previous-queries", type=Path, default=ROOT / "data/image_queries.csv")
    parser.add_argument("--products", type=Path, default=ROOT / "data/product_snapshot.csv")
    parser.add_argument("--product-images", type=Path, default=ROOT / "data/product_images.csv")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--human-k", type=int, default=5)
    pooling_dir = SCRIPT_DIR.parent / \
    parser.add_argument("--human-review-csv", type=Path, default=pooling_dir / "paired_top20_pool_human_review_pending.csv")
    parser.add_argument("--auto-rule-csv", type=Path, default=pooling_dir / "paired_top20_pool_auto_rule.csv")
    parser.add_argument("--output-html", type=Path, default=pooling_dir / "paired_top20_pool_review.html")
    parser.add_argument("--summary-csv", type=Path, default=pooling_dir / "paired_top20_pool_summary_by_query.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = build_rows(args)
    write_csv(args.output_csv, rows, FIELDS)
    products = {row["product_id"]: row for row in read_csv(args.products)}
    previous_queries = {row["query_id"]: row for row in read_csv(args.previous_queries)}
    challenging_queries = {row["query_id"]: row for row in read_csv(args.challenging_queries)}
    changed_challenging_query_ids = {
        query_id
        for query_id, query in challenging_queries.items()
        if previous_queries.get(query_id, {}).get("image_url") != query.get("image_url")
    }
    human_rows, automatic_rows = review_split(
        rows,
        products,
        changed_challenging_query_ids,
        args.human_k,
    )
    write_csv(args.human_review_csv, human_rows, FIELDS)
    write_csv(args.auto_rule_csv, automatic_rows, FIELDS)
    render_html(human_rows, args.output_html, sorted(changed_challenging_query_ids))
    grouped = Counter(row["query_id"] for row in rows)
    human_grouped = Counter(row["query_id"] for row in human_rows)
    auto_grouped = Counter(row["query_id"] for row in automatic_rows)
    summary = [
        {
            "query_id": query_id,
            "new_candidates": grouped[query_id],
            "human_review": human_grouped[query_id],
            "auto_rule": auto_grouped[query_id],
        }
        for query_id in sorted(grouped)
    ]
    write_csv(args.summary_csv, summary, ["query_id", "new_candidates", "human_review", "auto_rule"])
    sources = Counter(row["pool_sources"] for row in rows)
    grades = Counter(str(row["relevance_grade"]) for row in automatic_rows)
    print(f"new_pairs={len(rows)} affected_queries={len(grouped)} sources={dict(sources)}")
    print(f"human_review={len(human_rows)} auto_rule={len(automatic_rows)} auto_grades={dict(grades)}")
    print(f"master csv -> {args.output_csv}")
    print(f"human csv -> {args.human_review_csv}")
    print(f"auto csv -> {args.auto_rule_csv}")
    print(f"html -> {args.output_html}")
    print(f"summary -> {args.summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
