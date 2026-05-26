from __future__ import annotations


def resolve_preset(trace: dict, explicit_preset: str = "auto") -> str:
    if explicit_preset != "auto":
        return explicit_preset

    agent_tags = set(trace.get("agent_tags", []))

    if "rag" in agent_tags:
        return "rag"

    if "sql" in agent_tags:
        return "sql"

    return "default"