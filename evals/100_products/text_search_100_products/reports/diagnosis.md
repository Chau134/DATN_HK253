# Root-cause diagnosis for the healthy-AI run

## Service and index verification

- `GET http://127.0.0.1:8000/health`: HTTP 200.
- `GET http://127.0.0.1:8000/health/ready`: HTTP 200, `ready=true`;
  text and image embedding services are ready.
- Three preflight searches through Spring returned only `ai_source=text`, with no
  `ai_service_unavailable` or `ai_keyword_fallback` warning.
- Qdrant collection `product_text_vectors_cohere_embed_v4_1536` is green and has
  exactly 100 points.
- Comparing Qdrant payload `product_id` values with the 100 test cases produced
  100/100 overlap. The 51 misses are therefore not caused by absent product IDs.

## Primary failure: extracted filters are too strict

Among the 51 Top-5 misses, the response contained these extracted filters:

| Filter | Misses carrying filter |
|---|---:|
| category | 50 |
| gender | 23 |
| colors | 22 |
| material | 18 |
| brand | 2 |

Category and material are unconditional Qdrant `must` filters. Several index-time
payload values cannot match their extracted query values:

| Product | Query extraction | Indexed payload | Effect |
|---|---|---|---|
| 6, cardigan | `material=wool` | composition strings such as `42 acrylic ... 5 wool` | empty result |
| 11, fleece trousers | `material=fleece` | `cotton blend`, `cotton pha` | empty result |
| 16, polo knit | `category=polo`, `material=wool` | categories `sweater,cardigan`; composition string | empty result |
| 17, leather jacket | `material=leather` | `100 sheep leather` | empty result |
| 113, denim shirt | `category=shirt`, `material=denim` | category `jeans`, material `100 cotton` | empty result |

There are 21 queries with no returned products at all. Direct calls to
`/search/text` reproduce the same empty result, so Spring hydration is not the
cause.

## Secondary failures

1. When reranking is disabled, candidate retrieval uses only `top_k` candidates.
   For `top_k=5`, any correct product below vector rank 5 is unrecoverable.
2. Query rewriting often moves category/material words into filters and embeds a
   much shorter remainder. If the filter is inconsistent, both the candidate set
   and semantic query lose the most useful title terms.
3. There is no lexical exact-title fusion before final ranking. Consequently an
   exact indexed title achieves only 37% normalized-title match at rank 1.
4. Duplicate Vietnamese titles require equivalence-group scoring; strict source-ID
   Hit@1 unfairly penalizes interchangeable catalog records.

## Recommended implementation order

1. Make LLM/rule-extracted category and material soft constraints. Keep only
   explicit API request filters hard.
2. If hard-filtered retrieval is empty or below a confidence threshold, retry with
   `active=true` only and apply extracted filters as post-retrieval boosts.
3. Canonicalize index material metadata into atomic keys (`wool`, `leather`,
   `cotton`, `denim`, etc.) and repair product/category taxonomy conflicts.
4. Retrieve a fixed candidate pool of at least 20-50 points independently of
   output `top_k`.
5. Fuse vector score with normalized exact-title/token score, then enable the
   configured reranker if credentials are available.
6. Rerun this exact suite before adding accentless, typo, use-case, filter, and
   negative-query evaluations.
