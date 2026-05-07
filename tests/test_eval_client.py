from __future__ import annotations

import argparse

from fred_deepeval_cli.eval_client import (
    build_eval_payload,
    build_headers,
    build_runtime_context,
)


def test_build_runtime_context_includes_special_overrides() -> None:
    args = argparse.Namespace(
        user_id="alice",
        team_id="team-alpha",
        search_policy="semantic",
    )

    runtime_context = build_runtime_context(args)

    assert runtime_context == {
        "user_id": "alice",
        "team_id": "team-alpha",
        "search_policy": "semantic",
    }


def test_build_eval_payload_includes_runtime_context() -> None:
    args = argparse.Namespace(
        agent_id="fred.github.rag_expert",
        input="Quels sont les trois métriques ?",
        session_id="eval-001",
        user_id="alice",
        team_id="team-alpha",
        search_policy="semantic",
    )

    payload = build_eval_payload(args)

    assert payload == {
        "agent_id": "fred.github.rag_expert",
        "input": "Quels sont les trois métriques ?",
        "session_id": "eval-001",
        "runtime_context": {
            "user_id": "alice",
            "team_id": "team-alpha",
            "search_policy": "semantic",
        },
    }


def test_build_headers_includes_authorization_when_access_token_is_present() -> None:
    args = argparse.Namespace(access_token="token-123")

    headers = build_headers(args)

    assert headers == {
        "Content-Type": "application/json",
        "Authorization": "Bearer token-123",
    }


def test_build_headers_omits_authorization_when_access_token_is_missing() -> None:
    args = argparse.Namespace(access_token=None)

    headers = build_headers(args)

    assert headers == {
        "Content-Type": "application/json",
    }
