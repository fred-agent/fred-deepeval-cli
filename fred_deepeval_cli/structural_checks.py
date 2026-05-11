from __future__ import annotations

import re


# Shared helpers used by multiple structural-check profiles.


def normalize_source_label(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\.(docx|pdf|md|txt|pptx|csv)$", "", value)
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value


def extract_explicit_source_labels(output: str) -> list[str]:
    file_matches = re.findall(
        r"\b[\w.-]+\.(?:docx|pdf|md|txt|pptx|csv)\b",
        output,
        flags=re.IGNORECASE,
    )
    normalized = [normalize_source_label(match) for match in file_matches]
    return list(dict.fromkeys(normalized))


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


# RAG-specific structural checks.


def rag_tool_used_ok(trace: dict) -> bool:
    return "knowledge_search" in trace.get("tools_called", [])


def rag_context_nonempty_ok(trace: dict) -> bool:
    return bool(trace.get("retrieval_context"))


def rag_citations_present_ok(trace: dict) -> bool:
    output = trace.get("output") or ""
    lowered = output.lower()

    markers = [
        "source",
        "sources",
        "document",
        "documents",
        "selon le document",
        "dans les documents",
    ]
    return any(marker in lowered for marker in markers)


def rag_context_count_ok(trace: dict) -> bool:
    count = len(trace.get("retrieval_context", []))
    return 1 <= count <= 8


def rag_no_hallucinated_source_ok(trace: dict) -> bool:
    output = trace.get("output") or ""
    retrieval_context = trace.get("retrieval_context", [])

    cited_sources = extract_explicit_source_labels(output)
    if not cited_sources:
        return True

    retrieval_blob = normalize_source_label("\n".join(retrieval_context))
    return all(source in retrieval_blob for source in cited_sources)


# SQL-specific structural checks.


def sql_tool_used_ok(trace: dict) -> bool:
    tools_called = trace.get("tools_called", [])
    return any(
        tool in tools_called for tool in ("list_tabular_datasets", "read_query")
    )


def sql_schema_context_present_ok(trace: dict) -> bool:
    return _has_successful_tool_result(trace, "list_tabular_datasets")


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


# Profile selection and final structural-check payload assembly.


def build_structural_checks(trace: dict) -> dict:
    agent_id = trace.get("agent_id")
    is_rag = agent_id == "fred.github.rag_expert"
    is_sql = agent_id == "fred.github.sql_expert"

    if is_rag:
        profile = "rag_basic"
    elif is_sql:
        profile = "sql_basic"
    else:
        profile = "default"

    structural_checks = {
        "profile": profile,
        "required_tools_ok": True,
        "retrieval_context_ok": True,
        "expected_outcome_ok": True,
    }

    if is_rag:
        structural_checks["rag_tool_used_ok"] = rag_tool_used_ok(trace)
        structural_checks["rag_context_nonempty_ok"] = rag_context_nonempty_ok(trace)
        structural_checks["rag_citations_present_ok"] = rag_citations_present_ok(trace)
        structural_checks["rag_context_count_ok"] = rag_context_count_ok(trace)
        structural_checks["rag_no_hallucinated_source_ok"] = (
            rag_no_hallucinated_source_ok(trace)
        )

    if is_sql:
        structural_checks["sql_tool_used_ok"] = sql_tool_used_ok(trace)
        structural_checks["sql_schema_context_present_ok"] = (
            sql_schema_context_present_ok(trace)
        )
        structural_checks["sql_query_executed_ok"] = sql_query_executed_ok(trace)
        structural_checks["sql_no_execution_error_ok"] = sql_no_execution_error_ok(
            trace
        )

    return structural_checks
