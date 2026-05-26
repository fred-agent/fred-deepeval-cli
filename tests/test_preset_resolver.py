from __future__ import annotations

from fred_deepeval_cli.preset_resolver import resolve_preset


def test_resolve_preset_returns_explicit_value_when_forced() -> None:
    trace = {"agent_tags": ["rag", "documents", "react"]}
    assert resolve_preset(trace, explicit_preset="sql") == "sql"


def test_resolve_preset_returns_rag_from_agent_tags() -> None:
    trace = {"agent_tags": ["rag", "documents", "react"]}
    assert resolve_preset(trace) == "rag"


def test_resolve_preset_returns_sql_from_agent_tags() -> None:
    trace = {"agent_tags": ["sql", "tabular", "react"]}
    assert resolve_preset(trace) == "sql"


def test_resolve_preset_returns_default_when_no_known_tag_is_present() -> None:
    trace = {"agent_tags": ["general", "react"]}
    assert resolve_preset(trace) == "default"