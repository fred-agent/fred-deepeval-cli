from __future__ import annotations

from scripts.run_sql_scenarios import (
    compare_expected_values,
    extract_latest_query_result,
)


def test_extract_latest_query_result_returns_latest_successful_read_query_result() -> None:
    trace = {
        "steps": [
            {
                "kind": "tool_result",
                "tool_name": "read_query",
                "content": '{"rows": [{"value": 1}]}',
                "is_error": False,
            },
            {
                "kind": "tool_result",
                "tool_name": "read_query",
                "content": '{"rows": [{"value": 2}]}',
                "is_error": False,
            },
        ]
    }

    result = extract_latest_query_result(trace)

    assert result == {"rows": [{"value": 2}]}


def test_compare_expected_values_returns_no_failures_for_matching_row_expectations() -> None:
    trace = {
        "output": "Average order amount: 548.7",
        "steps": [
            {
                "kind": "tool_result",
                "tool_name": "read_query",
                "content": (
                    '{"rows": ['
                    '{"categorie": "mode", "total_revenue": 18634.7300001}, '
                    '{"categorie": "loisirs", "total_revenue": 21146.68}'
                    ']}'
                ),
                "is_error": False,
            }
        ],
    }

    failures = compare_expected_values(
        trace,
        {
            "output_contains": ["548.7"],
            "row_count": 2,
            "contains_rows": [
                {"categorie": "mode", "total_revenue": 18634.73},
                {"categorie": "LOISIRS", "total_revenue": 21146.68},
            ],
        },
    )

    assert failures == []


def test_compare_expected_values_returns_failure_for_mismatched_first_row() -> None:
    trace = {
        "steps": [
            {
                "kind": "tool_result",
                "tool_name": "read_query",
                "content": '{"rows": [{"nom": "Moreau", "total_revenue": 6307.83}]}',
                "is_error": False,
            }
        ]
    }

    failures = compare_expected_values(
        trace,
        {
            "first_row": {"nom": "Petit", "total_revenue": 6307.83},
        },
    )

    assert failures == [
        "first_row expected={'nom': 'Petit', 'total_revenue': 6307.83} actual={'nom': 'Moreau', 'total_revenue': 6307.83}"
    ]


def test_compare_expected_values_returns_failure_when_query_result_is_missing() -> None:
    trace = {"output": "No query was executed.", "steps": []}

    failures = compare_expected_values(trace, {"row_count": 1})

    assert failures == [
        "expected query result but no successful read_query result was found"
    ]
