from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

from fred_deepeval_cli.main import build_parser, run_evaluate


def test_build_parser_parses_evaluate_command() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "evaluate",
            "--base-url",
            "http://127.0.0.1:8000/fred/agents/v2",
            "--agent-id",
            "fred.test.assistant",
            "--input",
            "echo bonjour",
            "--session-id",
            "eval-001",
            "--user-id",
            "alice",
        ]
    )

    assert args.command == "evaluate"
    assert args.base_url == "http://127.0.0.1:8000/fred/agents/v2"
    assert args.agent_id == "fred.test.assistant"
    assert args.input == "echo bonjour"
    assert args.session_id == "eval-001"
    assert args.user_id == "alice"
    assert args.team_id is None


@patch("fred_runtime.cli.pod_client.AgentPodClient")
def test_run_evaluate_success(mock_client_cls: MagicMock, capsys) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.evaluate.return_value = {
        "session_id": "eval-001",
        "agent_id": "fred.test.assistant",
        "input": "echo bonjour",
        "output": "Echo: echo bonjour",
        "error": None,
        "latency_ms": 123,
        "model_name": None,
        "token_usage": None,
        "finish_reason": None,
        "steps": [
            {
                "kind": "final",
                "tool_name": None,
                "call_id": None,
                "arguments": None,
                "content": "Echo: echo bonjour",
                "is_error": None,
                "node_id": None,
                "error_message": None,
            }
        ],
        "retrieval_context": [],
        "tools_called": [],
    }

    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="fred.test.assistant",
        input="echo bonjour",
        session_id="eval-001",
        user_id="alice",
        team_id=None,
    )

    exit_code = run_evaluate(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["outcome"] == "success"
    assert payload["trace"]["agent_id"] == "fred.test.assistant"


@patch("fred_runtime.cli.pod_client.AgentPodClient")
def test_run_evaluate_execution_error(mock_client_cls: MagicMock, capsys) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.evaluate.return_value = {
        "session_id": "eval-002",
        "agent_id": "fred.github.rag_expert",
        "input": "What capabilities does fred.github.rag_expert have?",
        "output": None,
        "error": "Agent runtime_context has no access_token and refresh failed.",
        "latency_ms": 456,
        "model_name": None,
        "token_usage": None,
        "finish_reason": "error",
        "steps": [
            {
                "kind": "tool_call",
                "tool_name": "knowledge_search",
                "call_id": "call-123",
                "arguments": {"query": "fred.github.rag_expert capabilities"},
                "content": None,
                "is_error": None,
                "node_id": None,
                "error_message": None,
            }
        ],
        "retrieval_context": [],
        "tools_called": ["knowledge_search"],
    }

    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="fred.github.rag_expert",
        input="What capabilities does fred.github.rag_expert have?",
        session_id="eval-002",
        user_id="alice",
        team_id=None,
    )

    exit_code = run_evaluate(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["outcome"] == "execution_error"
    assert payload["trace"]["tools_called"] == ["knowledge_search"]

@patch("fred_runtime.cli.pod_client.AgentPodClient")
def test_run_evaluate_degraded(mock_client_cls: MagicMock, capsys) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.evaluate.return_value = {
        "session_id": "eval-003",
        "agent_id": "general-assistant",
        "input": "Show me the Prometheus metrics for the last 24 hours.",
        "output": "I was unable to retrieve live Prometheus metrics. Using cached data instead.",
        "error": None,
        "latency_ms": 789,
        "model_name": "mistral-medium-2508",
        "token_usage": {"input_tokens": 388, "output_tokens": 61},
        "finish_reason": "stop",
        "steps": [
            {
                "kind": "tool_call",
                "tool_name": "knowledge.prometheus.query_range",
                "call_id": "call-789",
                "arguments": {"query": "llm_call_latency_ms", "range": "24h"},
                "content": None,
                "is_error": None,
                "node_id": None,
                "error_message": None,
            },
            {
                "kind": "node_error",
                "tool_name": None,
                "call_id": None,
                "arguments": None,
                "content": None,
                "is_error": None,
                "node_id": "fetch_metrics",
                "error_message": "TimeoutError",
            },
            {
                "kind": "final",
                "tool_name": None,
                "call_id": None,
                "arguments": None,
                "content": "I was unable to retrieve live Prometheus metrics. Using cached data instead.",
                "is_error": None,
                "node_id": None,
                "error_message": None,
            },
        ],
        "retrieval_context": [],
        "tools_called": ["knowledge.prometheus.query_range"],
    }

    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="general-assistant",
        input="Show me the Prometheus metrics for the last 24 hours.",
        session_id="eval-003",
        user_id="alice",
        team_id=None,
    )

    exit_code = run_evaluate(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["outcome"] == "degraded"
    assert payload["trace"]["tools_called"] == ["knowledge.prometheus.query_range"]


@patch("fred_runtime.cli.pod_client.AgentPodClient")
def test_run_evaluate_hitl_blocked(mock_client_cls: MagicMock, capsys) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.evaluate.return_value = {
        "session_id": "eval-004",
        "agent_id": "bank-transfer-agent",
        "input": "Transfer 5 000 € from account FR76 to account FR29.",
        "output": None,
        "error": None,
        "latency_ms": 943,
        "model_name": "mistral-medium-2508",
        "token_usage": {"input_tokens": 271, "output_tokens": 0},
        "finish_reason": None,
        "steps": [
            {
                "kind": "tool_call",
                "tool_name": "bank.risk_guard.score_transfer",
                "call_id": "call-456",
                "arguments": {
                    "from_account": "FR76",
                    "to_account": "FR29",
                    "amount_eur": 5000,
                },
                "content": None,
                "is_error": None,
                "node_id": None,
                "error_message": None,
            },
            {
                "kind": "awaiting_human",
                "tool_name": None,
                "call_id": None,
                "arguments": None,
                "content": None,
                "is_error": None,
                "node_id": None,
                "error_message": None,
            },
        ],
        "retrieval_context": ["risk_score=0.72 | flag=HIGH | reason=unusual_destination_country"],
        "tools_called": ["bank.risk_guard.score_transfer"],
    }

    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="bank-transfer-agent",
        input="Transfer 5 000 € from account FR76 to account FR29.",
        session_id="eval-004",
        user_id="alice",
        team_id=None,
    )

    exit_code = run_evaluate(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["outcome"] == "hitl_blocked"
    assert payload["trace"]["tools_called"] == ["bank.risk_guard.score_transfer"]

