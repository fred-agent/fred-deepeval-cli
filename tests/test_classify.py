from __future__ import annotations

import json
from pathlib import Path

from fred_deepeval_cli.classify import classify_turn


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_classify_success_rag() -> None:
    trace = load_fixture("success_rag.json")
    assert classify_turn(trace) == "success"


def test_classify_execution_error() -> None:
    trace = load_fixture("execution_error.json")
    assert classify_turn(trace) == "execution_error"


def test_classify_degraded_node_error() -> None:
    trace = load_fixture("degraded_node_error.json")
    assert classify_turn(trace) == "degraded"


def test_classify_hitl_blocked() -> None:
    trace = load_fixture("hitl_blocked.json")
    assert classify_turn(trace) == "hitl_blocked"
