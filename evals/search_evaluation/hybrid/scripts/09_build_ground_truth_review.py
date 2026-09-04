from __future__ import annotations

import argparse
import csv
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCE_FIELDS = [
    "query_id", "difficulty", "transformation_type", "source_product_id",
    "source_image_url", "reference_image_url", "image_edit_request",
    "required_reference_color", "required_reference_material",
    "identity_preserved", "requested_change_present", "unintended_change_absent",
    "review_status", "reviewer_notes",
]
CANDIDATE_FIELDS = [
    "query_id", "difficulty", "transformation_type", "reference_image_url",
    "query_text", "candidate_product_id", "candidate_product_name",
    "candidate_category", "candidate_color", "candidate_material", "candidate_usage",
    "candidate_image_urls", "rule_grade", "prior_visual_grade", "prior_visual_source",
    "relevance_grade", "review_status", "reviewer_notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def product_images(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    preference = {"DETAIL_1": 0, "MAIN": 1, "FLAT_1": 2, "MODEL_1": 3}
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("product_id") and row.get("image_url"):
            grouped[row["product_id"]].append(row)
    result: dict[str, list[str]] = {}
    for product_id, images in grouped.items():
        images.sort(key=lambda row: (
            preference.get((row.get("image_type") or "").upper(), 10),
            int(row.get("sort_order") or 999),
        ))
        result[product_id] = list(dict.fromkeys(row["image_url"] for row in images))[:3]
    return result


def build_reference_rows(
    queries: list[dict[str, str]], requirements: list[dict[str, str]]
) -> list[dict[str, Any]]:
    requirement_by_query = {row["query_id"]: row for row in requirements}
    rows: list[dict[str, Any]] = []
    for query in queries:
        requirement = requirement_by_query.get(query["query_id"], {})
        edited = bool(query.get("image_edit_request", "").strip())
        rows.append({
            "query_id": query["query_id"],
            "difficulty": query["difficulty"],
            "transformation_type": query["transformation_type"],
            "source_product_id": query["source_product_id"],
            "source_image_url": query["source_image_url"],
            "reference_image_url": query["image_url"],
            "image_edit_request": query.get("image_edit_request", ""),
            "required_reference_color": requirement.get("required_reference_color", query.get("reference_color", "")),
            "required_reference_material": requirement.get("required_reference_material", query.get("reference_material", "")),
            "identity_preserved": "yes" if not edited else "",
            "requested_change_present": "not_applicable" if not edited else "",
            "unintended_change_absent": "yes" if not edited else "",
            "review_status": "approved" if not edited else "pending",
            "reviewer_notes": "reused_approved_image_evaluation_fixture" if not edited else "",
        })
    return rows


def build_candidate_rows(
    queries: list[dict[str, str]],
    candidates: list[dict[str, str]],
    products: list[dict[str, str]],
    image_ground_truth: list[dict[str, str]],
    product_image_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    query_by_id = {row["query_id"]: row for row in queries}
    product_by_id = {row["product_id"]: row for row in products}
    images_by_product = product_images(product_image_rows)
    prior_by_pair = {
        (row["query_id"], row["relevant_product_id"]): row
        for row in image_ground_truth
        if row.get("review_status") == "approved"
    }
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        query = query_by_id[candidate["query_id"]]
        product_id = candidate["relevant_product_id"]
        product = product_by_id.get(product_id, {})
        is_target = product_id == query["target_product_id"]
        prior = prior_by_pair.get((query["source_image_query_id"], product_id))
        if is_target:
            grade, status, notes = "3", "pending", "approve_after_reference_image_review"
        elif prior is not None:
            grade = prior["relevance_grade"]
            status = "approved"
            notes = f"reused_image_ground_truth:{prior.get('source', '')}:{prior.get('notes', '')}"
        else:
            grade, status, notes = "", "pending", "visual_similarity_review_required"
        rows.append({
            "query_id": query["query_id"],
            "difficulty": query["difficulty"],
            "transformation_type": query["transformation_type"],
            "reference_image_url": query["image_url"],
            "query_text": query["query_text"],
            "candidate_product_id": product_id,
            "candidate_product_name": product.get("product_name", ""),
            "candidate_category": product.get("category", ""),
            "candidate_color": product.get("color", ""),
            "candidate_material": product.get("material", ""),
            "candidate_usage": product.get("usage", ""),
            "candidate_image_urls": " | ".join(images_by_product.get(product_id, [])),
            "rule_grade": candidate.get("relevance_grade", ""),
            "prior_visual_grade": prior.get("relevance_grade", "") if prior else "",
            "prior_visual_source": prior.get("source", "") if prior else "",
            "relevance_grade": grade,
            "review_status": status,
            "reviewer_notes": notes,
        })
    return rows


def render_html(
    reference_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    payload = json.dumps(
        {"references": reference_rows, "candidates": candidate_rows},
        ensure_ascii=False,
    ).replace("</", "<\\/")
    document = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hybrid Ground Truth Review</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#f4f6f8;color:#17202a}}header{{position:sticky;top:0;background:#fff;padding:12px 18px;box-shadow:0 2px 8px #0002;z-index:2}}main{{max-width:1500px;margin:auto;padding:14px}}.card{{background:#fff;border:1px solid #d9e0e6;border-radius:8px;padding:12px;margin:10px 0}}.images{{display:grid;grid-template-columns:repeat(2,minmax(220px,1fr));gap:10px}}img{{width:100%;max-height:360px;object-fit:contain;background:#eee}}.candidate-images{{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}}.review{{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:7px;margin-top:8px}}input,select,button{{padding:7px}}small{{color:#59636e}}.pending{{border-left:5px solid #d33}}.approved{{border-left:5px solid #27944b}}@media(max-width:800px){{.images,.review{{grid-template-columns:1fr}}}}</style></head>
<body><header><b>Hybrid Ground Truth Review</b> <select id="kind"><option value="references">Ảnh tham chiếu</option><option value="candidates">Candidate</option></select> <select id="status"><option value="pending">pending</option><option value="">tất cả</option><option value="approved">approved</option></select> <input id="query" placeholder="query id"> <button id="export">Xuất CSV phần đang xem</button> <span id="stats"></span></header><main><div id="cards"></div></main>
<script>
const data={payload}; const key=r=>r.query_id+'|'+(r.candidate_product_id||'reference');
const storageKey='hybrid-ground-truth-review-v1|'+location.pathname; const saved=JSON.parse(localStorage.getItem(storageKey)||'{{}}');
for(const rows of Object.values(data)) for(const row of rows) if(saved[key(row)]) Object.assign(row,saved[key(row)]);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function persist(r){{saved[key(r)]={{identity_preserved:r.identity_preserved,requested_change_present:r.requested_change_present,unintended_change_absent:r.unintended_change_absent,relevance_grade:r.relevance_grade,review_status:r.review_status,reviewer_notes:r.reviewer_notes}};localStorage.setItem(storageKey,JSON.stringify(saved));}}
function render(){{const kind=document.querySelector('#kind').value,status=document.querySelector('#status').value,q=document.querySelector('#query').value.toLowerCase();const rows=data[kind].filter(r=>(!status||r.review_status===status)&&(!q||r.query_id.toLowerCase().includes(q)));document.querySelector('#stats').textContent=rows.length+'/'+data[kind].length;document.querySelector('#cards').innerHTML=rows.map(r=>kind==='references'?referenceCard(r):candidateCard(r)).join('');document.querySelectorAll('.card').forEach(card=>{{const r=data[kind].find(x=>key(x)===card.dataset.key);card.querySelectorAll('[data-field]').forEach(el=>el.onchange=e=>{{r[e.target.dataset.field]=e.target.value;persist(r);render();}})}})}}
function opts(value,values){{return values.map(v=>`<option value="${{v}}" ${{String(value)===v?'selected':''}}>${{v||'?'}}</option>`).join('')}}
function referenceCard(r){{return `<section class="card ${{esc(r.review_status)}}" data-key="${{esc(key(r))}}"><b>${{esc(r.query_id)}} · ${{esc(r.transformation_type)}} · ${{esc(r.source_product_id)}}</b><br><small>${{esc(r.image_edit_request)}}</small><div class="images"><div>Ảnh nguồn<img src="${{esc(r.source_image_url)}}"></div><div>Ảnh tham chiếu<img src="${{esc(r.reference_image_url)}}"></div></div><div class="review"><select data-field="identity_preserved">${{opts(r.identity_preserved,['','yes','no'])}}</select><select data-field="requested_change_present">${{opts(r.requested_change_present,['','yes','no','not_applicable'])}}</select><select data-field="unintended_change_absent">${{opts(r.unintended_change_absent,['','yes','no'])}}</select><select data-field="review_status">${{opts(r.review_status,['pending','approved','rejected'])}}</select><input data-field="reviewer_notes" value="${{esc(r.reviewer_notes)}}" placeholder="ghi chú"></div></section>`}}
function candidateCard(r){{const imgs=r.candidate_image_urls.split(' | ').filter(Boolean).map(u=>`<img src="${{esc(u)}}">`).join('');return `<section class="card ${{esc(r.review_status)}}" data-key="${{esc(key(r))}}"><b>${{esc(r.query_id)}} · candidate ${{esc(r.candidate_product_id)}} · ${{esc(r.candidate_product_name)}}</b><br><small>${{esc(r.query_text)}} | ${{esc(r.candidate_color)}} | ${{esc(r.candidate_material)}}</small><div class="images"><div>Ảnh query<img src="${{esc(r.reference_image_url)}}"></div><div class="candidate-images">${{imgs}}</div></div><div class="review"><select data-field="relevance_grade">${{opts(String(r.relevance_grade),['','0','1','2','3'])}}</select><select data-field="review_status">${{opts(r.review_status,['pending','approved','rejected'])}}</select><input data-field="reviewer_notes" value="${{esc(r.reviewer_notes)}}" placeholder="ghi chú"></div></section>`}}
function csvCell(v){{const s=String(v??'');return /[",\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s}} document.querySelector('#export').onclick=()=>{{const kind=document.querySelector('#kind').value,rows=data[kind],fields=kind==='references'?{json.dumps(REFERENCE_FIELDS)}:{json.dumps(CANDIDATE_FIELDS)};const csv=[fields.join(','),...rows.map(r=>fields.map(f=>csvCell(r[f])).join(','))].join('\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv;charset=utf-8'}}));a.download='hybrid_'+kind+'_reviewed.csv';a.click();URL.revokeObjectURL(a.href)}};for(const id of ['kind','status','query'])document.querySelector('#'+id).oninput=render;render();
</script></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the auditable Hybrid Search ground-truth review packet.")
    root = SCRIPT_DIR.parent
    parser.add_argument("--queries-csv", type=Path, default=root / "data" / "multimodal_queries.csv")
    parser.add_argument("--requirements-csv", type=Path, default=root / "data" / "reference_image_requirements.csv")
    parser.add_argument("--candidates-csv", type=Path, default=root / "data" / "ground_truth_multimodal_candidates.csv")
    parser.add_argument("--products-csv", type=Path, default=root / "data" / "product_snapshot.csv")
    parser.add_argument("--image-ground-truth-csv", type=Path, default=root.parent / "image" / "data" / "ground_truth_image_paired.csv")
    parser.add_argument("--product-images-csv", type=Path, default=root.parent / "image" / "data" / "product_images.csv")
    parser.add_argument("--reference-review-csv", type=Path, default=root / "reports" / "review" / "hybrid_reference_review.csv")
    parser.add_argument("--candidate-review-csv", type=Path, default=root / "reports" / "review" / "hybrid_candidate_review.csv")
    parser.add_argument("--output-html", type=Path, default=root / "reports" / "review" / "hybrid_ground_truth_review.html")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queries = read_csv(args.queries_csv)
    references = build_reference_rows(queries, read_csv(args.requirements_csv))
    candidates = build_candidate_rows(
        queries, read_csv(args.candidates_csv), read_csv(args.products_csv),
        read_csv(args.image_ground_truth_csv), read_csv(args.product_images_csv),
    )
    write_csv(args.reference_review_csv, REFERENCE_FIELDS, references)
    write_csv(args.candidate_review_csv, CANDIDATE_FIELDS, candidates)
    render_html(references, candidates, args.output_html)
    print(f"references={len(references)} pending={sum(r['review_status']=='pending' for r in references)}")
    print(f"candidates={len(candidates)} pending={sum(r['review_status']=='pending' for r in candidates)}")
    print(f"review_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
