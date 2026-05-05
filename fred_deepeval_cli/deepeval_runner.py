from __future__ import annotations

import os

from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from fred_deepeval_cli.deepeval_adapter import trace_to_test_case
from deepeval.models.llms import GPTModel, LiteLLMModel


def build_judge_model():
    provider = os.environ.get("DEEPEVAL_JUDGE_PROVIDER", "litellm")
    model_name = os.environ.get("DEEPEVAL_JUDGE_MODEL")

    if provider == "litellm":
        if not model_name:
            model_name = "mistral/mistral-large-latest"
        return LiteLLMModel(
            model=model_name,
            api_key=os.environ["LITELLM_API_KEY"],
            base_url=os.environ.get("LITELLM_API_BASE"),
        )

    if provider == "openai":
        if not model_name:
            model_name = "gpt-4.1-mini"
        return GPTModel(
            model=model_name,
        )

    raise ValueError(f"Unsupported DEEPEVAL_JUDGE_PROVIDER: {provider}")

def score_trace(trace: dict) -> dict:
    test_case = trace_to_test_case(trace)
    judge_model = build_judge_model()

    metrics = [
        AnswerRelevancyMetric(model=judge_model),
    ]

    if trace.get("retrieval_context"):
        metrics.append(FaithfulnessMetric(model=judge_model))

    results = []

    for metric in metrics:
        metric.measure(test_case)
        results.append(
            {
                "name": metric.__class__.__name__,
                "score": metric.score,
                "success": metric.success,
                "reason": getattr(metric, "reason", None),
            }
        )

    return {"metrics": results}
