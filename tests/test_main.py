from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

from fred_deepeval_cli.main import run_evaluate, run_score
from fred_deepeval_cli.test_helpers import make_response, make_trace




@patch("httpx.Client.post")
def test_run_evaluate_success(mock_post: MagicMock, capsys) -> None:
    mock_post.return_value = make_response(
        make_trace(
            session_id="eval-001",
            agent_id="fred.test.assistant",
            input="echo bonjour",
            output="Echo: echo bonjour",
        )
    )

    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="fred.test.assistant",
        input="echo bonjour",
        session_id="eval-001",
        user_id="alice",
        team_id=None,
        access_token=None,
        search_policy=None,
    )

    exit_code = run_evaluate(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["outcome"] == "success"
    assert payload["trace"]["agent_id"] == "fred.test.assistant"


@patch("httpx.Client.post")
def test_run_evaluate_execution_error(mock_post: MagicMock, capsys) -> None:
    mock_post.return_value = make_response(
        make_trace(
            session_id="eval-002",
            agent_id="fred.github.rag_expert",
            input="What capabilities does fred.github.rag_expert have?",
            output=None,
            error="Agent runtime_context has no access_token and refresh failed.",
            latency_ms=456,
            finish_reason="error",
            steps=[
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
            retrieval_context=[],
            tools_called=["knowledge_search"],
        )
    )
    
    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="fred.github.rag_expert",
        input="What capabilities does fred.github.rag_expert have?",
        session_id="eval-002",
        user_id="alice",
        team_id=None,
        access_token=None,
        search_policy=None,
    )
    
    exit_code = run_evaluate(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["outcome"] == "execution_error"
    assert payload["trace"]["tools_called"] == ["knowledge_search"]

@patch("httpx.Client.post")
def test_run_evaluate_degraded(mock_post: MagicMock, capsys) -> None:
    mock_post.return_value = make_response(
        make_trace(
            session_id="eval-003",
            agent_id="general-assistant",
            input="Show me the Prometheus metrics for the last 24 hours.",
            output="I was unable to retrieve live Prometheus metrics. Using cached data instead.",
            latency_ms=789,
            model_name="mistral-medium-2508",
            token_usage={"input_tokens": 388, "output_tokens": 61},
            finish_reason="stop",
            steps=[
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
            retrieval_context=[],
            tools_called=["knowledge.prometheus.query_range"],
        )
    )

    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="general-assistant",
        input="Show me the Prometheus metrics for the last 24 hours.",
        session_id="eval-003",
        user_id="alice",
        team_id=None,
        access_token=None,
        search_policy=None,
    )

    exit_code = run_evaluate(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["outcome"] == "degraded"
    assert payload["trace"]["tools_called"] == ["knowledge.prometheus.query_range"]


@patch("httpx.Client.post")
def test_run_evaluate_hitl_blocked(mock_post: MagicMock, capsys) -> None:
    mock_post.return_value = make_response(
        make_trace(
            session_id="eval-004",
            agent_id="bank-transfer-agent",
            input="Transfer 5 000 € from account FR76 to account FR29.",
            output=None,
            latency_ms=943,
            model_name="mistral-medium-2508",
            token_usage={"input_tokens": 271, "output_tokens": 0},
            steps=[
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
            retrieval_context=[
                "risk_score=0.72 | flag=HIGH | reason=unusual_destination_country"
            ],
            tools_called=["bank.risk_guard.score_transfer"],
        )
    )

    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="bank-transfer-agent",
        input="Transfer 5 000 € from account FR76 to account FR29.",
        session_id="eval-004",
        user_id="alice",
        team_id=None,
        access_token=None,
        search_policy=None,
    )

    exit_code = run_evaluate(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["outcome"] == "hitl_blocked"
    assert payload["trace"]["tools_called"] == ["bank.risk_guard.score_transfer"]

@patch("fred_deepeval_cli.main.score_trace")
@patch("httpx.Client.post")
def test_run_score_without_retrieval_context_uses_general_metric(
    mock_post: MagicMock,
    mock_score_trace: MagicMock,
    capsys,
) -> None:
    mock_post.return_value = make_response(
        make_trace(
            session_id="eval-005",
            agent_id="fred.test.assistant",
            input="echo bonjour",
            output="Echo: echo bonjour",
        )
    )

    mock_score_trace.return_value = {
        "metrics": [
            {
                "name": "AnswerRelevancyMetric",
                "score": 1.0,
                "success": True,
                "reason": None,
            }
        ]
    }

    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="fred.test.assistant",
        input="echo bonjour",
        session_id="eval-005",
        user_id="alice",
        team_id=None,
        access_token=None,
        search_policy=None,
    )

    exit_code = run_score(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert "deepeval" in payload
    assert payload["deepeval"]["metrics"][0]["name"] == "AnswerRelevancyMetric"


@patch("fred_deepeval_cli.main.score_trace")
@patch("httpx.Client.post")
def test_run_score_with_retrieval_context_includes_faithfulness(
    mock_post: MagicMock,
    mock_score_trace: MagicMock,
    capsys,
) -> None:
    mock_post.return_value = make_response(
        make_trace(
            session_id="eval-006",
            agent_id="fred.github.rag_expert",
            input="What capabilities does fred.github.rag_expert have?",
            output="fred.github.rag_expert can search indexed GitHub knowledge and answer from retrieved context.",
            latency_ms=456,
            finish_reason="stop",
            retrieval_context=[
                "fred.github.rag_expert can search indexed GitHub knowledge using retrieval."
            ],
            tools_called=["knowledge_search"],
        )
    )

    mock_score_trace.return_value = {
        "metrics": [
            {
                "name": "AnswerRelevancyMetric",
                "score": 0.95,
                "success": True,
                "reason": None,
            },
            {
                "name": "FaithfulnessMetric",
                "score": 0.91,
                "success": True,
                "reason": None,
            },
        ]
    }

    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="fred.github.rag_expert",
        input="What capabilities does fred.github.rag_expert have?",
        session_id="eval-006",
        user_id="alice",
        team_id=None,
        access_token=None,
        search_policy=None,
    )

    exit_code = run_score(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert "deepeval" in payload
    metric_names = [metric["name"] for metric in payload["deepeval"]["metrics"]]
    assert "AnswerRelevancyMetric" in metric_names
    assert "FaithfulnessMetric" in metric_names


