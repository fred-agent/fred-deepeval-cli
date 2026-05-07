from __future__ import annotations

import argparse

import httpx


def build_runtime_context(args: argparse.Namespace) -> dict:
    runtime_context = {"user_id": args.user_id}

    if args.team_id:
        runtime_context["team_id"] = args.team_id

    if args.search_policy:
        runtime_context["search_policy"] = args.search_policy

    return runtime_context


def build_eval_payload(args: argparse.Namespace) -> dict:
    return {
        "agent_id": args.agent_id,
        "input": args.input,
        "session_id": args.session_id,
        "runtime_context": build_runtime_context(args),
    }


def build_headers(args: argparse.Namespace) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}

    if args.access_token:
        headers["Authorization"] = f"Bearer {args.access_token}"

    return headers


def fetch_trace(args: argparse.Namespace) -> dict:
    with httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0, read=None)) as http_client:
        response = http_client.post(
            f"{args.base_url.rstrip('/')}/agents/evaluate",
            json=build_eval_payload(args),
            headers=build_headers(args),
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise RuntimeError("Evaluate response must be a JSON object.")
        return result
