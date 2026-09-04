from ecommerce_search_assistant.core.metrics import AssistantMetrics, SearchMetrics


def test_search_metrics_render_stage_histograms_and_bounded_labels() -> None:
    metrics = SearchMetrics()

    metrics.observe_text_search(
        timings_ms={
            "analyze_ms": 5.0,
            "llm_ms": 0.0,
            "embed_ms": 125.0,
            "qdrant_ms": 25.0,
            "primary_qdrant_ms": 15.0,
            "recovery_qdrant_ms": 10.0,
            "score_ms": 2.0,
            "rerank_ms": 0.0,
        },
        total_ms=160.0,
        llm_used=False,
        recovery_triggered=True,
        result_count=5,
        typo_correction_count=1,
        category_match_type="typo",
        category_filter_relaxed=True,
        recovery_rescued_top5=True,
        top1_lexical_coverage=0.8,
    )
    metrics.record_error("text")
    metrics.observe_text_search(
        timings_ms={"analyze_ms": 2.0},
        total_ms=2.0,
        llm_used=False,
        recovery_triggered=False,
        result_count=0,
        rejection_reason="invalid_catalog_constraint",
    )

    output = metrics.render_prometheus()

    assert 'ecommerce_search_requests_total{mode="text",outcome="success"} 2' in output
    assert 'ecommerce_search_requests_total{mode="text",outcome="error"} 1' in output
    assert 'ecommerce_search_text_path_total{path="fast_path"} 2' in output
    assert (
        'ecommerce_search_recovery_total'
        '{decision="rejected_invalid_catalog_constraint"} 1'
        in output
    )
    assert (
        'ecommerce_search_stage_duration_seconds_count{mode="text",stage="embedding"} 2'
        in output
    )
    assert 'ecommerce_search_result_count_sum{mode="text"} 5' in output
    assert "ecommerce_search_typo_corrections_total 1" in output
    assert 'ecommerce_search_category_match_total{match_type="typo"} 1' in output
    assert 'ecommerce_search_filter_relaxation_total{field="category"} 1' in output
    assert (
        'ecommerce_search_recovery_outcome_total{outcome="rescued_top5"} 1'
        in output
    )
    assert (
        'ecommerce_search_stage_duration_seconds_count'
        '{mode="text",stage="recovery_qdrant"} 1'
        in output
    )
    assert "ecommerce_search_top1_lexical_coverage_count 1" in output


def test_assistant_metrics_render_bounded_memory_metrics_and_alerts() -> None:
    metrics = AssistantMetrics()
    for turn in range(1, 4):
        metrics.observe_memory(
            turn_index=turn,
            recent_message_count=2,
            summary_chars=500,
            summary_compaction_count=turn,
            summary_max_chars=500,
            memory_sources=["structured_active_state", "recent_transcript"],
            reference_resolution_source="named:alpha",
        )
    for turn in range(1, 6):
        metrics.observe_latency(turn_index=turn, duration_seconds=0.1)
    for turn in range(16, 21):
        metrics.observe_latency(turn_index=turn, duration_seconds=2.0)
    metrics.record_recall_probe(False)
    metrics.record_checkpoint_failure()

    output = metrics.render_prometheus()

    assert "ecommerce_assistant_conversation_turn_index 3" in output
    assert "ecommerce_assistant_summary_compaction_count 3" in output
    assert (
        'ecommerce_assistant_memory_source_used_total{source="structured_active_state"} 3'
        in output
    )
    assert (
        'ecommerce_assistant_reference_resolution_source_total{source="named"} 3'
        in output
    )
    assert 'ecommerce_assistant_memory_alert{type="summary_hard_limit"} 1' in output
    assert 'ecommerce_assistant_memory_alert{type="checkpoint_failure"} 1' in output
    assert 'ecommerce_assistant_memory_alert{type="recall_probe"} 1' in output
    assert 'ecommerce_assistant_memory_alert{type="session_latency_growth"} 1' in output


def test_assistant_turn_metrics_include_route_stage_calls_and_cache() -> None:
    metrics = AssistantMetrics()
    metrics.record_product_context_cache(hits=2, misses=1)
    metrics.observe_turn(
        route="memory_recall",
        llm_call_count=0,
        springboot_call_count=0,
        warnings=["llm_reply_fallback"],
        stage_latencies_ms={"memory_recall": 5.0, "total": 8.0},
    )

    output = metrics.render_prometheus()
    assert 'ecommerce_assistant_product_context_cache_total{outcome="hit"} 2' in output
    assert 'ecommerce_assistant_route_total{route="memory_recall"} 1' in output
    assert 'ecommerce_assistant_fallback_total{reason="llm_reply_fallback"} 1' in output
    assert 'ecommerce_assistant_stage_latency_seconds_max{stage="total"} 0.008' in output
