from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR.parent / "reports" / "review" / "ground_truth_image_review_completed.csv"
DEFAULT_OUTPUT = SCRIPT_DIR.parent / "reports" / "review" / "image_ground_truth_audit.html"

BASE_FIELDS = [
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

AUDIT_FIELDS = BASE_FIELDS + [
    "audit_provenance",
    "audit_original_grade",
    "audit_grade",
    "audit_status",
    "audit_notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def audit_provenance(row: dict[str, str]) -> tuple[str, str, str]:
    notes = (row.get("reviewer_notes") or "").strip()
    if notes.startswith("metadata_rule_v1:"):
        return "metadata_rule_v1", "Rule metadata (1,500)", "pending_audit"
    if notes.startswith("human_top5_audit_override:"):
        return "human_top5_audit_override", "Human audit override", "human_reviewed"
    return "human_top5_review", "Human Top-5 review", "human_reviewed"


def build_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        provenance, provenance_label, initial_status = audit_provenance(row)
        normalized = {field: row.get(field, "") for field in BASE_FIELDS}
        normalized.update(
            {
                "audit_provenance": provenance,
                "audit_provenance_label": provenance_label,
                "audit_original_grade": row.get("relevance_grade", ""),
                "audit_grade": row.get("relevance_grade", ""),
                "audit_status": initial_status,
                "audit_notes": "",
            }
        )
        result.append(normalized)
    return result


def build_html(rows: list[dict[str, Any]], output_path: Path) -> None:
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    fields_json = json.dumps(AUDIT_FIELDS, ensure_ascii=False)
    document = f'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Audit Ground Truth Image Search</title>
  <style>
    :root {{ color-scheme: light; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f4f6f8; color: #17202a; font-family: system-ui, sans-serif; }}
    header {{ position: sticky; top: 0; z-index: 5; padding: 12px 18px; background: #fff; box-shadow: 0 2px 8px #0002; }}
    header h1 {{ margin: 0 0 10px; font-size: 20px; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    input, select, button {{ padding: 8px; border: 1px solid #bbc5cf; border-radius: 5px; background: #fff; }}
    button {{ cursor: pointer; }}
    button.primary {{ background: #2463a7; color: #fff; border-color: #2463a7; }}
    #stats {{ color: #43515d; }}
    #saveState {{ color: #267343; }}
    main {{ max-width: 1500px; margin: auto; padding: 14px; }}
    .guide, .card {{ background: #fff; border: 1px solid #d9e0e6; border-radius: 8px; padding: 14px; margin: 10px 0; }}
    .guide {{ border-left: 5px solid #2463a7; line-height: 1.5; }}
    .guide p {{ margin: 6px 0; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .badge {{ display: inline-block; padding: 3px 7px; border-radius: 999px; font-size: 12px; font-weight: 700; }}
    .badge.rule {{ background: #fff0c2; color: #765400; }}
    .badge.human {{ background: #dff3e5; color: #176b35; }}
    .badge.pending {{ background: #ffe0e0; color: #8b1e1e; }}
    .badge.done {{ background: #dcecff; color: #174f8a; }}
    .card {{ border-left: 5px solid #d99200; }}
    .card.human_top5_review, .card.human_top5_audit_override {{ border-left-color: #299653; }}
    .card.audit-done {{ opacity: .88; }}
    .meta {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; color: #43515d; font-size: 13px; }}
    .meta b {{ color: #17202a; }}
    .images {{ display: grid; grid-template-columns: minmax(280px, .8fr) minmax(500px, 1.2fr); gap: 10px; margin-top: 10px; }}
    .panel {{ min-width: 0; }}
    .panel img {{ width: 100%; height: 330px; object-fit: contain; background: #eef1f4; border-radius: 5px; }}
    .candidate-images {{ display: grid; grid-template-columns: repeat(3, minmax(100px, 1fr)); gap: 6px; }}
    .candidate-images img {{ height: 240px; }}
    .metadata, .rule-box {{ margin-top: 8px; padding: 9px; border-radius: 6px; line-height: 1.45; }}
    .metadata {{ background: #f6f8fa; }}
    .rule-box {{ background: #fff8df; }}
    .review {{ display: grid; grid-template-columns: 170px 170px 1fr; gap: 8px; margin-top: 10px; }}
    label {{ font-size: 13px; font-weight: 650; }}
    label select, label input {{ display: block; width: 100%; margin-top: 4px; }}
    .notes {{ grid-column: 1 / -1; }}
    .pager {{ display: flex; justify-content: center; align-items: center; gap: 10px; margin: 16px; }}
    @media (max-width: 900px) {{ .images, .review {{ grid-template-columns: 1fr; }} .notes {{ grid-column: auto; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Audit Ground Truth — Image Search</h1>
    <div class="controls">
      <input id="queryFilter" placeholder="query ID hoặc product ID">
      <select id="provenanceFilter">
        <option value="">Tất cả provenance</option>
        <option value="metadata_rule_v1">1500 rule-assisted</option>
        <option value="human_top5_review">Human Top-5</option>
        <option value="human_top5_audit_override">Human audit override</option>
      </select>
      <select id="statusFilter">
        <option value="">Tất cả trạng thái audit</option>
        <option value="pending_audit">Còn phải audit</option>
        <option value="human_reviewed">Đã review trước đây</option>
        <option value="audited">Đã audit lại</option>
      </select>
      <select id="difficultyFilter"><option value="">Mọi difficulty</option><option>easy</option><option>medium</option><option>hard</option></select>
      <select id="rankFilter"><option value="">Mọi rank</option><option value="top5">rank 1–5</option><option value="top10">rank 6–10</option><option value="top20">rank 11–20</option></select>
      <select id="gradeFilter"><option value="">Mọi grade hiện tại</option><option value="0">grade 0</option><option value="1">grade 1</option><option value="2">grade 2</option><option value="3">grade 3</option></select>
      <select id="pageSize"><option>10</option><option selected>20</option><option>50</option></select>
      <button class="primary" id="export">Xuất full audit CSV</button>
      <span id="stats"></span><b id="saveState">Sẵn sàng</b>
    </div>
  </header>
  <main>
    <section class="guide">
      <b>Mục đích audit</b>
      <p>File này giữ nguyên nhãn hiện tại để đối chiếu. 1.500 dòng màu vàng là nhãn từ <code>metadata_rule_v1</code> và mặc định ở trạng thái <b>còn phải audit</b>; 500 dòng màu xanh là các dòng đã có provenance human.</p>
      <p>Hãy nhìn ảnh query và các ảnh candidate, chọn grade 0–3, đổi trạng thái thành <b>Đã audit lại</b> và ghi chú nếu sửa. Grade 3 = cùng SKU; 2 = rất giống/có thể thay thế; 1 = liên quan yếu; 0 = không liên quan.</p>
      <p>Tiến độ được lưu trong trình duyệt theo từng dòng. Hãy bấm <b>Xuất full audit CSV</b> sau mỗi phiên; file xuất giữ cả grade gốc, grade audit và provenance.</p>
      <div class="legend"><span class="badge rule">metadata_rule_v1</span><span class="badge human">human provenance</span><span class="badge pending">pending audit</span><span class="badge done">audited</span></div>
    </section>
    <div id="cards"></div>
    <div class="pager"><button id="prev">Trang trước</button><span id="pageInfo"></span><button id="next">Trang sau</button></div>
  </main>
<script>
const rows = {payload};
const fields = {fields_json};
const storageKey = 'image-ground-truth-audit-v1|' + window.location.pathname;
const saved = JSON.parse(localStorage.getItem(storageKey) || '{{}}');
const rowKey = row => [row.query_id, row.candidate_product_id, row.candidate_rank].join('|');
for (const row of rows) {{ if (saved[rowKey(row)]) Object.assign(row, saved[rowKey(row)]); }}
let page = 0;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const rankBucket = row => {{ const rank = Number(row.candidate_rank || 0); return rank <= 5 ? 'top5' : rank <= 10 ? 'top10' : 'top20'; }};
function persist(row) {{
  saved[rowKey(row)] = {{ audit_grade: row.audit_grade, audit_status: row.audit_status, audit_notes: row.audit_notes }};
  localStorage.setItem(storageKey, JSON.stringify(saved));
  document.querySelector('#saveState').textContent = 'Đã lưu local';
}}
function filteredRows() {{
  const q = document.querySelector('#queryFilter').value.trim().toLowerCase();
  const provenance = document.querySelector('#provenanceFilter').value;
  const status = document.querySelector('#statusFilter').value;
  const difficulty = document.querySelector('#difficultyFilter').value;
  const rank = document.querySelector('#rankFilter').value;
  const grade = document.querySelector('#gradeFilter').value;
  return rows.filter(row =>
    (!q || [row.query_id, row.query_product_id, row.candidate_product_id].some(value => String(value).toLowerCase().includes(q))) &&
    (!provenance || row.audit_provenance === provenance) &&
    (!status || row.audit_status === status) &&
    (!difficulty || row.difficulty === difficulty) &&
    (!rank || rankBucket(row) === rank) &&
    (!grade || String(row.audit_grade) === grade)
  );
}}
function render() {{
  const filtered = filteredRows();
  const size = Number(document.querySelector('#pageSize').value);
  const pages = Math.max(1, Math.ceil(filtered.length / size));
  page = Math.min(page, pages - 1);
  const visible = filtered.slice(page * size, (page + 1) * size);
  const pending = rows.filter(row => row.audit_status === 'pending_audit').length;
  const audited = rows.filter(row => row.audit_status === 'audited').length;
  document.querySelector('#stats').textContent = `${{filtered.length}} dòng phù hợp · còn audit ${{pending}} · đã audit lại ${{audited}}`;
  document.querySelector('#pageInfo').textContent = `Trang ${{page + 1}}/${{pages}} · ${{visible.length}} dòng`;
  document.querySelector('#prev').disabled = page === 0;
  document.querySelector('#next').disabled = page >= pages - 1;
  document.querySelector('#cards').innerHTML = visible.map(row => `
    <section class="card ${{esc(row.audit_provenance)}} ${{row.audit_status === 'audited' ? 'audit-done' : ''}}" data-key="${{esc(rowKey(row))}}">
      <div class="meta"><b>${{esc(row.query_id)}}</b><span>rank ${{esc(row.candidate_rank || 'missing')}}</span><span>score ${{esc(row.retrieval_score)}}</span><span class="badge ${{row.audit_provenance === 'metadata_rule_v1' ? 'rule' : 'human'}}">${{esc(row.audit_provenance_label)}}</span><span class="badge ${{row.audit_status === 'pending_audit' ? 'pending' : 'done'}}">${{esc(row.audit_status)}}</span></div>
      <div class="images">
        <div class="panel"><b>Query · ${{esc(row.query_product_id)}} · ${{esc(row.query_product_name)}}</b><br><small>${{esc(row.query_category)}}</small><img loading="lazy" src="${{esc(row.query_image_url)}}"></div>
        <div class="panel"><b>Candidate · ${{esc(row.candidate_product_id)}} · ${{esc(row.candidate_product_name)}}</b><br><small>${{esc(row.candidate_category)}} · ${{esc(row.candidate_color)}} · ${{esc(row.candidate_material)}}</small><div class="candidate-images">${{String(row.candidate_image_urls || '').split(' | ').filter(Boolean).map(url => `<img loading="lazy" src="${{esc(url)}}">`).join('')}}</div></div>
      </div>
      <div class="metadata"><b>Nhãn gốc:</b> grade ${{esc(row.audit_original_grade)}} · ${{esc(row.reviewer_notes || 'không có ghi chú')}}<br><b>Gợi ý rule ban đầu:</b> grade ${{esc(row.suggested_grade)}} · ${{esc(row.suggestion_reason)}}</div>
      <div class="review">
        <label>Grade audit<select class="grade">${{[0,1,2,3].map(g => `<option value="${{g}}" ${{String(row.audit_grade) === String(g) ? 'selected' : ''}}>${{g}}</option>`).join('')}}</select></label>
        <label>Trạng thái audit<select class="status"><option value="pending_audit" ${{row.audit_status === 'pending_audit' ? 'selected' : ''}}>Còn phải audit</option><option value="human_reviewed" ${{row.audit_status === 'human_reviewed' ? 'selected' : ''}}>Giữ trạng thái human cũ</option><option value="audited" ${{row.audit_status === 'audited' ? 'selected' : ''}}>Đã audit lại</option></select></label>
        <label class="notes">Ghi chú audit<input class="note" value="${{esc(row.audit_notes)}}" placeholder="Ví dụ: rule gán grade 1 nhưng ảnh thực tế grade 2"></label>
      </div>
    </section>`).join('');
  document.querySelectorAll('.card').forEach(card => {{
    const row = rows.find(item => rowKey(item) === card.dataset.key);
    card.querySelector('.grade').onchange = event => {{ row.audit_grade = event.target.value; persist(row); }};
    card.querySelector('.status').onchange = event => {{ row.audit_status = event.target.value; persist(row); render(); }};
    card.querySelector('.note').onchange = event => {{ row.audit_notes = event.target.value; persist(row); }};
  }});
}}
function csvCell(value) {{ const text = String(value ?? ''); return /[",\\n]/.test(text) ? '"' + text.replaceAll('"', '""') + '"' : text; }}
document.querySelector('#export').onclick = () => {{
  const csv = [fields.join(','), ...rows.map(row => fields.map(field => csvCell(row[field])).join(','))].join('\\n');
  const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([csv], {{type: 'text/csv;charset=utf-8'}})); link.download = 'ground_truth_image_audit.csv'; link.click(); URL.revokeObjectURL(link.href);
}};
for (const id of ['queryFilter','provenanceFilter','statusFilter','difficultyFilter','rankFilter','gradeFilter']) document.querySelector('#' + id).oninput = () => {{ page = 0; render(); }};
document.querySelector('#pageSize').onchange = () => {{ page = 0; render(); }};
document.querySelector('#prev').onclick = () => {{ page -= 1; render(); }};
document.querySelector('#next').onclick = () => {{ page += 1; render(); }};
render();
</script>
</body>
</html>'''
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a gradual audit UI for image ground truth.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-html", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = build_rows(read_csv(args.input_csv))
    build_html(rows, args.output_html)
    provenance_counts = {}
    for row in rows:
        provenance_counts[row["audit_provenance"]] = provenance_counts.get(row["audit_provenance"], 0) + 1
    print(f"built audit rows={len(rows)} provenance={provenance_counts} -> {args.output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
