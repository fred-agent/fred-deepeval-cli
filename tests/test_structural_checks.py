from __future__ import annotations

from fred_deepeval_cli.structural_checks import (
    build_structural_checks,
    rag_citations_present_ok,
    rag_context_count_ok,
    rag_context_nonempty_ok,
    rag_no_hallucinated_source_ok,
    rag_tool_used_ok,
)


def test_rag_tool_used_ok_returns_true_when_knowledge_search_was_called() -> None:
    trace = {"tools_called": ["knowledge_search"]}

    assert rag_tool_used_ok(trace) is True


def test_rag_tool_used_ok_returns_false_when_knowledge_search_was_not_called() -> None:
    trace = {"tools_called": []}

    assert rag_tool_used_ok(trace) is False


def test_rag_context_nonempty_ok_returns_false_for_empty_context() -> None:
    trace = {"retrieval_context": []}

    assert rag_context_nonempty_ok(trace) is False


def test_rag_context_nonempty_ok_returns_true_for_nonempty_context() -> None:
    trace = {"retrieval_context": ["chunk-1"]}

    assert rag_context_nonempty_ok(trace) is True


def test_rag_citations_present_ok_returns_true_when_output_mentions_documents() -> None:
    trace = {
        "output": "Ces métriques sont citées dans les documents CIR et le Dossier Technique CIR."
    }

    assert rag_citations_present_ok(trace) is True


def test_rag_citations_present_ok_returns_false_when_output_has_no_source_markers() -> None:
    trace = {
        "output": "Les trois métriques sont Answer relevance, Context relevance et Groundedness."
    }

    assert rag_citations_present_ok(trace) is False


def test_rag_context_count_ok_returns_false_for_empty_context() -> None:
    trace = {"retrieval_context": []}

    assert rag_context_count_ok(trace) is False


def test_rag_context_count_ok_returns_true_for_reasonable_context_size() -> None:
    trace = {"retrieval_context": ["chunk-1", "chunk-2", "chunk-3"]}

    assert rag_context_count_ok(trace) is True


def test_rag_context_count_ok_returns_false_for_too_many_context_items() -> None:
    trace = {
        "retrieval_context": [
            "chunk-1",
            "chunk-2",
            "chunk-3",
            "chunk-4",
            "chunk-5",
            "chunk-6",
            "chunk-7",
            "chunk-8",
            "chunk-9",
        ]
    }

    assert rag_context_count_ok(trace) is False


def test_rag_no_hallucinated_source_ok_returns_true_when_no_explicit_source_is_cited() -> None:
    trace = {
        "output": "Les documents mentionnent plusieurs verrous liés à l’évaluation et à la transparence.",
        "retrieval_context": [
            "Les documents mentionnent plusieurs verrous liés à l’évaluation et à la transparence."
        ],
    }

    assert rag_no_hallucinated_source_ok(trace) is True


def test_rag_no_hallucinated_source_ok_returns_true_when_cited_source_is_in_context() -> None:
    trace = {
        "output": "Source : CIR_TSN_2024_MARTO.docx",
        "retrieval_context": [
            "Extrait du document CIR_TSN_2024_MARTO concernant les verrous du système."
        ],
    }

    assert rag_no_hallucinated_source_ok(trace) is True


def test_rag_no_hallucinated_source_ok_returns_false_when_cited_source_is_missing_from_context() -> None:
    trace = {
        "output": "Source : CIR_2025_SECRET.docx",
        "retrieval_context": [
            "Extrait du document CIR_TSN_2024_MARTO concernant les verrous du système."
        ],
    }

    assert rag_no_hallucinated_source_ok(trace) is False


def test_build_structural_checks_returns_rag_profile_for_rag_expert() -> None:
    trace = {
        "agent_id": "fred.github.rag_expert",
        "tools_called": ["knowledge_search"],
        "retrieval_context": [
            "Extrait du document CIR_TSN_2024_MARTO concernant les verrous du systeme.",
            "Autre extrait utile.",
        ],
        "output": "Source : CIR_TSN_2024_MARTO.docx",
    }

    checks = build_structural_checks(trace)

    assert checks["profile"] == "rag_basic"
    assert checks["rag_tool_used_ok"] is True
    assert checks["rag_context_nonempty_ok"] is True
    assert checks["rag_citations_present_ok"] is True
    assert checks["rag_context_count_ok"] is True
    assert checks["rag_no_hallucinated_source_ok"] is True
