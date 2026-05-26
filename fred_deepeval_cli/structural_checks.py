from __future__ import annotations

import re


# RAG-specific structural checks.
def rag_tool_used_ok(trace: dict) -> bool:
    return "knowledge_search" in trace.get("tools_called", [])


def rag_context_nonempty_ok(trace: dict) -> bool:
    return bool(trace.get("retrieval_context"))

# SQL-specific structural checks.
def _tool_steps(trace: dict, kind: str, tool_name: str) -> list[dict]:
    return [
        step
        for step in trace.get("steps", [])
        if step.get("kind") == kind and step.get("tool_name") == tool_name
    ]


def _has_tool_call(trace: dict, tool_name: str) -> bool:
    return bool(_tool_steps(trace, "tool_call", tool_name))


def _has_successful_tool_result(trace: dict, tool_name: str) -> bool:
    for step in _tool_steps(trace, "tool_result", tool_name):
        if step.get("is_error"):
            continue

        content = step.get("content") or ""
        if isinstance(content, str) and content.strip():
            if not content.lstrip().startswith("Error:"):
                return True

    return False


def sql_query_executed_ok(trace: dict) -> bool:
    return _has_tool_call(trace, "read_query") and _has_successful_tool_result(
        trace, "read_query"
    )


def sql_no_execution_error_ok(trace: dict) -> bool:
    if trace.get("error"):
        return False

    for step in trace.get("steps", []):
        if step.get("kind") == "node_error":
            return False

        if step.get("kind") == "tool_result":
            if step.get("is_error"):
                return False

            content = step.get("content") or ""
            if isinstance(content, str) and content.lstrip().startswith("Error:"):
                return False

    return True

# Final structural-check payload assembly.
def build_structural_checks(trace: dict, preset: str = "default") -> dict:
    checks: dict[str, object] = {
        "preset": preset,
    }

    if preset == "rag":
        checks["rag_tool_used_ok"] = rag_tool_used_ok(trace)
        checks["rag_context_nonempty_ok"] = rag_context_nonempty_ok(trace)
    elif preset == "sql":
        checks["sql_query_executed_ok"] = sql_query_executed_ok(trace)
        checks["sql_no_execution_error_ok"] = sql_no_execution_error_ok(trace)

    return checks