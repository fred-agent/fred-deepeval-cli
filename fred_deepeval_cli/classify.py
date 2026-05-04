from __future__ import annotations


def classify_turn(trace: dict) -> str:
    steps = trace.get("steps", [])

    if trace.get("error"):
        return "execution_error"

    if any(step.get("kind") == "awaiting_human" for step in steps):
        return "hitl_blocked"

    if any(step.get("kind") == "node_error" for step in steps):
        return "degraded"

    if trace.get("output"):
        return "success"

    return "unknown"
