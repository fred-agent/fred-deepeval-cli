from __future__ import annotations

import logging
import os

# LiteLLM et DeepEval produisent des logs ERROR/WARNING sur les retries et
# les JSON invalides — ces cas sont gérés par notre try/except, on les silence.
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("root").setLevel(logging.CRITICAL)

from fred_deepeval_cli.deepeval_adapter import trace_to_test_case
from deepeval.models.llms import GPTModel, LiteLLMModel
from fred_deepeval_cli.config_loader import load_configuration
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
)

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
            request_timeout=120,
            num_retries=0,
        )

    if provider == "openai":
        return GPTModel(model=model_name)

    raise ValueError(f"Unsupported judge provider: {provider}")

def score_trace(trace: dict, preset: str = "default", expected_output: str | None = None) -> dict:
    test_case = trace_to_test_case(trace, expected_output=expected_output)
    judge_model = build_judge_model()
    retrieval_context = trace.get("retrieval_context") or []

    def _metric(cls, **kwargs):
        m = cls(model=judge_model, async_mode=False, **kwargs)
        return m

    metrics = [_metric(AnswerRelevancyMetric)]

    if preset == "rag":
        if retrieval_context:
            metrics.append(_metric(FaithfulnessMetric))
            metrics.append(_metric(ContextualRelevancyMetric))

        if retrieval_context and expected_output:
            metrics.append(_metric(ContextualPrecisionMetric))
            metrics.append(_metric(ContextualRecallMetric))
    results = []

    for metric in metrics:
        try:
            metric.measure(test_case)
            results.append(
                {
                    "name": metric.__class__.__name__,
                    "score": metric.score,
                    "success": metric.success,
                    "reason": getattr(metric, "reason", None),
                }
            )
        except Exception as e:
            results.append(
                {
                    "name": metric.__class__.__name__,
                    "score": None,
                    "success": False,
                    "reason": f"Evaluation error: {e}",
                }
            )

    return {
        "preset": preset,
        "metrics": results,
    }