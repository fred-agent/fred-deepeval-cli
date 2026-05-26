from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

from fred_deepeval_cli.main import run_score
from fred_deepeval_cli.test_helpers import make_response, make_trace


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
        "preset": "default",
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
        preset="auto",
    )

    exit_code = run_score(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert "deepeval" in payload
    assert payload["deepeval"]["metrics"][0]["name"] == "AnswerRelevancyMetric"
    assert payload["preset"] == "default"
    assert payload["deepeval"]["preset"] == "default"
    assert payload["structural_checks"]["preset"] == "default"


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
            agent_tags=["rag", "documents", "react"],
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
        "preset": "rag",
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
        preset="auto",
    )

    exit_code = run_score(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert "deepeval" in payload
    metric_names = [metric["name"] for metric in payload["deepeval"]["metrics"]]
    assert "AnswerRelevancyMetric" in metric_names
    assert "FaithfulnessMetric" in metric_names
    assert payload["preset"] == "rag"
    assert payload["deepeval"]["preset"] == "rag"
    assert payload["structural_checks"]["preset"] == "rag"

@patch("fred_deepeval_cli.main.score_trace")
@patch("httpx.Client.post")
def test_run_score_forces_explicit_sql_preset(
    mock_post: MagicMock,
    mock_score_trace: MagicMock,
    capsys,
) -> None:
    mock_post.return_value = make_response(
        make_trace(
            session_id="eval-007",
            agent_id="fred.github.rag_expert",
            agent_tags=["rag", "documents", "react"],
            input="What capabilities does fred.github.rag_expert have?",
            output="fred.github.rag_expert can search indexed GitHub knowledge.",
        )
    )

    mock_score_trace.return_value = {
        "preset": "sql",
        "metrics": [
            {
                "name": "AnswerRelevancyMetric",
                "score": 0.88,
                "success": True,
                "reason": None,
            }
        ],
    }

    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000/fred/agents/v2",
        agent_id="fred.github.rag_expert",
        input="What capabilities does fred.github.rag_expert have?",
        session_id="eval-007",
        user_id="alice",
        team_id=None,
        access_token=None,
        search_policy=None,
        preset="sql",
    )

    exit_code = run_score(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["preset"] == "sql"
    assert payload["deepeval"]["preset"] == "sql"
    assert payload["structural_checks"]["preset"] == "sql"