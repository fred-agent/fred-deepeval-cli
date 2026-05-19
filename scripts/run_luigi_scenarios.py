from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "tests" / "luigi_scenarios.json"


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("luigi_scenarios.json must contain a JSON array.")
    return data


def run_cli_eval(args: argparse.Namespace, scenario: dict[str, Any]) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "fred_deepeval_cli.main",
        "evaluate",
        "--base-url",
        args.base_url,
        "--trace-mode",
        args.trace_mode,
        "--agent-id",
        scenario.get("agent_id", "Luigi v2"),
        "--input",
        scenario["input"],
        "--session-id",
        f"luigi-scenario-{scenario['id']}",
        "--user-id",
        args.user_id,
    ]

    if args.access_token:
        cmd.extend(["--access-token", args.access_token])
    if args.search_policy:
        cmd.extend(["--search-policy", args.search_policy])
    if args.team_id:
        cmd.extend(["--team-id", args.team_id])

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()

    if proc.returncode not in (0, 1):
        raise RuntimeError(
            f"CLI execution failed for scenario {scenario['id']}.\n\n"
            f"STDOUT:\n{stdout or '<empty>'}\n\n"
            f"STDERR:\n{stderr or '<empty>'}"
        )

    start = stdout.find("{")
    if start == -1:
        raise RuntimeError(
            f"No JSON payload found for scenario {scenario['id']}.\n\n"
            f"Return code: {proc.returncode}\n\n"
            f"STDOUT:\n{stdout or '<empty>'}\n\n"
            f"STDERR:\n{stderr or '<empty>'}"
        )

    return json.loads(stdout[start:])



def get_nested_value(payload: dict[str, Any], dotted_key: str) -> Any:
    trace = payload.get("trace", {})
    retrieval_context = trace.get("retrieval_context", [])

    prefixes = {
        "cv.": "CV extrait.",
        "enjeuxBesoins.": "Enjeux et besoins extraits.",
        "prestationFinanciere.": "Prestations financières extraites.",
    }

    source_blob = None
    field_path = dotted_key
    for prefix, marker in prefixes.items():
        if dotted_key.startswith(prefix):
            field_path = dotted_key[len(prefix) :]
            for item in retrieval_context:
                if isinstance(item, str) and marker in item:
                    source_blob = item
                    break
            break

    if source_blob is None:
        return None

    json_start = source_blob.find("{")
    if json_start == -1:
        return None

    try:
        parsed = json.loads(source_blob[json_start:])
    except json.JSONDecodeError:
        return None

    return parsed.get(field_path)


def evaluate_scenario(payload: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    checks = payload.get("structural_checks", {})
    trace = payload.get("trace", {})
    expected_flow = scenario.get("expected_flow", {})
    expected_values = scenario.get("expected_values", {})
    expected_constraints = scenario.get("expected_constraints", {})

    results: dict[str, Any] = {
        "id": scenario["id"],
        "outcome": payload.get("outcome"),
        "checks": {},
        "values": {},
        "constraints": {},
    }

    flow_mapping = {
        "required_tools": "luigi_required_tools_ok",
        "sequence_ok": "luigi_extraction_sequence_ok",
        "fill_template_attempted": "luigi_template_attempted_ok",
        "ppt_generated": "luigi_template_generated_ok",
        "retry_after_validation": "luigi_retry_after_validation_ok",
    }

    for expected_key, expected_value in expected_flow.items():
        check_name = flow_mapping.get(expected_key)
        if not check_name:
            continue
        observed = checks.get(check_name)
        results["checks"][check_name] = {
            "expected": expected_value,
            "observed": observed,
            "ok": observed == expected_value,
        }

    for dotted_key, expected_value in expected_values.items():
        observed = get_nested_value(payload, dotted_key)
        results["values"][dotted_key] = {
            "expected": expected_value,
            "observed": observed,
            "ok": observed == expected_value,
        }

    if "final_output_consistent" in expected_constraints:
        observed = checks.get("luigi_final_output_consistent_ok")
        expected_value = expected_constraints["final_output_consistent"]
        results["constraints"]["final_output_consistent"] = {
            "expected": expected_value,
            "observed": observed,
            "ok": observed == expected_value,
        }

    if "financial_block_zero_or_empty" in expected_constraints:
        observed = get_nested_value(payload, "prestationFinanciere.prixTotal")
        expected_value = expected_constraints["financial_block_zero_or_empty"]
        ok = (observed == 0) if expected_value else True
        results["constraints"]["financial_block_zero_or_empty"] = {
            "expected": expected_value,
            "observed": observed,
            "ok": ok,
        }

    results["trace_session_id"] = trace.get("session_id")
    return results


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)

    def rate(items: list[bool]) -> float:
        return sum(1 for item in items if item) / total if total else 0.0

    return {
        "scenario_count": total,
        "ppt_generation_success_rate": rate(
            [
                r["checks"].get("luigi_template_generated_ok", {}).get("observed") is True
                for r in results
            ]
        ),
        "sequence_ok_rate": rate(
            [
                r["checks"].get("luigi_extraction_sequence_ok", {}).get("observed") is True
                for r in results
            ]
        ),
        "template_validation_recovery_rate": rate(
            [
                r["checks"].get("luigi_retry_after_validation_ok", {}).get("observed") is True
                for r in results
            ]
        ),
        "final_output_consistency_rate": rate(
            [
                r["constraints"].get("final_output_consistent", {}).get("ok") is True
                for r in results
                if "final_output_consistent" in r["constraints"]
            ]
        ),
        "field_exact_match_rate": rate(
            [
                all(item["ok"] for item in r["values"].values()) if r["values"] else True
                for r in results
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Luigi scenario evaluation.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--trace-mode", choices=["adapted", "native", "auto"], default="adapted")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--access-token")
    parser.add_argument("--team-id")
    parser.add_argument("--search-policy", default="semantic")
    parser.add_argument("--scenarios", type=Path, default=SCENARIOS_PATH)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    scenarios = load_scenarios(args.scenarios)

    results = []
    for scenario in scenarios:
        payload = run_cli_eval(args, scenario)
        results.append(evaluate_scenario(payload, scenario))

    report = {
        "summary": summarize(results),
        "results": results,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
