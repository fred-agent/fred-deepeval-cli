from __future__ import annotations

import argparse
import json
from numbers import Number
from pathlib import Path
from types import SimpleNamespace
import uuid

from fred_deepeval_cli.classify import classify_turn
from fred_deepeval_cli.eval_client import fetch_trace
from fred_deepeval_cli.structural_checks import build_structural_checks

DEFAULT_SCENARIOS_PATH = (
    Path(__file__).resolve().parents[1] / "tests" / "sql_scenarios.json"
)


def load_scenarios(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_expected_flow(checks: dict, expected_flow: dict) -> list[str]:
    failures: list[str] = []

    expected_schema_context = expected_flow.get("schema_context")
    if expected_schema_context is not None:
        actual_schema_context = checks.get("sql_schema_context_present_ok")
        if actual_schema_context != expected_schema_context:
            failures.append(
                "schema_context "
                f"expected={expected_schema_context} actual={actual_schema_context}"
            )

    expected_query_executed = expected_flow.get("query_executed")
    if expected_query_executed is not None:
        actual_query_executed = checks.get("sql_query_executed_ok")
        if actual_query_executed != expected_query_executed:
            failures.append(
                "query_executed "
                f"expected={expected_query_executed} actual={actual_query_executed}"
            )

    return failures


def extract_latest_query_result(trace: dict) -> dict | None:
    for step in reversed(trace.get("steps", [])):
        if step.get("kind") != "tool_result":
            continue
        if step.get("tool_name") != "read_query":
            continue
        if step.get("is_error"):
            continue

        content = step.get("content")
        if isinstance(content, dict):
            return content

        if isinstance(content, str) and content.strip():
            if content.lstrip().startswith("Error:"):
                continue
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                return parsed
            return None

    return None


def values_match(expected: object, actual: object, *, tolerance: float = 0.01) -> bool:
    if isinstance(expected, Number) and isinstance(actual, Number):
        return abs(float(expected) - float(actual)) <= tolerance

    if isinstance(expected, str) and isinstance(actual, str):
        return expected.casefold() == actual.casefold()

    return expected == actual


def row_matches_expected_values(actual_row: dict, expected_row: dict) -> bool:
    for key, expected_value in expected_row.items():
        if key not in actual_row:
            return False
        if not values_match(expected_value, actual_row.get(key)):
            return False
    return True


def compare_expected_values(trace: dict, expected_values: dict) -> list[str]:
    failures: list[str] = []
    if not expected_values:
        return failures

    output = trace.get("output") or ""
    for snippet in expected_values.get("output_contains", []):
        if snippet not in output:
            failures.append(f"output missing snippet={snippet!r}")

    expects_query_result = any(
        key in expected_values for key in ("row_count", "first_row", "contains_rows")
    )
    query_result = extract_latest_query_result(trace)
    rows = query_result.get("rows", []) if isinstance(query_result, dict) else []
    
    expected_sql_fragments = expected_values.get("sql_query_contains", [])
    actual_sql_query = ""
    if isinstance(query_result, dict):
        actual_sql_query = query_result.get("sql_query", "") or ""

    for fragment in expected_sql_fragments:
        if fragment not in actual_sql_query:
            failures.append(
                f"sql_query missing fragment={fragment!r}"
            )

    if expects_query_result and query_result is None:
        failures.append("expected query result but no successful read_query result was found")
        return failures

    if expected_values.get("row_count") is not None:
        expected_row_count = expected_values["row_count"]
        actual_row_count = len(rows)
        if actual_row_count != expected_row_count:
            failures.append(
                f"row_count expected={expected_row_count} actual={actual_row_count}"
            )

    expected_first_row = expected_values.get("first_row")
    if expected_first_row is not None:
        if not rows:
            failures.append("first_row expected but query returned no rows")
        elif not row_matches_expected_values(rows[0], expected_first_row):
            failures.append(
                f"first_row expected={expected_first_row} actual={rows[0]}"
            )

    expected_rows = expected_values.get("contains_rows", [])
    for expected_row in expected_rows:
        if not any(row_matches_expected_values(actual_row, expected_row) for actual_row in rows):
            failures.append(f"expected row not found: {expected_row}")

    return failures


def summarize_observed_values(trace: dict) -> dict:
    query_result = extract_latest_query_result(trace)
    rows = query_result.get("rows", []) if isinstance(query_result, dict) else []
    sql_query = query_result.get("sql_query") if isinstance(query_result, dict) else None

    return {
        "sql_query": sql_query,
        "query_row_count": len(rows),
        "query_first_row": rows[0] if rows else None,
    }



def evaluate_scenario(
    scenario: dict,
    *,
    base_url: str,
    agent_id: str,
    user_id: str,
    team_id: str | None,
    access_token: str | None,
) -> tuple[str, dict]:
    session_id = f"{scenario['id']}-{uuid.uuid4().hex[:8]}"


    args = SimpleNamespace(
        base_url=base_url,
        agent_id=agent_id,
        input=scenario["input"],
        session_id=session_id,
        user_id=user_id,
        team_id=team_id,
        access_token=access_token,
        search_policy=None,
    )

    trace = fetch_trace(args)
    outcome = classify_turn(trace)
    checks = build_structural_checks(trace)

    failures = compare_expected_flow(checks, scenario.get("expected_flow", {}))
    failures.extend(compare_expected_values(trace, scenario.get("expected_values", {})))

    result = {
        "id": scenario["id"],
        "input": scenario["input"],
        "outcome": outcome,
        "profile": checks.get("profile"),
        "expected_flow": scenario.get("expected_flow", {}),
        "expected_values": scenario.get("expected_values", {}),
        "observed_checks": {
            "sql_schema_context_present_ok": checks.get(
                "sql_schema_context_present_ok"
            ),
            "sql_query_executed_ok": checks.get("sql_query_executed_ok"),
            "sql_tool_used_ok": checks.get("sql_tool_used_ok"),
            "sql_no_execution_error_ok": checks.get("sql_no_execution_error_ok"),
        },
        "observed_values": summarize_observed_values(trace),
        "pass": not failures,
        "failures": failures,
    }
    return outcome, result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SQL evaluation scenarios against fred.github.sql_expert."
    )
    parser.add_argument("--base-url", required=True, help="Fred pod base URL.")
    parser.add_argument(
        "--agent-id",
        default="fred.github.sql_expert",
        help="Agent identifier.",
    )
    parser.add_argument(
        "--user-id",
        default="alice",
        help="Runtime user identifier.",
    )
    parser.add_argument("--team-id", help="Optional runtime team identifier.")
    parser.add_argument("--access-token", help="Optional bearer token.")
    parser.add_argument(
        "--scenarios",
        default=str(DEFAULT_SCENARIOS_PATH),
        help="Path to sql_scenarios.json.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    scenarios_path = Path(args.scenarios)
    scenarios = load_scenarios(scenarios_path)

    results: list[dict] = []
    has_failures = False

    for scenario in scenarios:
        _, result = evaluate_scenario(
            scenario,
            base_url=args.base_url,
            agent_id=args.agent_id,
            user_id=args.user_id,
            team_id=args.team_id,
            access_token=args.access_token,
        )
        results.append(result)
        if not result["pass"]:
            has_failures = True

    print(json.dumps({"results": results}, indent=2, ensure_ascii=False))
    return 1 if has_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
