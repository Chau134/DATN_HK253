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
    "query_text", "required_category", "required_color", "required_material",
    "required_price_bucket", "required_usage", "candidate_product_id",
    "candidate_product_name", "candidate_category", "candidate_color",
    "candidate_material", "candidate_price", "candidate_usage",
    "candidate_image_urls", "hard_constraints_satisfied", "visual_similarity",
    "relevance_grade", "confidence", "review_status", "reviewer_notes",
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
            # Every reference must be reviewed in this Hybrid evaluation. Do not
            # pre-approve reused images in the fully manual review protocol.
            "identity_preserved": "",
            "requested_change_present": "",
            "unintended_change_absent": "",
            "review_status": "pending",
            "reviewer_notes": "",
        })
    return rows


def build_candidate_rows(
    queries: list[dict[str, str]],
    candidates: list[dict[str, str]],
    products: list[dict[str, str]],
    product_image_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    query_by_id = {row["query_id"]: row for row in queries}
    product_by_id = {row["product_id"]: row for row in products}
    images_by_product = product_images(product_image_rows)
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        query = query_by_id[candidate["query_id"]]
        product_id = candidate["relevant_product_id"]
        product = product_by_id.get(product_id, {})
        rows.append({
            "query_id": query["query_id"],
            "difficulty": query["difficulty"],
            "transformation_type": query["transformation_type"],
            "reference_image_url": query["image_url"],
            "query_text": query["query_text"],
            "required_category": query.get("category", ""),
            "required_color": query.get("color", ""),
            "required_material": query.get("material", ""),
            "required_price_bucket": query.get("price_bucket", ""),
            "required_usage": query.get("usage", ""),
            "candidate_product_id": product_id,
            "candidate_product_name": product.get("product_name", ""),
            "candidate_category": product.get("category", ""),
            "candidate_color": product.get("color", ""),
            "candidate_material": product.get("material", ""),
            "candidate_price": product.get("price", ""),
            "candidate_usage": product.get("usage", ""),
            "candidate_image_urls": " | ".join(images_by_product.get(product_id, [])),
            "hard_constraints_satisfied": "",
            "visual_similarity": "",
            "relevance_grade": "",
            "confidence": "",
            "review_status": "pending",
            "reviewer_notes": "",
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
const storageKey='hybrid-ground-truth-reference-manual-v3|'+location.pathname; const saved=JSON.parse(localStorage.getItem(storageKey)||'{{}}');
for(const rows of Object.values(data)) for(const row of rows) if(saved[key(row)]) Object.assign(row,saved[key(row)]);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function persist(r){{saved[key(r)]={{identity_preserved:r.identity_preserved,requested_change_present:r.requested_change_present,unintended_change_absent:r.unintended_change_absent,relevance_grade:r.relevance_grade,review_status:r.review_status,reviewer_notes:r.reviewer_notes}};localStorage.setItem(storageKey,JSON.stringify(saved));}}
function render(){{const kind=document.querySelector('#kind').value,status=document.querySelector('#status').value,q=document.querySelector('#query').value.toLowerCase();const rows=data[kind].filter(r=>(!status||r.review_status===status)&&(!q||r.query_id.toLowerCase().includes(q)));document.querySelector('#stats').textContent=rows.length+'/'+data[kind].length;document.querySelector('#cards').innerHTML=rows.map(r=>kind==='references'?referenceCard(r):candidateCard(r)).join('');document.querySelectorAll('.card').forEach(card=>{{const r=data[kind].find(x=>key(x)===card.dataset.key);card.querySelectorAll('[data-field]').forEach(el=>el.onchange=e=>{{r[e.target.dataset.field]=e.target.value;persist(r);render();}})}})}}
function opts(value,values){{return values.map(v=>`<option value="${{v}}" ${{String(value)===v?'selected':''}}>${{v||'?'}}</option>`).join('')}}
function referenceCard(r){{return `<section class="card ${{esc(r.review_status)}}" data-key="${{esc(key(r))}}"><b>${{esc(r.query_id)}} · ${{esc(r.transformation_type)}} · ${{esc(r.source_product_id)}}</b><br><small>${{esc(r.image_edit_request)}}</small><div class="images"><div>Ảnh nguồn<img src="${{esc(r.source_image_url)}}"></div><div>Ảnh tham chiếu<img src="${{esc(r.reference_image_url)}}"></div></div><div class="review"><select data-field="identity_preserved">${{opts(r.identity_preserved,['','yes','no'])}}</select><select data-field="requested_change_present">${{opts(r.requested_change_present,['','yes','no','not_applicable'])}}</select><select data-field="unintended_change_absent">${{opts(r.unintended_change_absent,['','yes','no'])}}</select><select data-field="review_status">${{opts(r.review_status,['pending','approved','rejected'])}}</select><input data-field="reviewer_notes" value="${{esc(r.reviewer_notes)}}" placeholder="ghi chú"></div></section>`}}
function candidateCard(r){{const imgs=r.candidate_image_urls.split(' | ').filter(Boolean).map(u=>`<img src="${{esc(u)}}">`).join('');return `<section class="card ${{esc(r.review_status)}}" data-key="${{esc(key(r))}}"><b>${{esc(r.query_id)}} · candidate ${{esc(r.candidate_product_id)}} · ${{esc(r.candidate_product_name)}}</b><br><small>${{esc(r.query_text)}} | ${{esc(r.candidate_color)}} | ${{esc(r.candidate_material)}}</small><div class="images"><div>Ảnh query<img src="${{esc(r.reference_image_url)}}"></div><div class="candidate-images">${{imgs}}</div></div><div class="review"><select data-field="relevance_grade">${{opts(String(r.relevance_grade),['','0','1','2','3'])}}</select><select data-field="review_status">${{opts(r.review_status,['pending','approved','rejected'])}}</select><input data-field="reviewer_notes" value="${{esc(r.reviewer_notes)}}" placeholder="ghi chú"></div></section>`}}
function csvCell(v){{const s=String(v??'');return /[",\\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s}} document.querySelector('#export').onclick=()=>{{const kind=document.querySelector('#kind').value,rows=data[kind],fields=kind==='references'?{json.dumps(REFERENCE_FIELDS)}:{json.dumps(CANDIDATE_FIELDS)};const csv=[fields.join(','),...rows.map(r=>fields.map(f=>csvCell(r[f])).join(','))].join('\\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv;charset=utf-8'}}));a.download='hybrid_'+kind+'_reviewed.csv';a.click();URL.revokeObjectURL(a.href)}};for(const id of ['kind','status','query'])document.querySelector('#'+id).oninput=render;render();
</script></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def _render_manual_candidate_html_broken_encoding(
    reference_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    payload = json.dumps(
        {"references": reference_rows, "candidates": candidate_rows},
        ensure_ascii=False,
    ).replace("</", "<\\/")
    document = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Du�t tay Ground Truth Hybrid</title><style>
body{font-family:system-ui,sans-serif;margin:0;background:#f4f6f8;color:#17202a}header{position:sticky;top:0;background:#fff;padding:12px 18px;box-shadow:0 2px 8px #0002;z-index:2}.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}main{max-width:1500px;margin:auto;padding:14px}.guide,.card{background:#fff;border:1px solid #d9e0e6;border-radius:8px;padding:14px;margin:10px 0}.guide{border-left:5px solid #2463a7}.guide li{margin:6px 0}.card{border-left:5px solid #d33}.card.approved{border-left-color:#27944b}.images{display:grid;grid-template-columns:minmax(280px,.8fr) minmax(500px,1.2fr);gap:10px;margin-top:10px}img{width:100%;height:360px;object-fit:contain;background:#eee}.candidate-images{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.constraints,.metadata{padding:10px;background:#f6f8fa;border-radius:6px;margin-top:8px;line-height:1.55}.constraints{background:#fff6d9}.review{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:8px;margin-top:10px}label{font-size:13px;font-weight:600}label select,label input{display:block;width:100%;box-sizing:border-box;margin-top:4px}input,select,button{padding:8px}.notes{grid-column:1/-1}.pager{display:flex;justify-content:center;align-items:center;gap:10px;margin:14px}@media(max-width:900px){.images,.review{grid-template-columns:1fr}.notes{grid-column:auto}}
</style></head><body>
<header><div class="toolbar"><b>Du�t tay Ground Truth Hybrid</b><select id="kind"><option value="candidates">654 candidate</option><option value="references">100>�nh tham ch�u</option></select><select id="status"><option value="pending">Ci�a du�t</option><option value="">T�t �</option><option value="approved">� duy�t</option></select><input id="query" placeholder="query id"><select id="pageSize"><option>10</option><option>20</option><option>50</option></select><button id="export">Xu�t to�n b� CSV</button><span id="stats"></span></div></header>
<main><section class="guide"><b>Quy ~�c c~�m candidate</b><ol>
<li>So �nh tham chi�u ~�i ba>�nh candidate � �nh gi� k�u d�ng, phom, h�a t�t v�!�c �m t~� gi�c. ^� qua th�c t�nh m� c�u truy ~�n y�u c�u �i.</li>
<li>�i ch�u candidate v�i ~�t � r�ng b�c b�t b�c trong � m�u v�ng. Ts��ng <4 kh�ng ph�i r�ng b�c.</li>
<li><b>Grade 3:</b> th�a �i r�ng b�c v� g�n ni�!�ng �n ph�m/k�u d�ng. <b>Grade 2:</b> t~�a m�i r�ng b�c v� u��ng ~�!� ~�t. <b>Grade 1:</b> c� li�n quan ni�ng t��ng t� y�u h�c sai �t n~�t m�t r�ng b�c. <b>Grade 0:</b> sai lo�i �n ph�m h�c kh�ng li�n quan.</li>
<li>N�u <b>T~�a to�n ~� r�ng b�c = no</b>, grade ~�i!a l� 1. Grade 23 b�t b�c gi� t~� n�y l� yes.</li>
<li>C~�n <b>approved</b>!� x�c n~�n!� c~�m, k� c� grade 0. C~� c~�n <b>rejected</b> ~�u>�nh/d� l�u ~�ng khi�n kh�ng t~� ch�m v� p~�i ghi ch�.</li>
</ol><b>Ti�n � m�u trong tr�nh du�t. H�y X�t to�n ~� CSV sau �i phi�n.</b></section><div id="cards"></div><div class="pager"><button id="prev">Trang ts��c</button><span id="pageInfo"></span><button id="next">Trang sau</button></div></main>
<script>
const data=__PAYLOAD__,candidateFields=__CANDIDATE_FIELDS__,referenceFields=__REFERENCE_FIELDS__;
const key=r=>r.query_id+'|'+(r.candidate_product_id||'reference');let page=0;
const storageKey='hybrid-ground-truth-candidate-manual-v1|'+location.pathname;
const saved=JSON.parse(localStorage.getItem(storageKey)||'{}');
for(const rows of Object.values(data))for(const row of rows)if(saved[key(row)])Object.assign(row,saved[key(row)]);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const value=v=>esc(v||'');
function opts(current,values){return values.map(v=>'<option value="'+v+'" '+(String(current??'')===v?'selected':'')+'>'+(v||' ch�n ')+'</option>').join('')}
function persist(r){saved[key(r)]={hard_constraints_satisfied:r.hard_constraints_satisfied,visual_similarity:r.visual_similarity,relevance_grade:r.relevance_grade,confidence:r.confidence,review_status:r.review_status,reviewer_notes:r.reviewer_notes};localStorage.setItem(storageKey,JSON.stringify(saved))}
function referenceCard(r){return '<section class="card '+esc(r.review_status)+'"><b>'+esc(r.query_id)+' � '+esc(r.transformation_type)+'</b><div class="images"><div>�nh ngu�n<img loading="lazy" src="'+esc(r.source_image_url)+'"></div><div>�nh tham ch�u<img loading="lazy" src="'+esc(r.reference_image_url)+'"></div></div></section>'}
function candidateCard(r){const imgs=(r.candidate_image_urls||'').split(' | ').filter(Boolean).map(u=>'<img loading="lazy" src="'+esc(u)+'">').join('');return '<section class="card '+esc(r.review_status)+'" data-key="'+esc(key(r))+'"><b>'+esc(r.query_id)+' � candidate '+esc(r.candidate_product_id)+' � '+esc(r.candidate_product_name)+'</b><div class="metadata"><b>C�u truy ~�n:</b> '+esc(r.query_text)+'</div><div class="constraints"><b>R�ng bu�c ~�t bu�c:</b> category='+value(r.required_category)+'; color='+value(r.required_color)+'; material='+value(r.required_material)+'; price='+value(r.required_price_bucket)+'; usage='+value(r.required_usage)+'</div><div class="metadata"><b>Candidate:</b> category='+value(r.candidate_category)+'; color='+value(r.candidate_color)+'; material='+value(r.candidate_material)+'; price='+value(r.candidate_price)+'; usage='+value(r.candidate_usage)+'</div><div class="images"><div>�nh tham ch�u<img loading="lazy" src="'+esc(r.reference_image_url)+'"></div><div class="candidate-images">'+(imgs||'<b>Kh�ng c�>�nh candidate</b>')+'</div></div><div class="review"><label>T~�a to�n ~� r�ng b�c<select data-field="hard_constraints_satisfied">'+opts(r.hard_constraints_satisfied,['','yes','no'])+'</select></label><label>� u��ng ~� t~� gi�c<select data-field="visual_similarity">'+opts(r.visual_similarity,['','0','1','2','3'])+'</select></label><label>Relevance grade<select data-field="relevance_grade">'+opts(r.relevance_grade,['','0','1','2','3'])+'</select></label><label?� tin �y<select data-field="confidence">'+opts(r.confidence,['','high','medium','low'])+'</select></label><label>T~�ng th�i<select data-field="review_status">'+opts(r.review_status,['pending','approved','rejected'])+'</select></label><label class="notes">Ghi ch�<input data-field="reviewer_notes" value="'+esc(r.reviewer_notes)+'" placeholder="^�t bu�c ~�u rejected/low confidence"></label></div></section>'}
function filtered(){const kind=document.querySelector('#kind').value,status=document.querySelector('#status').value,q=document.querySelector('#query').value.toLowerCase();return data[kind].filter(r=>(!status||r.review_status===status)&&(!q||r.query_id.toLowerCase().includes(q)))}
function render(){const kind=document.querySelector('#kind').value,rows=filtered(),size=Number(document.querySelector('#pageSize').value),pages=Math.max(1,Math.ceil(rows.length/size));page=Math.min(page,pages-1);const shown=rows.slice(page*size,(page+1)*size);document.querySelector('#stats').textContent=rows.length+'!ang ~�c / '+data[kind].length+' ~�ng';document.querySelector('#pageInfo').textContent='Trang '+(page+1)+'/'+pages;document.querySelector('#cards').innerHTML=shown.map(r=>kind==='references'?referenceCard(r):candidateCard(r)).join('');document.querySelectorAll('.card[data-key]').forEach(card=>{const r=data[kind].find(x=>key(x)===card.dataset.key);card.querySelectorAll('[data-field]').forEach(el=>el.onchange=e=>{r[e.target.dataset.field]=e.target.value;persist(r);render()})})}
function csvCell(v){const s=String(v??'');return /[",\\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s}
document.querySelector('#export').onclick=()=>{const kind=document.querySelector('#kind').value,rows=data[kind],fields=kind==='references'?referenceFields:candidateFields,csv=[fields.join(','),...rows.map(r=>fields.map(f=>csvCell(r[f])).join(','))].join('\\n'),a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.download=kind==='candidates'?'hybrid_candidate_review.csv':'hybrid_reference_review.csv';a.click();URL.revokeObjectURL(a.href)};
document.querySelector('#prev').onclick=()=>{page=Math.max(0,page-1);render()};document.querySelector('#next').onclick=()=>{page++;render()};for(const id of ['kind','status','query','pageSize'])document.querySelector('#'+id).oninput=()=>{page=0;render()};render();
</script></body></html>"""
    document = (
        document.replace("__PAYLOAD__", payload)
        .replace("__CANDIDATE_FIELDS__", json.dumps(CANDIDATE_FIELDS))
        .replace("__REFERENCE_FIELDS__", json.dumps(REFERENCE_FIELDS))
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def render_manual_candidate_html(
    reference_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    payload = json.dumps(
        {"references": reference_rows, "candidates": candidate_rows},
        ensure_ascii=False,
    ).replace("</", "<\\/")
    document = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Duyet tay Ground Truth Hybrid</title><style>
body{font-family:system-ui,sans-serif;margin:0;background:#f4f6f8;color:#17202a}header{position:sticky;top:0;background:#fff;padding:12px 18px;box-shadow:0 2px 8px #0002;z-index:2}.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}main{max-width:1500px;margin:auto;padding:14px}.guide,.card{background:#fff;border:1px solid #d9e0e6;border-radius:8px;padding:14px;margin:10px 0}.guide{border-left:5px solid #2463a7}.guide li{margin:6px 0}.card{border-left:5px solid #d33}.card.approved{border-left-color:#27944b}.images{display:grid;grid-template-columns:minmax(280px,.8fr) minmax(500px,1.2fr);gap:10px;margin-top:10px}img{width:100%;height:360px;object-fit:contain;background:#eee}.candidate-images{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.constraints,.metadata{padding:10px;background:#f6f8fa;border-radius:6px;margin-top:8px;line-height:1.55}.constraints{background:#fff6d9}.review{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:8px;margin-top:10px}label{font-size:13px;font-weight:600}label select,label input{display:block;width:100%;box-sizing:border-box;margin-top:4px}input,select,button{padding:8px}.notes{grid-column:1/-1}.pager{display:flex;justify-content:center;align-items:center;gap:10px;margin:14px}@media(max-width:900px){.images,.review{grid-template-columns:1fr}.notes{grid-column:auto}}
</style></head><body><header><div class="toolbar"><b>Duyet tay Ground Truth Hybrid</b><select id="kind"><option value="candidates">654 candidate</option><option value="references">100 anh tham chieu</option></select><select id="status"><option value="pending">Chua duyet</option><option value="">Tat ca</option><option value="approved">Da duyet</option></select><input id="query" placeholder="query id"><select id="pageSize"><option>10</option><option>20</option><option>50</option></select><button id="export">Xuat toan bo CSV</button><span id="stats"></span><b id="saveState">Dang khoi tao...</b></div></header>
<main><section class="guide"><b>QUY TAC CHAM CANDIDATE</b><ol>
<li>So sanh anh tham chieu voi 3 anh candidate ve kieu dang, phom, hoa tiet va dac diem thi giac. Bo qua thuoc tinh ma cau truy van yeu cau thay doi.</li>
<li>Doi chieu candidate voi moi rang buoc trong o mau vang. Truong "-" khong phai rang buoc.</li>
<li>Category, color, material va usage phai khop metadata hien thi (bo qua hoa/thuong va dau cau). Price: 200k_500k = [200.000, 500.000); 500k_1m = [500.000, 1.000.000); 1m_2m = [1.000.000, 2.000.000).</li>
<li><b>Grade 3:</b> thoa moi rang buoc va gan nhu dung san pham/kieu dang. <b>Grade 2:</b> thoa moi rang buoc va tuong tu du tot. <b>Grade 1:</b> co lien quan nhung tuong tu yeu, hoac sai it nhat 1 rang buoc. <b>Grade 0:</b> sai loai san pham/khong lien quan.</li>
<li>Hard constraints = no thi grade toi da la 1. Grade 2-3 bat buoc Hard constraints = yes.</li>
<li>Chon approved de xac nhan nhan da cham, ke ca grade 0. Chi chon rejected khi anh/du lieu hong khong the cham; bat buoc ghi chu.</li>
</ol><b>Tien do luu trong trinh duyet. Hay Xuat toan bo CSV sau moi phien.</b></section><div id="cards"></div><div class="pager"><button id="prev">Trang truoc</button><span id="pageInfo"></span><button id="next">Trang sau</button></div></main>
<script>
const data=__PAYLOAD__,candidateFields=__CANDIDATE_FIELDS__,referenceFields=__REFERENCE_FIELDS__;
const key=r=>r.query_id+'|'+(r.candidate_product_id||'reference');let page=0;
const storageKey='hybrid-ground-truth-candidate-manual-v2|'+location.pathname,saved=JSON.parse(localStorage.getItem(storageKey)||'{}');
for(const rows of Object.values(data))for(const row of rows)if(saved[key(row)])Object.assign(row,saved[key(row)]);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),value=v=>esc(v||'-');
function opts(cur,vals){return vals.map(v=>'<option value="'+v+'" '+(String(cur??'')===v?'selected':'')+'>'+(v||'-- chon --')+'</option>').join('')}
function reviewState(r){return {query_id:r.query_id,candidate_product_id:r.candidate_product_id,hard_constraints_satisfied:r.hard_constraints_satisfied,visual_similarity:r.visual_similarity,relevance_grade:r.relevance_grade,confidence:r.confidence,review_status:r.review_status,reviewer_notes:r.reviewer_notes}}
function persist(r){saved[key(r)]=reviewState(r);localStorage.setItem(storageKey,JSON.stringify(saved));const state=document.querySelector('#saveState');state.textContent='Dang luu CSV...';fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(reviewState(r))}).then(x=>{if(!x.ok)throw Error();state.textContent='Da luu vao CSV'}).catch(()=>state.textContent='Chi luu trong trinh duyet')}
function referenceCard(r){return '<section class="card '+esc(r.review_status)+'"><b>'+esc(r.query_id)+' | '+esc(r.transformation_type)+'</b><div class="images"><div>Anh nguon<img loading="lazy" src="'+esc(r.source_image_url)+'"></div><div>Anh tham chieu<img loading="lazy" src="'+esc(r.reference_image_url)+'"></div></div></section>'}
function candidateCard(r){const imgs=(r.candidate_image_urls||'').split(' | ').filter(Boolean).map(u=>'<img loading="lazy" src="'+esc(u)+'">').join('');return '<section class="card '+esc(r.review_status)+'" data-key="'+esc(key(r))+'"><b>'+esc(r.query_id)+' | candidate '+esc(r.candidate_product_id)+' | '+esc(r.candidate_product_name)+'</b><div class="metadata"><b>Cau truy van:</b> '+esc(r.query_text)+'</div><div class="constraints"><b>Rang buoc:</b> category='+value(r.required_category)+'; color='+value(r.required_color)+'; material='+value(r.required_material)+'; price='+value(r.required_price_bucket)+'; usage='+value(r.required_usage)+'</div><div class="metadata"><b>Candidate:</b> category='+value(r.candidate_category)+'; color='+value(r.candidate_color)+'; material='+value(r.candidate_material)+'; price='+value(r.candidate_price)+'; usage='+value(r.candidate_usage)+'</div><div class="images"><div>Anh tham chieu<img loading="lazy" src="'+esc(r.reference_image_url)+'"></div><div class="candidate-images">'+(imgs||'<b>Khong co anh candidate</b>')+'</div></div><div class="review"><label>Thoa toan bo rang buoc<select data-field="hard_constraints_satisfied">'+opts(r.hard_constraints_satisfied,['','yes','no'])+'</select></label><label>Tuong tu thi giac<select data-field="visual_similarity">'+opts(r.visual_similarity,['','0','1','2','3'])+'</select></label><label>Relevance grade<select data-field="relevance_grade">'+opts(r.relevance_grade,['','0','1','2','3'])+'</select></label><label>Do tin cay<select data-field="confidence">'+opts(r.confidence,['','high','medium','low'])+'</select></label><label>Trang thai<select data-field="review_status">'+opts(r.review_status,['pending','approved','rejected'])+'</select></label><label class="notes">Ghi chu<input data-field="reviewer_notes" value="'+esc(r.reviewer_notes)+'" placeholder="Bat buoc neu rejected/low confidence"></label></div></section>'}
function filtered(){const kind=document.querySelector('#kind').value,status=document.querySelector('#status').value,q=document.querySelector('#query').value.toLowerCase();return data[kind].filter(r=>(!status||r.review_status===status)&&(!q||r.query_id.toLowerCase().includes(q)))}
function valid(r){if(!r.hard_constraints_satisfied||r.visual_similarity===''||r.relevance_grade===''||!r.confidence){alert('Can chon du 4 truong danh gia truoc khi approved.');return false}if(Number(r.relevance_grade)>=2&&r.hard_constraints_satisfied!=='yes'){alert('Grade 2-3 bat buoc Hard constraints = yes.');return false}if(r.hard_constraints_satisfied==='no'&&Number(r.relevance_grade)>1){alert('Hard constraints = no thi grade toi da la 1.');return false}if(r.confidence==='low'&&!String(r.reviewer_notes||'').trim()){alert('Low confidence bat buoc ghi chu.');return false}return true}
function render(){const kind=document.querySelector('#kind').value,rows=filtered(),size=Number(document.querySelector('#pageSize').value),pages=Math.max(1,Math.ceil(rows.length/size));page=Math.min(page,pages-1);const shown=rows.slice(page*size,(page+1)*size);document.querySelector('#stats').textContent=rows.length+' dang loc / '+data[kind].length+' tong';document.querySelector('#pageInfo').textContent='Trang '+(page+1)+'/'+pages;document.querySelector('#cards').innerHTML=shown.map(r=>kind==='references'?referenceCard(r):candidateCard(r)).join('');document.querySelectorAll('.card[data-key]').forEach(card=>{const r=data[kind].find(x=>key(x)===card.dataset.key);card.querySelectorAll('[data-field]').forEach(el=>el.onchange=e=>{const field=e.target.dataset.field,old=r[field];r[field]=e.target.value;if(field==='review_status'&&r[field]==='approved'&&!valid(r)){r[field]=old;e.target.value=old;return}persist(r);if(field==='review_status')render()})})}
function csvCell(v){const s=String(v??'');return /[",\\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s}
document.querySelector('#export').onclick=()=>{const kind=document.querySelector('#kind').value,rows=data[kind],fields=kind==='references'?referenceFields:candidateFields,csv=[fields.join(','),...rows.map(r=>fields.map(f=>csvCell(r[f])).join(','))].join('\\n'),a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.download=kind==='candidates'?'hybrid_candidate_review.csv':'hybrid_reference_review.csv';a.click();URL.revokeObjectURL(a.href)};
async function init(){const state=document.querySelector('#saveState');try{const response=await fetch('/api/reviews');if(!response.ok)throw Error();const serverRows=await response.json();for(const incoming of serverRows){const row=data.candidates.find(x=>key(x)===key(incoming));if(row)Object.assign(row,incoming)}for(const row of data.candidates)if(saved[key(row)])Object.assign(row,saved[key(row)]);const localRows=data.candidates.filter(r=>saved[key(r)]).map(reviewState);if(localRows.length){await fetch('/api/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows:localRows})})}state.textContent='Da ket noi CSV'}catch(e){state.textContent='Chi luu trong trinh duyet'}render()}
document.querySelector('#prev').onclick=()=>{page=Math.max(0,page-1);render()};document.querySelector('#next').onclick=()=>{page++;render()};for(const id of ['kind','status','query','pageSize'])document.querySelector('#'+id).oninput=()=>{page=0;render()};init();
</script></body></html>"""
    document = (
        document.replace("__PAYLOAD__", payload)
        .replace("__CANDIDATE_FIELDS__", json.dumps(CANDIDATE_FIELDS))
        .replace("__REFERENCE_FIELDS__", json.dumps(REFERENCE_FIELDS))
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the auditable Hybrid Search ground-truth review packet.")
    root = SCRIPT_DIR.parent
    parser.add_argument("--queries-csv", type=Path, default=root / "data" / "multimodal_queries.csv")
    parser.add_argument("--requirements-csv", type=Path, default=root / "data" / "reference_image_requirements.csv")
    parser.add_argument("--candidates-csv", type=Path, default=root / "data" / "ground_truth_multimodal_post_filter_20260831.csv")
    parser.add_argument("--products-csv", type=Path, default=root / "data" / "product_snapshot.csv")
    parser.add_argument("--product-images-csv", type=Path, default=root.parent / "image" / "data" / "product_images.csv")
    parser.add_argument("--reference-review-csv", type=Path, default=root / "reports" / "review" / "hybrid_reference_review.csv")
    parser.add_argument("--candidate-review-csv", type=Path, default=root / "reports" / "review" / "hybrid_candidate_review.csv")
    parser.add_argument("--output-html", type=Path, default=root / "reports" / "review" / "hybrid_ground_truth_review.html")
    parser.add_argument(
        "--references-only",
        action="store_true",
        help="Build the 100-reference manual-review packet without overwriting candidate review CSV.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queries = read_csv(args.queries_csv)
    if args.references_only:
        references = build_reference_rows(queries, read_csv(args.requirements_csv))
        write_csv(args.reference_review_csv, REFERENCE_FIELDS, references)
        render_html(references, [], args.output_html)
        print(f"references={len(references)} pending={sum(r['review_status']=='pending' for r in references)}")
        print(f"review_html={args.output_html}")
        return 0
    references = read_csv(args.reference_review_csv)
    if len(references) != 100 or any(row.get("review_status") != "approved" for row in references):
        raise ValueError("all 100 reference images must be approved before candidate review")
    candidates = build_candidate_rows(
        queries, read_csv(args.candidates_csv), read_csv(args.products_csv),
        read_csv(args.product_images_csv),
    )
    if len(candidates) != 654:
        raise ValueError(f"expected 654 candidate pairs, found {len(candidates)}")
    write_csv(args.candidate_review_csv, CANDIDATE_FIELDS, candidates)
    render_manual_candidate_html(references, candidates, args.output_html)
    print(f"references={len(references)} approved=100")
    print(f"candidates={len(candidates)} pending={sum(r['review_status']=='pending' for r in candidates)}")
    print(f"review_html={args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
