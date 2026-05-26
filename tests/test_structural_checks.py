from __future__ import annotations

from fred_deepeval_cli.structural_checks import (
    build_structural_checks,
    rag_context_nonempty_ok,
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

def test_build_structural_checks_returns_rag_checks_for_rag_preset() -> None:
    trace = {
        "tools_called": ["knowledge_search"],
        "retrieval_context": ["Document 1"],
    }

    checks = build_structural_checks(trace, preset="rag")

    assert checks["preset"] == "rag"
    assert checks["rag_tool_used_ok"] is True
    assert checks["rag_context_nonempty_ok"] is True