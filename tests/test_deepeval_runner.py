from __future__ import annotations

from unittest.mock import patch

from fred_deepeval_cli.deepeval_runner import score_trace
from fred_deepeval_cli.test_helpers import make_trace


class FakeMetric:
    def __init__(self, model=None) -> None:
        self.model = model
        self.score = None
        self.success = None
        self.reason = None

    def measure(self, test_case) -> None:
        self.score = 1.0
        self.success = True
        self.reason = None


class FakeAnswerMetric(FakeMetric):
    pass


class FakeFaithfulnessMetric(FakeMetric):
    pass


@patch("fred_deepeval_cli.deepeval_runner.build_judge_model")
@patch("fred_deepeval_cli.deepeval_runner.FaithfulnessMetric", new=FakeFaithfulnessMetric)
@patch("fred_deepeval_cli.deepeval_runner.AnswerRelevancyMetric", new=FakeAnswerMetric)
def test_score_trace_without_retrieval_context_only_uses_answer_relevancy(
    mock_build_judge_model,
) -> None:
    mock_build_judge_model.return_value = object()

    result = score_trace(
        make_trace(
            retrieval_context=[],
            output="Echo: echo bonjour",
        )
    )

    metric_names = [metric["name"] for metric in result["metrics"]]

    assert metric_names == ["FakeAnswerMetric"]


@patch("fred_deepeval_cli.deepeval_runner.build_judge_model")
@patch("fred_deepeval_cli.deepeval_runner.FaithfulnessMetric", new=FakeFaithfulnessMetric)
@patch("fred_deepeval_cli.deepeval_runner.AnswerRelevancyMetric", new=FakeAnswerMetric)
def test_score_trace_with_retrieval_context_adds_faithfulness(
    mock_build_judge_model,
) -> None:
    mock_build_judge_model.return_value = object()

    result = score_trace(
        make_trace(
            agent_id="fred.github.rag_expert",
            output="Réponse fondée sur le contexte.",
            retrieval_context=["chunk-1"],
            tools_called=["knowledge_search"],
        )
    )

    metric_names = [metric["name"] for metric in result["metrics"]]

    assert "FakeAnswerMetric" in metric_names
    assert "FakeFaithfulnessMetric" in metric_names
