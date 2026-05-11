from __future__ import annotations

from fred_deepeval_cli.structural_checks import (
    build_structural_checks,
    sql_no_execution_error_ok,
    sql_query_executed_ok,
    sql_schema_context_present_ok,
    sql_tool_used_ok,
)


def test_sql_tool_used_ok_returns_false_when_no_sql_tool_was_called() -> None:
    trace = {"tools_called": []}

    assert sql_tool_used_ok(trace) is False


def test_sql_tool_used_ok_returns_true_when_list_tabular_datasets_was_called() -> None:
    trace = {"tools_called": ["list_tabular_datasets"]}

    assert sql_tool_used_ok(trace) is True


def test_sql_tool_used_ok_returns_true_when_read_query_was_called() -> None:
    trace = {"tools_called": ["read_query"]}

    assert sql_tool_used_ok(trace) is True


def test_sql_schema_context_present_ok_returns_true_for_successful_dataset_listing() -> None:
    trace = {
        "steps": [
            {
                "kind": "tool_result",
                "tool_name": "list_tabular_datasets",
                "content": "[{\"document_name\": \"commandes.csv\"}]",
                "is_error": False,
            }
        ]
    }

    assert sql_schema_context_present_ok(trace) is True


def test_sql_schema_context_present_ok_returns_false_when_dataset_listing_failed() -> None:
    trace = {
        "steps": [
            {
                "kind": "tool_result",
                "tool_name": "list_tabular_datasets",
                "content": "Error: backend unavailable",
                "is_error": True,
            }
        ]
    }

    assert sql_schema_context_present_ok(trace) is False


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


def test_build_structural_checks_returns_sql_checks_for_sql_expert() -> None:
    trace = {
        "agent_id": "fred.github.sql_expert",
        "tools_called": ["list_tabular_datasets", "read_query"],
        "error": None,
        "steps": [
            {
                "kind": "tool_result",
                "tool_name": "list_tabular_datasets",
                "content": "[{\"document_name\": \"commandes.csv\"}]",
                "is_error": False,
            },
            {
                "kind": "tool_call",
                "tool_name": "read_query",
                "arguments": {"query": "SELECT * FROM commandes LIMIT 10"},
            },
            {
                "kind": "tool_result",
                "tool_name": "read_query",
                "content": "{\"rows\": [{\"id_commande\": 1}]}",
                "is_error": False,
            },
        ],
    }

    checks = build_structural_checks(trace)

    assert checks["profile"] == "sql_basic"
    assert checks["sql_tool_used_ok"] is True
    assert checks["sql_schema_context_present_ok"] is True
    assert checks["sql_query_executed_ok"] is True
    assert checks["sql_no_execution_error_ok"] is True
