from __future__ import annotations

from collections import Counter, defaultdict
from threading import Lock
from typing import Mapping


_DURATION_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0)
_RESULT_BUCKETS = (0, 1, 3, 5, 10, 20, 50, 100)
_COVERAGE_BUCKETS = (0.0, 0.25, 0.5, 0.75, 1.0)
_CATEGORY_MATCH_TYPES = frozenset({"exact", "alias", "typo", "inferred", "none"})


class SearchMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: Counter[tuple[str, str]] = Counter()
        self._llm_paths: Counter[str] = Counter()
        self._recoveries: Counter[str] = Counter()
        self._typo_corrections = 0
        self._category_matches: Counter[str] = Counter()
        self._filter_relaxations: Counter[str] = Counter()
        self._recovery_outcomes: Counter[str] = Counter()
        self._coverage_buckets: Counter[float] = Counter()
        self._coverage_count = 0
        self._coverage_sum = 0.0
        self._duration_count: Counter[tuple[str, str]] = Counter()
        self._duration_sum: defaultdict[tuple[str, str], float] = defaultdict(float)
        self._duration_buckets: Counter[tuple[str, str, float]] = Counter()
        self._result_buckets: Counter[tuple[str, int]] = Counter()
        self._result_count: Counter[str] = Counter()
        self._result_sum: Counter[str] = Counter()

    def observe_text_search(
        self,
        *,
        timings_ms: Mapping[str, float],
        total_ms: float,
        llm_used: bool,
        recovery_triggered: bool,
        result_count: int,
        rejection_reason: str | None = None,
        typo_correction_count: int = 0,
        category_match_type: str | None = None,
        category_filter_relaxed: bool = False,
        recovery_rescued_top5: bool = False,
        top1_lexical_coverage: float | None = None,
    ) -> None:
        stages = {
            "analyze": float(timings_ms.get("analyze_ms", 0.0)),
            "llm": float(timings_ms.get("llm_ms", 0.0)),
            "embedding": float(timings_ms.get("embed_ms", 0.0)),
            "qdrant": float(timings_ms.get("qdrant_ms", 0.0)),
            "primary_qdrant": float(timings_ms.get("primary_qdrant_ms", 0.0)),
            "scoring": float(timings_ms.get("score_ms", 0.0)),
            "rerank": float(timings_ms.get("rerank_ms", 0.0)),
            "total": total_ms,
        }
        if recovery_triggered:
            stages["recovery_qdrant"] = float(
                timings_ms.get("recovery_qdrant_ms", 0.0)
            )
        with self._lock:
            self._requests[("text", "success")] += 1
            self._llm_paths["llm" if llm_used else "fast_path"] += 1
            self._typo_corrections += max(0, int(typo_correction_count))
            match_type = category_match_type or "none"
            if match_type not in _CATEGORY_MATCH_TYPES:
                match_type = "none"
            self._category_matches[match_type] += 1
            if category_filter_relaxed:
                self._filter_relaxations["category"] += 1
            if rejection_reason:
                self._recoveries[f"rejected_{rejection_reason}"] += 1
            else:
                self._recoveries["triggered" if recovery_triggered else "not_triggered"] += 1
            if recovery_triggered:
                self._recovery_outcomes[
                    "rescued_top5" if recovery_rescued_top5 else "not_rescued_top5"
                ] += 1
            for stage, duration_ms in stages.items():
                key = ("text", stage)
                seconds = max(0.0, duration_ms / 1000)
                self._duration_count[key] += 1
                self._duration_sum[key] += seconds
                for bucket in _DURATION_BUCKETS:
                    if seconds <= bucket:
                        self._duration_buckets[("text", stage, bucket)] += 1
            self._result_count["text"] += 1
            self._result_sum["text"] += result_count
            for bucket in _RESULT_BUCKETS:
                if result_count <= bucket:
                    self._result_buckets[("text", bucket)] += 1
            if top1_lexical_coverage is not None:
                coverage = min(1.0, max(0.0, float(top1_lexical_coverage)))
                self._coverage_count += 1
                self._coverage_sum += coverage
                for bucket in _COVERAGE_BUCKETS:
                    if coverage <= bucket:
                        self._coverage_buckets[bucket] += 1

    def record_error(self, mode: str) -> None:
        with self._lock:
            self._requests[(mode, "error")] += 1

    def render_prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP ecommerce_search_requests_total Search requests by mode and outcome.",
                "# TYPE ecommerce_search_requests_total counter",
            ]
            for (mode, outcome), value in sorted(self._requests.items()):
                lines.append(
                    f'ecommerce_search_requests_total{{mode="{mode}",outcome="{outcome}"}} {value}'
                )
            lines.extend(
                [
                    "# HELP ecommerce_search_text_path_total Text requests by query-understanding path.",
                    "# TYPE ecommerce_search_text_path_total counter",
                ]
            )
            for path, value in sorted(self._llm_paths.items()):
                lines.append(f'ecommerce_search_text_path_total{{path="{path}"}} {value}')
            lines.extend(
                [
                    "# HELP ecommerce_search_recovery_total Text weak-result recovery decisions.",
                    "# TYPE ecommerce_search_recovery_total counter",
                ]
            )
            for decision, value in sorted(self._recoveries.items()):
                lines.append(f'ecommerce_search_recovery_total{{decision="{decision}"}} {value}')
            lines.extend(
                [
                    "# HELP ecommerce_search_typo_corrections_total Controlled query typo corrections.",
                    "# TYPE ecommerce_search_typo_corrections_total counter",
                    f"ecommerce_search_typo_corrections_total {self._typo_corrections}",
                    "# HELP ecommerce_search_category_match_total Category matches by bounded type.",
                    "# TYPE ecommerce_search_category_match_total counter",
                ]
            )
            for match_type, value in sorted(self._category_matches.items()):
                lines.append(
                    f'ecommerce_search_category_match_total{{match_type="{match_type}"}} {value}'
                )
            lines.extend(
                [
                    "# HELP ecommerce_search_filter_relaxation_total Relaxed inferred filters.",
                    "# TYPE ecommerce_search_filter_relaxation_total counter",
                ]
            )
            for field, value in sorted(self._filter_relaxations.items()):
                lines.append(
                    f'ecommerce_search_filter_relaxation_total{{field="{field}"}} {value}'
                )
            lines.extend(
                [
                    "# HELP ecommerce_search_recovery_outcome_total Recovery Top-5 outcomes.",
                    "# TYPE ecommerce_search_recovery_outcome_total counter",
                ]
            )
            for outcome, value in sorted(self._recovery_outcomes.items()):
                lines.append(
                    f'ecommerce_search_recovery_outcome_total{{outcome="{outcome}"}} {value}'
                )
            lines.extend(
                [
                    "# HELP ecommerce_search_stage_duration_seconds Search stage duration.",
                    "# TYPE ecommerce_search_stage_duration_seconds histogram",
                ]
            )
            for mode, stage in sorted(self._duration_count):
                for bucket in _DURATION_BUCKETS:
                    count = self._duration_buckets[(mode, stage, bucket)]
                    lines.append(
                        "ecommerce_search_stage_duration_seconds_bucket"
                        f'{{mode="{mode}",stage="{stage}",le="{bucket:g}"}} {count}'
                    )
                count = self._duration_count[(mode, stage)]
                total = self._duration_sum[(mode, stage)]
                lines.append(
                    "ecommerce_search_stage_duration_seconds_bucket"
                    f'{{mode="{mode}",stage="{stage}",le="+Inf"}} {count}'
                )
                lines.append(
                    f'ecommerce_search_stage_duration_seconds_count{{mode="{mode}",stage="{stage}"}} {count}'
                )
                lines.append(
                    f'ecommerce_search_stage_duration_seconds_sum{{mode="{mode}",stage="{stage}"}} {total:.9f}'
                )
            lines.extend(
                [
                    "# HELP ecommerce_search_result_count Number of returned products.",
                    "# TYPE ecommerce_search_result_count histogram",
                ]
            )
            for mode in sorted(self._result_count):
                for bucket in _RESULT_BUCKETS:
                    count = self._result_buckets[(mode, bucket)]
                    lines.append(
                        f'ecommerce_search_result_count_bucket{{mode="{mode}",le="{bucket}"}} {count}'
                    )
                count = self._result_count[mode]
                lines.append(
                    f'ecommerce_search_result_count_bucket{{mode="{mode}",le="+Inf"}} {count}'
                )
                lines.append(f'ecommerce_search_result_count_count{{mode="{mode}"}} {count}')
                lines.append(
                    f'ecommerce_search_result_count_sum{{mode="{mode}"}} {self._result_sum[mode]}'
                )
            lines.extend(
                [
                    "# HELP ecommerce_search_top1_lexical_coverage Top-1 title token coverage.",
                    "# TYPE ecommerce_search_top1_lexical_coverage histogram",
                ]
            )
            for bucket in _COVERAGE_BUCKETS:
                lines.append(
                    "ecommerce_search_top1_lexical_coverage_bucket"
                    f'{{le="{bucket:g}"}} {self._coverage_buckets[bucket]}'
                )
            lines.append(
                "ecommerce_search_top1_lexical_coverage_bucket"
                f'{{le="+Inf"}} {self._coverage_count}'
            )
            lines.append(
                f"ecommerce_search_top1_lexical_coverage_count {self._coverage_count}"
            )
            lines.append(
                f"ecommerce_search_top1_lexical_coverage_sum {self._coverage_sum:.9f}"
            )
            return "\n".join(lines) + "\n"

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
            self._llm_paths.clear()
            self._recoveries.clear()
            self._typo_corrections = 0
            self._category_matches.clear()
            self._filter_relaxations.clear()
            self._recovery_outcomes.clear()
            self._coverage_buckets.clear()
            self._coverage_count = 0
            self._coverage_sum = 0.0
            self._duration_count.clear()
            self._duration_sum.clear()
            self._duration_buckets.clear()
            self._result_buckets.clear()
            self._result_count.clear()
            self._result_sum.clear()


search_metrics = SearchMetrics()


class AssistantMetrics:
    """Low-cardinality conversational-memory metrics without message content."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._observations = 0
        self._turn_index = 0
        self._recent_message_count = 0
        self._summary_chars = 0
        self._summary_compaction_count = 0
        self._memory_sources: Counter[str] = Counter()
        self._reference_sources: Counter[str] = Counter()
        self._recall_probes: Counter[str] = Counter()
        self._checkpoint_failures = 0
        self._summary_limit_streak = 0
        self._early_latency_count = 0
        self._early_latency_sum = 0.0
        self._late_latency_count = 0
        self._late_latency_sum = 0.0
        self._product_context_cache_hits = 0
        self._product_context_cache_misses = 0
        self._routes: Counter[str] = Counter()
        self._llm_calls = 0
        self._springboot_calls = 0
        self._fallbacks: Counter[str] = Counter()
        self._stage_latency_count: Counter[str] = Counter()
        self._stage_latency_sum: Counter[str] = Counter()
        self._stage_latency_max: dict[str, float] = {}

    def observe_memory(
        self,
        *,
        turn_index: int,
        recent_message_count: int,
        summary_chars: int,
        summary_compaction_count: int,
        summary_max_chars: int,
        memory_sources: list[str],
        reference_resolution_source: str,
    ) -> None:
        allowed_memory_sources = {
            "structured_active_state",
            "recent_transcript",
            "semantic_summary",
            "long_term_preference",
            "none",
        }
        allowed_reference_sources = {"first", "latest", "named", "last_product_ids", "none"}
        with self._lock:
            self._observations += 1
            self._turn_index = max(0, int(turn_index))
            self._recent_message_count = max(0, int(recent_message_count))
            self._summary_chars = max(0, int(summary_chars))
            self._summary_compaction_count = max(0, int(summary_compaction_count))
            for source in set(memory_sources or ["none"]):
                bounded = source if source in allowed_memory_sources else "none"
                self._memory_sources[bounded] += 1
            reference = reference_resolution_source
            if reference.startswith("named:"):
                reference = "named"
            if reference not in allowed_reference_sources:
                reference = "none"
            self._reference_sources[reference] += 1
            at_limit = summary_max_chars > 0 and summary_chars >= summary_max_chars
            self._summary_limit_streak = self._summary_limit_streak + 1 if at_limit else 0

    def observe_latency(self, *, turn_index: int, duration_seconds: float) -> None:
        duration = max(0.0, float(duration_seconds))
        with self._lock:
            if turn_index <= 5:
                self._early_latency_count += 1
                self._early_latency_sum += duration
            elif turn_index >= 16:
                self._late_latency_count += 1
                self._late_latency_sum += duration

    def record_recall_probe(self, passed: bool) -> None:
        with self._lock:
            self._recall_probes["pass" if passed else "fail"] += 1

    def record_checkpoint_failure(self) -> None:
        with self._lock:
            self._checkpoint_failures += 1

    def record_product_context_cache(self, *, hits: int, misses: int) -> None:
        with self._lock:
            self._product_context_cache_hits += max(0, int(hits))
            self._product_context_cache_misses += max(0, int(misses))

    def observe_turn(
        self,
        *,
        route: str,
        llm_call_count: int,
        springboot_call_count: int,
        warnings: list[str],
        stage_latencies_ms: dict[str, float],
    ) -> None:
        allowed_stages = {
            "start", "load_context", "understand_query", "route_intent",
            "text_search", "image_search", "hybrid_search", "clarification",
            "memory_recall", "conversation_reply", "out_of_catalog_reply",
            "product_context", "generate_reply", "save_context", "total",
        }
        with self._lock:
            self._routes[route or "unknown"] += 1
            self._llm_calls += max(0, int(llm_call_count))
            self._springboot_calls += max(0, int(springboot_call_count))
            for warning in warnings:
                if any(marker in warning for marker in ("fallback", "failed", "unavailable")):
                    self._fallbacks[warning] += 1
            for stage, duration_ms in stage_latencies_ms.items():
                if stage not in allowed_stages:
                    continue
                duration = max(0.0, float(duration_ms)) / 1000.0
                self._stage_latency_count[stage] += 1
                self._stage_latency_sum[stage] += duration
                self._stage_latency_max[stage] = max(
                    self._stage_latency_max.get(stage, 0.0),
                    duration,
                )

    def render_prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP ecommerce_assistant_conversation_turn_index Last observed conversation turn index.",
                "# TYPE ecommerce_assistant_conversation_turn_index gauge",
                f"ecommerce_assistant_conversation_turn_index {self._turn_index}",
                "# HELP ecommerce_assistant_recent_message_count Last observed recent transcript size.",
                "# TYPE ecommerce_assistant_recent_message_count gauge",
                f"ecommerce_assistant_recent_message_count {self._recent_message_count}",
                "# HELP ecommerce_assistant_summary_chars Last observed conversation summary size.",
                "# TYPE ecommerce_assistant_summary_chars gauge",
                f"ecommerce_assistant_summary_chars {self._summary_chars}",
                "# HELP ecommerce_assistant_summary_compaction_count Last observed compaction count.",
                "# TYPE ecommerce_assistant_summary_compaction_count gauge",
                f"ecommerce_assistant_summary_compaction_count {self._summary_compaction_count}",
                "# HELP ecommerce_assistant_memory_source_used_total Memory sources included in assistant context.",
                "# TYPE ecommerce_assistant_memory_source_used_total counter",
            ]
            for source, value in sorted(self._memory_sources.items()):
                lines.append(
                    f'ecommerce_assistant_memory_source_used_total{{source="{source}"}} {value}'
                )
            lines.extend(
                [
                    "# HELP ecommerce_assistant_reference_resolution_source_total Reference resolutions by bounded source.",
                    "# TYPE ecommerce_assistant_reference_resolution_source_total counter",
                ]
            )
            for source, value in sorted(self._reference_sources.items()):
                lines.append(
                    "ecommerce_assistant_reference_resolution_source_total"
                    f'{{source="{source}"}} {value}'
                )
            lines.extend(
                [
                    "# HELP ecommerce_assistant_memory_recall_probe_total Recall probe outcomes.",
                    "# TYPE ecommerce_assistant_memory_recall_probe_total counter",
                ]
            )
            for outcome, value in sorted(self._recall_probes.items()):
                lines.append(
                    f'ecommerce_assistant_memory_recall_probe_total{{outcome="{outcome}"}} {value}'
                )
            lines.extend(
                [
                    "# HELP ecommerce_assistant_checkpoint_failures_total Checkpoint read/write failures.",
                    "# TYPE ecommerce_assistant_checkpoint_failures_total counter",
                    f"ecommerce_assistant_checkpoint_failures_total {self._checkpoint_failures}",
                    "# HELP ecommerce_assistant_memory_alert Conversational-memory alert conditions.",
                    "# TYPE ecommerce_assistant_memory_alert gauge",
                    "ecommerce_assistant_memory_alert"
                    f'{{type="summary_hard_limit"}} {int(self._summary_limit_streak >= 3)}',
                    "ecommerce_assistant_memory_alert"
                    f'{{type="checkpoint_failure"}} {int(self._checkpoint_failures > 0)}',
                    "ecommerce_assistant_memory_alert"
                    f'{{type="recall_probe"}} {int(self._recall_probes["fail"] > 0)}',
                    "ecommerce_assistant_memory_alert"
                    f'{{type="session_latency_growth"}} {int(self._latency_growth_alert())}',
                    "# HELP ecommerce_assistant_product_context_cache_total Product context cache outcomes.",
                    "# TYPE ecommerce_assistant_product_context_cache_total counter",
                    "ecommerce_assistant_product_context_cache_total"
                    f'{{outcome="hit"}} {self._product_context_cache_hits}',
                    "ecommerce_assistant_product_context_cache_total"
                    f'{{outcome="miss"}} {self._product_context_cache_misses}',
                    "# HELP ecommerce_assistant_llm_calls_total LLM calls made by assistant turns.",
                    "# TYPE ecommerce_assistant_llm_calls_total counter",
                    f"ecommerce_assistant_llm_calls_total {self._llm_calls}",
                    "# HELP ecommerce_assistant_springboot_calls_total Spring Boot calls made by assistant turns.",
                    "# TYPE ecommerce_assistant_springboot_calls_total counter",
                    f"ecommerce_assistant_springboot_calls_total {self._springboot_calls}",
                    "# HELP ecommerce_assistant_route_total Assistant turns by route.",
                    "# TYPE ecommerce_assistant_route_total counter",
                    "# HELP ecommerce_assistant_fallback_total Assistant fallbacks by reason.",
                    "# TYPE ecommerce_assistant_fallback_total counter",
                    "# HELP ecommerce_assistant_stage_latency_seconds Assistant stage latency.",
                    "# TYPE ecommerce_assistant_stage_latency_seconds summary",
                ]
            )
            for route, value in sorted(self._routes.items()):
                lines.append(
                    f'ecommerce_assistant_route_total{{route="{route}"}} {value}'
                )
            for reason, value in sorted(self._fallbacks.items()):
                lines.append(
                    f'ecommerce_assistant_fallback_total{{reason="{reason}"}} {value}'
                )
            for stage, count in sorted(self._stage_latency_count.items()):
                lines.append(
                    "ecommerce_assistant_stage_latency_seconds_count"
                    f'{{stage="{stage}"}} {count}'
                )
                lines.append(
                    "ecommerce_assistant_stage_latency_seconds_sum"
                    f'{{stage="{stage}"}} {self._stage_latency_sum[stage]}'
                )
                lines.append(
                    "ecommerce_assistant_stage_latency_seconds_max"
                    f'{{stage="{stage}"}} {self._stage_latency_max[stage]}'
                )
            return "\n".join(lines) + "\n"

    def _latency_growth_alert(self) -> bool:
        if self._early_latency_count < 5 or self._late_latency_count < 5:
            return False
        early_mean = self._early_latency_sum / self._early_latency_count
        late_mean = self._late_latency_sum / self._late_latency_count
        return late_mean > max(early_mean * 2.0, early_mean + 1.0)

    def reset(self) -> None:
        with self._lock:
            self._observations = 0
            self._turn_index = 0
            self._recent_message_count = 0
            self._summary_chars = 0
            self._summary_compaction_count = 0
            self._memory_sources.clear()
            self._reference_sources.clear()
            self._recall_probes.clear()
            self._checkpoint_failures = 0
            self._summary_limit_streak = 0
            self._early_latency_count = 0
            self._early_latency_sum = 0.0
            self._late_latency_count = 0
            self._late_latency_sum = 0.0
            self._product_context_cache_hits = 0
            self._product_context_cache_misses = 0
            self._routes.clear()
            self._llm_calls = 0
            self._springboot_calls = 0
            self._fallbacks.clear()
            self._stage_latency_count.clear()
            self._stage_latency_sum.clear()
            self._stage_latency_max.clear()


assistant_metrics = AssistantMetrics()
