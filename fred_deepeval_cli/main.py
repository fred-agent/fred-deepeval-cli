from __future__ import annotations

import argparse
import json

import httpx

from fred_deepeval_cli.classify import classify_turn


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
    evaluate_parser.add_argument("--base-url", required=True, help="Fred pod base URL.")
    evaluate_parser.add_argument("--agent-id", required=True, help="Agent identifier.")
    evaluate_parser.add_argument("--input", required=True, help="User input to evaluate.")
    evaluate_parser.add_argument("--session-id", required=True, help="Session identifier.")
    evaluate_parser.add_argument("--user-id", required=True, help="Runtime user identifier.")
    evaluate_parser.add_argument("--team-id", help="Optional runtime team identifier.")

    return parser


def run_evaluate(args: argparse.Namespace) -> int:
    from fred_runtime.cli.pod_client import AgentPodClient
    with httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0, read=None)) as http_client:
        client = AgentPodClient(
            base_url=args.base_url.rstrip("/"),
            http_client=http_client,
        )

        trace = client.evaluate(
            agent_id=args.agent_id,
            message=args.input,
            session_id=args.session_id,
            user_id=args.user_id,
            team_id=args.team_id,
        )

    outcome = classify_turn(trace)

    payload = {
        "outcome": outcome,
        "trace": trace,
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

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
