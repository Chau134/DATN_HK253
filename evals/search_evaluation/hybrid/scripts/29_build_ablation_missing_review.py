"""Build one self-contained review page for unjudged Top-5 ablation pairs."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS = {
    "Text-only": ROOT / "data/search_results_text_only_20260905.csv",
    "Image-only": ROOT / "data/search_results_image_only_20260905.csv",
    "Fusion, rerank tắt": ROOT / "data/search_results_fusion_no_rerank_20260905.csv",
    "Image-conditioned, rerank tắt": (
        ROOT / "reports/image_conditioned_20260910/ablation_image_conditioned_no_rerank_current_20260911/candidate_results.csv"
    ),
    "Image-conditioned, rerank bật": (
        ROOT / "reports/image_conditioned_20260910/ablation_image_conditioned_rerank_valid_20260911/candidate_results.csv"
    ),
}
RUN_RANK_FIELDS = {
    "Text-only": "text_only_rank",
    "Image-only": "image_only_rank",
    "Fusion, rerank tắt": "fusion_no_rerank_rank",
    "Image-conditioned, rerank tắt": "image_conditioned_no_rerank_rank",
    "Image-conditioned, rerank bật": "image_conditioned_rerank_rank",
}


def _load_contract():
    path = Path(__file__).with_name("13_compare_ablation.py")
    spec = importlib.util.spec_from_file_location("hybrid_contract", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load constraint contract: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def product_images_from_sql(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"INSERT INTO `product_images` VALUES (.*?);", text, re.S)
    grouped: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    pattern = re.compile(r"\((\d+),(\d+),'([^']*)','([^']*)',(\d+),'[^']*'\)")
    for values in matches:
        for _, product_id, image_type, url, sort_order in pattern.findall(values):
            if url.startswith("http"):
                grouped[product_id].append((image_type.upper(), int(sort_order), url))
    preference = {"DETAIL_1": 0, "MAIN": 1, "FLAT_1": 2, "MODEL_1": 3}
    return {
        product_id: " | ".join(
            url
            for image_type, order, url in sorted(
                values, key=lambda item: (preference.get(item[0], 10), item[1])
            )[:3]
        )
        for product_id, values in grouped.items()
    }


def build_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    contract = _load_contract()
    queries = {row["query_id"]: row for row in read_csv(args.queries)}
    products = {row["product_id"]: row for row in read_csv(args.products)}
    judged = {
        (row["query_id"], row["relevant_product_id"])
        for row in read_csv(args.ground_truth)
        if row.get("review_status") == "approved"
    }
    images = product_images_from_sql(args.product_images_sql)

    ranks: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    for run_name, run_path in DEFAULT_RUNS.items():
        if not run_path.is_file():
            raise FileNotFoundError(f"Missing run for {run_name}: {run_path}")
        for row in read_csv(run_path):
            rank = int(row["rank"])
            if 1 <= rank <= 5:
                ranks[(row["query_id"], row["product_id"])][run_name] = str(rank)

    rows: list[dict[str, str]] = []
    for (query_id, product_id), run_ranks in sorted(ranks.items()):
        if (query_id, product_id) in judged:
            continue
        query = queries[query_id]
        product = products.get(product_id, {})
        checks = contract.requested_constraint_results(query, product or None)
        violations = [field for field, passed in checks.items() if not passed]
        rows.append({
            "query_id": query_id,
            "query_text": query.get("query_text", ""),
            "image_url": query.get("image_url", ""),
            "transformation_type": query.get("transformation_type", ""),
            "difficulty": query.get("difficulty", ""),
            "target_product_id": query.get("target_product_id", ""),
            "product_id": product_id,
            "top5_runs": " | ".join(
                f"{name}: #{run_ranks[name]}" for name in DEFAULT_RUNS if name in run_ranks
            ),
            **{field: run_ranks.get(name, "") for name, field in RUN_RANK_FIELDS.items()},
            "product_name": product.get("product_name", ""),
            "product_category": product.get("category", ""),
            "product_color": product.get("color", ""),
            "product_material": product.get("material", ""),
            "product_usage": product.get("usage", ""),
            "product_price": product.get("price", ""),
            "candidate_image_urls": images.get(product_id, ""),
            "requested_category": query.get("category", ""),
            "requested_color": query.get("color", ""),
            "requested_material": query.get("material", ""),
            "requested_usage": query.get("usage", ""),
            "requested_price_bucket": query.get("price_bucket", ""),
            "manual_relevance_grade": "",
            "manual_constraint_status": "fail" if violations else "pass",
            "manual_violation_fields": ",".join(violations),
            "reviewer": "",
            "reviewed_at": "",
            "review_notes": "",
        })
    return rows


def build_page(rows: list[dict[str, str]], export_name: str) -> str:
    fields = list(rows[0]) if rows else []
    payload = json.dumps({"fields": fields, "rows": rows}, ensure_ascii=False).replace("</", "<\\/")
    export_json = json.dumps(export_name, ensure_ascii=False)
    return f'''<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hybrid ablation – review nhãn NDCG Top-5 còn thiếu</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f4f6fa;color:#182033;font:14px Segoe UI,Arial,sans-serif}}
header{{position:sticky;top:0;z-index:5;padding:14px 20px;background:#17233b;color:white}}h1{{font-size:20px;margin:0 0 5px}}
.bar{{position:sticky;top:70px;z-index:4;display:flex;gap:8px;align-items:center;padding:10px 20px;background:white;border-bottom:1px solid #dce2ec}}
input,select,button{{padding:7px;border:1px solid #b9c4d5;border-radius:5px;font:inherit}}button{{color:white;background:#1769d2;border-color:#1769d2;font-weight:600;cursor:pointer}}
.stats{{margin-left:auto;font-weight:600}}.note{{margin:12px 20px;padding:10px;background:#fff8db;border:1px solid #ead280;border-radius:6px}}
.card{{margin:12px 20px;padding:14px;background:white;border:1px solid #dce2ec;border-radius:8px;box-shadow:0 1px 3px #0001}}
.head{{display:flex;gap:10px;justify-content:space-between}}.qid{{font-weight:700;color:#174f9e}}.runs{{font-weight:700;color:#8a4b08;text-align:right}}
.query{{font-size:16px;font-weight:650;margin:8px 0}}.cols{{display:grid;grid-template-columns:300px minmax(300px,1fr);gap:14px}}
.images{{display:flex;gap:5px;align-items:flex-start;overflow:auto}}img{{width:135px;height:175px;object-fit:contain;background:#f1f3f6;border:1px solid #dce2ec}}
.reference img{{width:180px;height:230px}}.meta{{line-height:1.55}}.requested{{padding:8px;background:#eef5ff;border-radius:5px;margin-bottom:8px}}
.constraint{{margin-top:6px;padding:6px;border-radius:4px;font-weight:600}}.pass{{background:#e9f8ed;color:#176b2c}}.fail{{background:#fff0f0;color:#a12626}}
.review{{display:flex;gap:10px;align-items:center;margin-top:10px;padding-top:10px;border-top:1px solid #e3e7ee}}.review select{{width:180px;font-weight:700}}.review input{{flex:1}}
.graded{{border-left:5px solid #238636}}@media(max-width:800px){{.cols{{grid-template-columns:1fr}}.bar{{top:88px;flex-wrap:wrap}}.stats{{margin-left:0}}}}
</style></head><body>
<header><h1>Review nhãn NDCG cho Top-5 còn thiếu</h1><div>Hợp không trùng của đúng 5 cấu hình Bảng 20; chỉ gồm cặp chưa có trong Ground Truth v2.</div></header>
<div class="bar"><input id="search" size="28" placeholder="Tìm query hoặc sản phẩm"><select id="state"><option value="">Tất cả</option><option value="missing">Chưa chấm</option><option value="graded">Đã chấm</option></select><button id="prev" type="button">← Trước</button><button id="next" type="button">Sau →</button><span id="pageInfo"></span><button id="download" type="button">Tải CSV</button><span id="stats" class="stats"></span></div>
<div class="note"><b>Bạn chỉ cần chọn NDCG grade 0–3.</b> 3 = rất phù hợp cả ảnh và yêu cầu mới; 2 = phù hợp rõ, khác biệt nhỏ; 1 = chỉ liên quan một phần; 0 = không phù hợp hoặc vi phạm yêu cầu chính. Với danh sách mục đích sử dụng thông thường, candidate đạt <b>một mục bất kỳ (ANY)</b> là đạt; chỉ dùng ALL khi truy vấn nói rõ “tất cả”, “cả ba” hoặc “đồng thời”. Trạng thái ràng buộc bên dưới đã được evaluator request-scoped tự động điền.</div>
<main id="cards"></main>
<script>
const INITIAL={payload};const KEY='hybrid-ablation-five-way-missing-ndcg-v2';
let rows=structuredClone(INITIAL.rows);try{{const s=JSON.parse(localStorage.getItem(KEY));if(Array.isArray(s)&&s.length===rows.length)rows=s}}catch(e){{}}
let page=0;const PAGE_SIZE=20;const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function render(){{const q=document.getElementById('search').value.toLowerCase(),state=document.getElementById('state').value;const matched=rows.map((r,i)=>({{r,i}})).filter(({{r}})=>{{const graded=r.manual_relevance_grade!=='';if(state==='missing'&&graded)return false;if(state==='graded'&&!graded)return false;return !q||JSON.stringify(r).toLowerCase().includes(q)}});const pages=Math.max(1,Math.ceil(matched.length/PAGE_SIZE));page=Math.min(page,pages-1);const visible=matched.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE);const out=[];
visible.forEach(({{r,i}})=>{{const graded=r.manual_relevance_grade!=='';const requested=[r.requested_category,r.requested_color,r.requested_material,r.requested_usage,r.requested_price_bucket].filter(Boolean).join(' · ');const imgs=(r.candidate_image_urls||'').split(' | ').filter(Boolean).map(u=>`<a href="${{esc(u)}}" target="_blank"><img loading="lazy" src="${{esc(u)}}"></a>`).join('');const opts=['','0','1','2','3'].map(x=>`<option value="${{x}}" ${{r.manual_relevance_grade===x?'selected':''}}>${{x||'— chọn grade —'}}</option>`).join('');const constraint=r.manual_constraint_status==='pass'?'Đạt ràng buộc request-scoped':`Không đạt: ${{esc(r.manual_violation_fields)}}`;
out.push(`<section class="card ${{graded?'graded':''}}"><div class="head"><span class="qid">${{esc(r.query_id)}} · candidate ${{esc(r.product_id)}}</span><span class="runs">${{esc(r.top5_runs)}}</span></div><div class="query">${{esc(r.query_text)}}</div><div class="cols"><div class="reference"><b>Ảnh tham chiếu</b><br><a href="${{esc(r.image_url)}}" target="_blank"><img loading="lazy" src="${{esc(r.image_url)}}"></a></div><div><b>Ảnh candidate</b><div class="images">${{imgs||'Không có URL ảnh'}}</div><div class="meta"><div class="requested"><b>Yêu cầu fixture:</b> ${{esc(requested||'không có')}}</div><b>${{esc(r.product_name)}}</b><br>Loại: ${{esc(r.product_category)}} · Màu: ${{esc(r.product_color)}}<br>Chất liệu: ${{esc(r.product_material)}}<br>Mục đích: ${{esc(r.product_usage)}} · Giá: ${{esc(r.product_price)}}<div class="constraint ${{r.manual_constraint_status}}">${{constraint}}</div></div></div></div><div class="review"><b>NDCG grade</b><select data-i="${{i}}">${{opts}}</select><input data-i="${{i}}" data-note="1" value="${{esc(r.review_notes)}}" placeholder="Ghi chú (không bắt buộc)"></div></section>`);}});document.getElementById('cards').innerHTML=out.join('');const done=rows.filter(r=>r.manual_relevance_grade!=='').length;document.getElementById('stats').textContent=`Lọc ${{matched.length}}/${{rows.length}} · Đã chấm ${{done}} · Còn ${{rows.length-done}}`;document.getElementById('pageInfo').textContent=`Trang ${{page+1}}/${{pages}}`;document.getElementById('prev').disabled=page===0;document.getElementById('next').disabled=page>=pages-1;}}
document.getElementById('cards').addEventListener('change',e=>{{if(e.target.dataset.i===undefined)return;const r=rows[Number(e.target.dataset.i)];if(e.target.dataset.note)r.review_notes=e.target.value;else{{r.manual_relevance_grade=e.target.value;if(e.target.value){{r.reviewer=r.reviewer||'user_review';r.reviewed_at=r.reviewed_at||new Date().toISOString()}}}}localStorage.setItem(KEY,JSON.stringify(rows));render()}});document.getElementById('cards').addEventListener('input',e=>{{if(e.target.dataset.note){{rows[Number(e.target.dataset.i)].review_notes=e.target.value;localStorage.setItem(KEY,JSON.stringify(rows))}}}});['search','state'].forEach(id=>document.getElementById(id).addEventListener('input',()=>{{page=0;render()}}));document.getElementById('prev').onclick=()=>{{if(page>0){{page--;render();scrollTo(0,0)}}}};document.getElementById('next').onclick=()=>{{page++;render();scrollTo(0,0)}};
const cell=v=>'"'+String(v??'').replace(/"/g,'""')+'"';document.getElementById('download').onclick=()=>{{const csv=[INITIAL.fields,...rows.map(r=>INITIAL.fields.map(f=>r[f]??''))].map(x=>x.map(cell).join(',')).join('\\r\\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([new TextEncoder().encode('\ufeff'+csv)],{{type:'text/csv;charset=utf-8'}}));a.download={export_json};a.click();URL.revokeObjectURL(a.href)}};render();
</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--output-html", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--queries", type=Path, default=ROOT / "data/multimodal_queries.csv")
    parser.add_argument("--products", type=Path, default=ROOT / "data/product_snapshot.csv")
    parser.add_argument("--product-images-sql", type=Path, default=ROOT.parents[2] / "database/1000_final.sql")
    parser.add_argument("--export-name", default="hybrid_ablation_five_way_missing_reviewed_v2.csv")
    args = parser.parse_args()
    rows = build_rows(args)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(build_page(rows, args.export_name), encoding="utf-8")
    by_run = {
        name: sum(bool(row[field]) for row in rows)
        for name, field in RUN_RANK_FIELDS.items()
    }
    print(json.dumps({
        "rows": len(rows),
        "unjudged_top5_by_run": by_run,
        "constraint_status": {
            status: sum(row["manual_constraint_status"] == status for row in rows)
            for status in ("pass", "fail")
        },
        "html": str(args.output_html),
        "csv": str(args.output_csv),
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
