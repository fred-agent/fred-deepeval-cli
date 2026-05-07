from __future__ import annotations

import os

from fred_deepeval_cli.deepeval_adapter import trace_to_test_case
from deepeval.models.llms import GPTModel, LiteLLMModel
from fred_deepeval_cli.config_loader import load_configuration
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric


def build_judge_model():
    config = load_configuration()
    provider = config.judge.provider
    model_name = config.judge.model

    if provider == "litellm":
        api_key = os.environ.get("LITELLM_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing LITELLM_API_KEY in environment/.env for the litellm judge."
            )

        return LiteLLMModel(
            model=model_name,
            api_key=api_key,
            base_url=config.judge.api_base,
        )

    if provider == "openai":
        return GPTModel(model=model_name)

    raise ValueError(f"Unsupported judge provider: {provider}")

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
