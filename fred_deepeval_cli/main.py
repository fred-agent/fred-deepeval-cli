from __future__ import annotations

import argparse
import json

import httpx

from fred_deepeval_cli.classify import classify_turn
from fred_deepeval_cli.deepeval_runner import score_trace



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

def fetch_trace(args: argparse.Namespace) -> dict:
    from fred_runtime.cli.pod_client import AgentPodClient

    with httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0, read=None)) as http_client:
        client = AgentPodClient(
            base_url=args.base_url.rstrip("/"),
            http_client=http_client,
        )

        return client.evaluate(
            agent_id=args.agent_id,
            message=args.input,
            session_id=args.session_id,
            user_id=args.user_id,
            team_id=args.team_id,
        )

def run_evaluate(args: argparse.Namespace) -> int:
    trace = fetch_trace(args)
    outcome = classify_turn(trace)

    payload = {
        "outcome": outcome,
        "trace": trace,
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if outcome == "execution_error":
        return 1

    return 0

def run_score(args: argparse.Namespace) -> int:
    trace = fetch_trace(args)
    outcome = classify_turn(trace)
    deepeval_results = score_trace(trace)

    payload = {
        "outcome": outcome,
        "trace": trace,
        "deepeval": deepeval_results,
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
