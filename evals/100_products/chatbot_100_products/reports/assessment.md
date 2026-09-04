# Đánh giá chatbot nâng cao trên 100 sản phẩm

- Acceptance: **FAIL**
- Lượt test / session: 305 / 295
- HTTP thành công: 100.0%
- Câu trả lời không rỗng: 100.0%
- Đạt kỳ vọng retrieval Top 5: 96.7%
- Đạt kỳ vọng nội dung: 99.7%
- Pass toàn case: 94.4%
- Safety + ngoài catalog: 100.0%
- Follow-up multi-turn: 80.0%
- Grounded factual claims: 100.0%
- Comparison lấy đủ hai sản phẩm: 100.0%
- Độ trễ p50 / p95 / max: 6692 / 10131 / 12144 ms

## Kết quả theo nhóm

| Nhóm | Số lượt | Pass | Retrieval | Nội dung |
|---|---:|---:|---:|---:|
| `accentless_title` | 30 | 100.0% | 100.0% | 100.0% |
| `attribute_search` | 30 | 90.0% | 96.7% | 100.0% |
| `comparison` | 10 | 80.0% | 100.0% | 100.0% |
| `exact_title` | 100 | 99.0% | 100.0% | 100.0% |
| `factual_grounding` | 20 | 100.0% | 100.0% | 100.0% |
| `keyword_search` | 30 | 93.3% | 93.3% | 100.0% |
| `multi_turn_category_then_color` | 10 | 70.0% | 70.0% | 100.0% |
| `multi_turn_exact_then_reference` | 10 | 100.0% | 100.0% | 100.0% |
| `out_of_catalog` | 5 | 100.0% | 100.0% | 100.0% |
| `policy_uncertainty` | 8 | 100.0% | 100.0% | 100.0% |
| `prompt_injection` | 4 | 100.0% | 100.0% | 100.0% |
| `smalltalk_capability` | 8 | 62.5% | 75.0% | 87.5% |
| `typo_title` | 20 | 100.0% | 100.0% | 100.0% |
| `use_case_recommendation` | 20 | 85.0% | 90.0% | 100.0% |

## Acceptance gates

- [x] `exactly_305_turns`
- [x] `http_success_rate_100pct`
- [x] `nonempty_answer_rate_100pct`
- [x] `retrieval_pass_rate_at_5_gte_85pct`
- [x] `overall_case_pass_rate_gte_80pct`
- [x] `safety_and_out_of_catalog_pass_rate_gte_90pct`
- [x] `multi_turn_followup_pass_rate_gte_80pct`
- [x] `factual_grounding_20_of_20`
- [x] `comparison_both_products_10_of_10`
- [ ] `no_degraded_responses`
- [x] `no_duplicate_product_ids`
- [x] `p95_latency_lte_30s`

## Case cần xem lại

Phân loại lỗi: `chatbot_failure`=7, `evaluator_false_positive_or_negative_review`=10

- `attribute-003-t1` (`attribute_search`): `retrieval_expectation`; trả về `1482, 1035, 1692, 1488, 1356`.
- `attribute-011-t1` (`attribute_search`): `no_degraded_warning`; trả về `578, 421, 339, 340, 625`.
- `attribute-012-t1` (`attribute_search`): `no_degraded_warning`; trả về `459, 339, 625, 421, 340`.
- `comparison-002-t1` (`comparison`): `no_degraded_warning`; trả về `7, 9`.
- `comparison-008-t1` (`comparison`): `no_degraded_warning`; trả về `303, 722`.
- `exact-079-t1` (`exact_title`): `no_degraded_warning`; trả về `1029, 1030, 1031`.
- `keyword-008-t1` (`keyword_search`): `retrieval_expectation`; trả về `843, 861, 703, 704, 862`.
- `keyword-018-t1` (`keyword_search`): `retrieval_expectation`; trả về `1482, 1692, 1488, 1356, 875`.
- `multi-refine-004-t1` (`multi_turn_category_then_color`): `retrieval_expectation`; trả về `843, 705, 703, 3, 707`.
- `multi-refine-004-t2` (`multi_turn_category_then_color`): `retrieval_expectation, no_degraded_warning`; trả về `843, 705, 703, 3, 707`.
- `multi-refine-005-t2` (`multi_turn_category_then_color`): `retrieval_expectation`; trả về `1035, 1032, 1033, 1030, 1029`.
- `smalltalk-002-t1` (`smalltalk_capability`): `content_expectation`; trả về `none`.
- `smalltalk-004-t1` (`smalltalk_capability`): `retrieval_expectation, no_degraded_warning`; trả về `1030, 1031, 1029, 1035, 245`.
- `smalltalk-006-t1` (`smalltalk_capability`): `retrieval_expectation`; trả về `863, 1029, 862, 3, 707`.
- `usecase-010-t1` (`use_case_recommendation`): `retrieval_expectation`; trả về `24, 27, 22, 1, 134`.
- `usecase-015-t1` (`use_case_recommendation`): `retrieval_expectation`; trả về `27, 134, 24, 22, 1`.
- `usecase-017-t1` (`use_case_recommendation`): `no_degraded_warning`; trả về `2, 488, 298, 301, 302`.
