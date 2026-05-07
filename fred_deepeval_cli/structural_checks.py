from __future__ import annotations

import re


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


def rag_no_hallucinated_source_ok(trace: dict) -> bool:
    output = trace.get("output") or ""
    retrieval_context = trace.get("retrieval_context", [])

    cited_sources = extract_explicit_source_labels(output)
    if not cited_sources:
        return True

    retrieval_blob = normalize_source_label("\n".join(retrieval_context))
    return all(source in retrieval_blob for source in cited_sources)


def build_structural_checks(trace: dict) -> dict:
    is_rag = trace.get("agent_id") == "fred.github.rag_expert"

    structural_checks = {
        "profile": "rag_basic" if is_rag else "default",
        "required_tools_ok": True,
        "retrieval_context_ok": True,
        "expected_outcome_ok": True,
    }

    if is_rag:
        structural_checks["rag_tool_used_ok"] = rag_tool_used_ok(trace)
        structural_checks["rag_context_nonempty_ok"] = rag_context_nonempty_ok(trace)
        structural_checks["rag_citations_present_ok"] = rag_citations_present_ok(trace)
        structural_checks["rag_context_count_ok"] = rag_context_count_ok(trace)
        structural_checks["rag_no_hallucinated_source_ok"] = rag_no_hallucinated_source_ok(trace)

    return structural_checks
