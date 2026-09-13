"""Generate a self-contained browser review page from the frozen review pool."""

import argparse
import csv
import html
import json
from pathlib import Path


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--export-name", default="hybrid_ground_truth_reviewed_all_v1.csv", help="Distinct download filename for a new review round")
    parser.add_argument("--max-rank", type=int, default=5, help="include rows up to this rank in either run")
    args = parser.parse_args()
    if Path(args.export_name).name != args.export_name or not args.export_name.lower().endswith(".csv"):
        parser.error("--export-name must be a CSV filename, not a path")
    source_rows = read_csv(args.pool)
    rows = []
    for row in source_rows:
        candidate_rank = row.get("candidate_rank", "")
        baseline_rank = row.get("baseline_rank", "")
        in_rank = ((candidate_rank and int(candidate_rank) <= args.max_rank) or
                   (baseline_rank and int(baseline_rank) <= args.max_rank))
        if not in_rank and row.get("priority") != "P1_target_outside_top5":
            continue
        item = dict(row)
        # Existing approved grade is reference-only; new/manual fields are what
        # the reviewer edits in the browser.
        item["manual_relevance_grade"] = item.get("existing_grade", "")
        item["manual_constraint_status"] = ""
        item["manual_violation_fields"] = ""
        item["reviewer"] = ""
        item["reviewed_at"] = ""
        item["review_notes"] = ""
        rows.append(item)
    fields = list(rows[0]) if rows else []
    payload = json.dumps({"fields": fields, "rows": rows}, ensure_ascii=False).replace("</", "<\\/")
    export_name_json = json.dumps(args.export_name).replace("</", "<\\/")
    title = "Hybrid Ground Truth Review"
    page = f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light; font-family: Segoe UI, Arial, sans-serif; }}
body {{ margin: 0; background: #f5f7fb; color: #172033; }}
header {{ position: sticky; top: 0; z-index: 10; background: #172033; color: white; padding: 14px 18px; box-shadow: 0 2px 8px #0003; }}
h1 {{ font-size: 20px; margin: 0 0 6px; }}
.sub {{ font-size: 12px; opacity: .85; }}
.toolbar {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 12px 18px; background: white; border-bottom: 1px solid #dce2ec; position: sticky; top: 73px; z-index: 9; }}
input, select, button {{ font: inherit; border: 1px solid #bcc7d8; border-radius: 5px; padding: 6px 8px; background: white; }}
button {{ cursor: pointer; background: #1f6feb; color: white; border-color: #1f6feb; font-weight: 600; }}
button.secondary {{ background: white; color: #1f3d6d; }}
.stats {{ margin-left: auto; font-size: 12px; color: #43516a; }}
.note {{ margin: 12px 18px; padding: 10px 12px; background: #fffbe6; border: 1px solid #ead38b; border-radius: 6px; font-size: 13px; line-height: 1.45; }}
.table-wrap {{ overflow: auto; margin: 0 18px 24px; max-height: calc(100vh - 205px); border: 1px solid #dce2ec; background: white; }}
table {{ border-collapse: separate; border-spacing: 0; min-width: 2050px; width: max-content; font-size: 12px; }}
th, td {{ border-right: 1px solid #e4e9f1; border-bottom: 1px solid #e4e9f1; padding: 6px; vertical-align: top; max-width: 280px; }}
th {{ position: sticky; top: 0; background: #eaf0f8; z-index: 3; text-align: left; white-space: nowrap; }}
td {{ background: white; }}
tr.priority-p0_candidate_top5_unjudged td, tr.priority-p0_baseline_top5_unjudged td {{ background: #fff8e1; }}
tr.priority-p1_target_outside_top5 td {{ background: #ffeceb; }}
.sticky {{ position: sticky; left: 0; z-index: 2; background: inherit; min-width: 104px; }}
th.sticky {{ z-index: 4; background: #eaf0f8; }}
.qid {{ font-weight: 700; white-space: nowrap; }}
.query {{ min-width: 300px; max-width: 390px; white-space: normal; }}
.product {{ min-width: 250px; white-space: normal; }}
.candidate-images {{ min-width: 330px; max-width: 360px; }}
.candidate-images img {{ width: 105px; height: 135px; object-fit: contain; background: #f0f2f5; border: 1px solid #dce2ec; margin: 2px; vertical-align: top; }}
.muted {{ color: #68758c; }}
.rank {{ text-align: center; min-width: 45px; }}
.grade, .constraint {{ min-width: 150px; }}
.grade select, .constraint select {{ width: 145px; }}
.notes input {{ width: 220px; }}
a {{ color: #145db2; }}
.priority {{ white-space: nowrap; font-weight: 600; }}
</style>
</head>
<body>
<header><h1>Hybrid Ground Truth Review</h1><div class="sub">Review độc lập NDCG@5 và constraint gate · dữ liệu nhúng từ review pool · không sửa ground truth gốc</div></header>
<div class="toolbar">
  <input id="search" placeholder="Tìm query, product, nội dung..." size="30">
  <select id="priority"><option value="">Tất cả priority</option><option value="P0_candidate_top5_unjudged">P0 candidate Top-5</option><option value="P0_baseline_top5_unjudged">P0 baseline Top-5</option><option value="P1_target_outside_top5">P1 target ngoài Top-5</option><option value="P2_candidate_top20_unjudged">P2 candidate Top-20</option><option value="P3_baseline_top20_unjudged">P3 baseline Top-20</option></select>
  <select id="reviewState"><option value="">Tất cả trạng thái</option><option value="unreviewed">Chưa review</option><option value="reviewed">Đã có grade + constraint</option></select>
  <button id="download">Tải toàn bộ CSV</button><button class="secondary" id="downloadNdcg">Tải pool NDCG Top-5</button><button class="secondary" id="downloadConstraint">Tải pool constraint candidate</button><button class="secondary" id="fillTime">Điền thời gian các dòng đã sửa</button><button class="secondary" id="reset">Khôi phục bản nhúng</button>
  <span class="stats" id="stats"></span>
</div>
<div class="note"><b>Quy tắc:</b> Grade NDCG: 3 = đúng kiểu dáng + đúng yêu cầu văn bản; 2 = phù hợp rõ nhưng khác biệt nhỏ; 1 = chỉ liên quan một phần; 0 = không liên quan/vi phạm yêu cầu chính. Constraint điền <code>pass</code>, <code>fail</code> hoặc <code>unclear</code>. Không suy grade từ target ID hay fixture; tỷ lệ % chỉ bắt buộc khi query nói rõ. Với mismatch màu/sắc độ hoặc thứ tự usage, ghi chú để adjudicate.</div>
<div class="table-wrap"><table><thead><tr>
<th class="sticky">Query / priority</th><th>Ảnh tham chiếu</th><th class="candidate-images">Ảnh candidate</th><th class="query">Query text</th><th>Transform</th><th class="rank">Candidate rank</th><th class="rank">Baseline rank</th><th class="product">Product</th><th>Product category</th><th>Color</th><th>Material</th><th>Usage</th><th>Price</th><th>Fixture constraints</th><th class="grade">NDCG grade</th><th class="constraint">Constraint</th><th>Violation fields</th><th>Reviewer</th><th>Reviewed at</th><th class="notes">Notes</th>
</tr></thead><tbody id="body"></tbody></table></div>
<script>
const INITIAL = {payload};
let rows = structuredClone(INITIAL.rows);
const body = document.getElementById('body');
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const reviewed = r => r.manual_relevance_grade !== '' && r.manual_constraint_status !== '' && r.reviewer !== '' && r.reviewed_at !== '';
function select(value, options, cls, ri, field) {{
  const opts = options.map(x => `<option value="${{esc(x)}}" ${{String(value)===x?'selected':''}}>${{x || '—'}}</option>`).join('');
  return `<select class="${{cls}}" data-row="${{ri}}" data-field="${{field}}">${{opts}}</select>`;
}}
function textInput(value, ri, field, width='') {{ return `<input value="${{esc(value)}}" data-row="${{ri}}" data-field="${{field}}" ${{width?'style="width:'+width+'"':''}}>`; }}
function render() {{
  const q = document.getElementById('search').value.toLowerCase();
  const p = document.getElementById('priority').value;
  const s = document.getElementById('reviewState').value;
  body.innerHTML = '';
  let visible = 0;
  rows.forEach((r, i) => {{
    const hay = JSON.stringify(r).toLowerCase();
    if (q && !hay.includes(q)) return;
    if (p && r.priority !== p) return;
    if (s === 'reviewed' && !reviewed(r)) return;
    if (s === 'unreviewed' && reviewed(r)) return;
    visible++;
    const tr = document.createElement('tr'); tr.className = 'priority-' + (r.priority || 'none');
    const fixture = [r.fixture_category, r.fixture_color, r.fixture_material, r.fixture_usage, r.fixture_price_bucket].filter(Boolean).join(' · ');
    const candidateImages = (r.candidate_image_urls || '').split(' | ').filter(Boolean).map(u => `<a href="${{esc(u)}}" target="_blank" rel="noopener"><img loading="lazy" src="${{esc(u)}}" alt="candidate ${{esc(r.product_id)}}"></a>`).join('') || '<span class="muted">Không có URL ảnh candidate</span>';
    tr.innerHTML = `<td class="sticky"><div class="qid">${{esc(r.query_id)}}</div><div class="priority">${{esc(r.priority)}}</div><div class="muted">target: ${{esc(r.target_product_id)}}</div></td>
      <td><a href="${{esc(r.image_url)}}" target="_blank" rel="noopener">mở ảnh</a></td><td class="candidate-images">${{candidateImages}}</td>
      <td class="query">${{esc(r.query_text)}}</td><td>${{esc(r.transformation_type)}}<br><span class="muted">${{esc(r.difficulty)}}</span></td>
      <td class="rank">${{esc(r.candidate_rank)}}</td><td class="rank">${{esc(r.baseline_rank)}}</td>
      <td class="product"><b>${{esc(r.product_id)}}</b> · ${{esc(r.product_name)}}<br><span class="muted">${{esc(r.existing_grade ? 'existing grade '+r.existing_grade : '')}}</span></td>
      <td>${{esc(r.product_category)}}</td><td>${{esc(r.product_color)}}</td><td>${{esc(r.product_material)}}</td><td>${{esc(r.product_usage)}}</td><td>${{esc(r.product_price)}}</td>
      <td class="product">${{esc(fixture)}}</td>
      <td class="grade">${{select(r.manual_relevance_grade, ['', '0','1','2','3'], '', i, 'manual_relevance_grade')}}</td>
      <td class="constraint">${{select(r.manual_constraint_status, ['', 'pass','fail','unclear'], '', i, 'manual_constraint_status')}}</td>
      <td>${{textInput(r.manual_violation_fields, i, 'manual_violation_fields', '150px')}}</td><td>${{textInput(r.reviewer, i, 'reviewer', '120px')}}</td><td>${{textInput(r.reviewed_at, i, 'reviewed_at', '145px')}}</td><td class="notes">${{textInput(r.review_notes, i, 'review_notes', '220px')}}</td>`;
    body.appendChild(tr);
  }});
  document.getElementById('stats').textContent = `${{visible}} / ${{rows.length}} dòng · đã hoàn tất ${{rows.filter(reviewed).length}}`;
}}
body.addEventListener('change', e => {{ const i=e.target.dataset.row, f=e.target.dataset.field; if (i !== undefined && f) {{ rows[Number(i)][f]=e.target.value; render(); }} }});
body.addEventListener('input', e => {{ const i=e.target.dataset.row, f=e.target.dataset.field; if (i !== undefined && f) rows[Number(i)][f]=e.target.value; }});
['search','priority','reviewState'].forEach(id => document.getElementById(id).addEventListener('input', render));
document.getElementById('reset').onclick = () => {{ rows = structuredClone(INITIAL.rows); render(); }};
document.getElementById('fillTime').onclick = () => {{ const now = new Date().toISOString(); rows.forEach(r => {{ if (r.manual_relevance_grade !== '' || r.manual_constraint_status !== '' || r.review_notes) r.reviewed_at = r.reviewed_at || now; }}); render(); }};
function csvCell(v) {{ return '"' + String(v ?? '').replace(/"/g, '""') + '"'; }}
function downloadRows(selected, name) {{
  const csv = [INITIAL.fields, ...selected.map(r => INITIAL.fields.map(f => r[f] ?? ''))].map(row => row.map(csvCell).join(',')).join('\\r\\n');
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([new TextEncoder().encode('\\ufeff'+csv)], {{type:'text/csv;charset=utf-8'}})); a.download = name; a.click(); URL.revokeObjectURL(a.href);
}}
document.getElementById('download').onclick = () => downloadRows(rows, {export_name_json});
document.getElementById('downloadNdcg').onclick = () => downloadRows(rows.filter(r => ['P0_candidate_top5_unjudged','P0_baseline_top5_unjudged'].includes(r.priority)), 'hybrid_ndcg_top5_reviewed_v1.csv');
document.getElementById('downloadConstraint').onclick = () => downloadRows(rows.filter(r => r.candidate_rank && Number(r.candidate_rank) <= 5), 'hybrid_constraint_top5_reviewed_v1.csv');
render();
</script>
</body></html>'''
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8")
    print(json.dumps({"output": str(args.output), "rows": len(rows), "bytes": args.output.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
