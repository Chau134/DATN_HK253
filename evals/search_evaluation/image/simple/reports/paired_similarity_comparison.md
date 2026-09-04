# Paired Image Similarity Comparison

Queries: 100; paired bootstrap: 10,000 samples; seed: 42.

| Metric | Simple | Challenging | Delta C-S | CI 95% |
|---|---:|---:|---:|---:|
| Recall@5 | 0.7406 | 0.7214 | -0.0192 | [-0.0558, +0.0170] |
| NDCG@5 | 0.8528 | 0.8100 | -0.0427 | [-0.0682, -0.0189] |
| mAP | 0.7752 | 0.7234 | -0.0518 | [-0.0862, -0.0181] |

The shared ground truth uses binary relevance grade >= 2; grade 1 contributes to graded NDCG.
