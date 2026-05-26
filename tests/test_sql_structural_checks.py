from __future__ import annotations

from fred_deepeval_cli.structural_checks import (
    build_structural_checks,
    sql_no_execution_error_ok,
    sql_query_executed_ok,
)

def test_sql_query_executed_ok_returns_true_when_read_query_succeeds() -> None:
    trace = {
        "steps": [
            {
                "kind": "tool_call",
                "tool_name": "read_query",
                "arguments": {"query": "SELECT 1"},
            },
            {
                "kind": "tool_result",
                "tool_name": "read_query",
                "content": "{\"rows\": [{\"value\": 1}]}",
                "is_error": False,
            },
        ]
    }

    assert sql_query_executed_ok(trace) is True


def test_sql_query_executed_ok_returns_false_when_read_query_was_not_successful() -> None:
    trace = {
        "steps": [
            {
                "kind": "tool_call",
                "tool_name": "read_query",
                "arguments": {"query": "SELECT 1"},
            },
            {
                "kind": "tool_result",
                "tool_name": "read_query",
                "content": "Error: query failed",
                "is_error": True,
            },
        ]
    }

    assert sql_query_executed_ok(trace) is False


def test_sql_no_execution_error_ok_returns_true_for_clean_sql_run() -> None:
    trace = {
        "error": None,
        "steps": [
            {
                "kind": "tool_result",
                "tool_name": "read_query",
                "content": "{\"rows\": [{\"value\": 1}]}",
                "is_error": False,
            }
        ],
    }

    assert sql_no_execution_error_ok(trace) is True


def test_sql_no_execution_error_ok_returns_false_for_global_error() -> None:
    trace = {
        "error": "backend failure",
        "steps": [],
    }

    assert sql_no_execution_error_ok(trace) is False


def test_sql_no_execution_error_ok_returns_false_for_node_error() -> None:
    trace = {
        "error": None,
        "steps": [
            {
                "kind": "node_error",
                "node_id": "execute_sql",
                "error_message": "TimeoutError",
            }
        ],
    }

    assert sql_no_execution_error_ok(trace) is False


def test_sql_no_execution_error_ok_returns_false_for_tool_error() -> None:
    trace = {
        "error": None,
        "steps": [
            {
                "kind": "tool_result",
                "tool_name": "read_query",
                "content": "Error: Error calling read_query. Status code: 500",
                "is_error": True,
            }
        ],
    }

    assert sql_no_execution_error_ok(trace) is False

def test_build_structural_checks_returns_sql_checks_for_sql_preset() -> None:
    trace = {
        "steps": [
            {
                "kind": "tool_call",
                "tool_name": "read_query",
            },
            {
                "kind": "tool_result",
                "tool_name": "read_query",
                "content": "query results",
                "is_error": False,
            },
        ],
        "error": None,
    }

    checks = build_structural_checks(trace, preset="sql")

    assert checks["preset"] == "sql"
    assert checks["sql_query_executed_ok"] is True
    assert checks["sql_no_execution_error_ok"] is True