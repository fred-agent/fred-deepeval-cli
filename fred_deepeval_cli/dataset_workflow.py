from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker, UnsandboxedWorkflowRunner
from temporalio.testing import WorkflowEnvironment

from fred_deepeval_cli.classify import classify_turn
from fred_deepeval_cli.deepeval_runner import score_trace
from fred_deepeval_cli.eval_client import fetch_trace
from fred_deepeval_cli.preset_resolver import resolve_preset
from fred_deepeval_cli.structural_checks import build_structural_checks


@activity.defn
async def evaluate_question_activity(params: dict) -> dict:
    """Une question = une activity Temporal."""
    args = SimpleNamespace(
        base_url=params["base_url"],
        agent_id=params["agent_id"],
        input=params["input"],
        session_id=params["session_id"],
        user_id=params["user_id"],
        team_id=params.get("team_id"),
        access_token=params.get("access_token"),
        search_policy=params.get("search_policy"),
    )

    try:
        trace = fetch_trace(args)
    except Exception as e:
        return {
            "id": params["id"],
            "input": params["input"],
            "outcome": "error",
            "preset": "unknown",
            "rag_ok": False,
            "structural_checks": {},
            "metrics": {},
            "error": str(e),
        }

    outcome = classify_turn(trace)
    preset = resolve_preset(trace)
    checks = build_structural_checks(trace, preset=preset)
    expected_output = params.get("expected_answer")
    deepeval_result = score_trace(trace, preset=preset, expected_output=expected_output)

    metrics_by_name = {m["name"]: m for m in deepeval_result.get("metrics", [])}
    rag_ok = all(
        v for k, v in checks.items() if k != "preset" and isinstance(v, bool)
    )

    return {
        "id": params["id"],
        "input": params["input"],
        "outcome": outcome,
        "preset": preset,
        "rag_ok": rag_ok,
        "structural_checks": {k: v for k, v in checks.items() if k != "preset"},
        "metrics": metrics_by_name,
    }


@workflow.defn
class RagDatasetWorkflow:
    @workflow.run
    async def run(self, questions: list[dict]) -> list[dict]:
        results = []
        for q in questions:
            result = await workflow.execute_activity(
                evaluate_question_activity,
                q,
                start_to_close_timeout=timedelta(minutes=10),
            )
            results.append(result)
        return results


async def run_with_temporal(questions: list[dict]) -> list[dict]:
    """Lance le workflow en mode in-memory (pas de serveur Temporal requis)."""
    async with await WorkflowEnvironment.start_local() as env:
        async with Worker(
            env.client,
            task_queue="rag-eval",
            workflows=[RagDatasetWorkflow],
            activities=[evaluate_question_activity],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            results: list[dict] = await env.client.execute_workflow(
                RagDatasetWorkflow.run,
                questions,
                id="rag-dataset-eval",
                task_queue="rag-eval",
            )
    return results


async def run_with_temporal_server(questions: list[dict], server_url: str) -> list[dict]:
    """Lance le workflow sur un serveur Temporal réel (production)."""
    client = await Client.connect(server_url)
    async with Worker(
        client,
        task_queue="rag-eval",
        workflows=[RagDatasetWorkflow],
        activities=[evaluate_question_activity],
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        results: list[dict] = await client.execute_workflow(
            RagDatasetWorkflow.run,
            questions,
            id="rag-dataset-eval",
            task_queue="rag-eval",
        )
    return results
