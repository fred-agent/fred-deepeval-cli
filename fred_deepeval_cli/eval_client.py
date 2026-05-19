from __future__ import annotations

import argparse

import httpx

from fred_deepeval_cli.trace_sources import (
    NativeEvalTraceSource,
    PrismAdaptedTraceSource,
)


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
    native = NativeEvalTraceSource()
    adapted = PrismAdaptedTraceSource()

    if args.trace_mode == "native":
        return native.fetch_trace(args)

    if args.trace_mode == "adapted":
        return adapted.fetch_trace(args)

    try:
        return native.fetch_trace(args)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code not in {404, 405}:
            raise
    except RuntimeError:
        pass

    return adapted.fetch_trace(args)
