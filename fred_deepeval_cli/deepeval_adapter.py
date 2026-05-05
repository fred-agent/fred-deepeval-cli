from __future__ import annotations

from deepeval.test_case import LLMTestCase


def trace_to_test_case(trace: dict) -> LLMTestCase:
    return LLMTestCase(
        input=trace.get("input", ""),
        actual_output=trace.get("output") or "",
        retrieval_context=trace.get("retrieval_context", []),
    )
