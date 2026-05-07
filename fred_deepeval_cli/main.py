from __future__ import annotations

import argparse
import json
import os

from fred_deepeval_cli.classify import classify_turn
from fred_deepeval_cli.deepeval_runner import score_trace
from fred_deepeval_cli.eval_client import (
    build_eval_payload,
    build_headers,
    build_runtime_context,
    fetch_trace,
)
from fred_deepeval_cli.structural_checks import build_structural_checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fred-deepeval-cli",
        description="External CLI for evaluating Fred agent turns.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate one Fred agent turn via /agents/evaluate.",
    )
    add_shared_eval_args(evaluate_parser)

    score_parser = subparsers.add_parser(
        "score",
        help="Evaluate one Fred agent turn and score it with DeepEval.",
    )
    add_shared_eval_args(score_parser)

    return parser


def add_shared_eval_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", required=True, help="Fred pod base URL.")
    parser.add_argument("--agent-id", required=True, help="Agent identifier.")
    parser.add_argument("--input", required=True, help="User input to evaluate.")
    parser.add_argument("--session-id", required=True, help="Session identifier.")
    parser.add_argument("--user-id", required=True, help="Runtime user identifier.")
    parser.add_argument("--team-id", help="Optional runtime team identifier.")
    parser.add_argument(
        "--access-token",
        default=os.environ.get("FRED_ACCESS_TOKEN"),
        help="Optional bearer token for authenticated agent evaluation.",
    )
    parser.add_argument(
        "--search-policy",
        default=os.environ.get("FRED_SEARCH_POLICY"),
        help="Optional runtime search policy override (for example: semantic).",
    )


def build_base_payload(outcome: str, trace: dict) -> dict:
    return {
        "outcome": outcome,
        "trace": trace,
        "structural_checks": build_structural_checks(trace),
        "run_metadata": {},
    }


def run_evaluate(args: argparse.Namespace) -> int:
    trace = fetch_trace(args)
    outcome = classify_turn(trace)

    payload = build_base_payload(outcome, trace)

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if outcome == "execution_error":
        return 1

    return 0


def run_score(args: argparse.Namespace) -> int:
    trace = fetch_trace(args)
    outcome = classify_turn(trace)

    payload = build_base_payload(outcome, trace)

    payload["deepeval"] = score_trace(trace)
    payload["scoring_errors"] = []
    payload["run_metadata"] = {
        "scoring_provider": "litellm",
        "scoring_model": "mistral/mistral-large-latest",
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if outcome == "execution_error":
        return 1

    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "evaluate":
        return run_evaluate(args)

    if args.command == "score":
        return run_score(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
