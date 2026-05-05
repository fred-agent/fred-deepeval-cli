from __future__ import annotations

import json
from pathlib import Path

from fred_deepeval_cli.deepeval_adapter import trace_to_test_case


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_trace_to_test_case_maps_input_output_and_retrieval_context() -> None:
    trace = load_fixture("success_with_retrieval.json")

    test_case = trace_to_test_case(trace)

    assert test_case.input == trace["input"]
    assert test_case.actual_output == trace["output"]
    assert test_case.retrieval_context == trace["retrieval_context"]
