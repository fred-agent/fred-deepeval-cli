from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
import uuid

from fred_deepeval_cli.display import console, render_campaign
from fred_deepeval_cli.classify import classify_turn
from fred_deepeval_cli.deepeval_runner import score_trace
from fred_deepeval_cli.eval_client import fetch_trace
from fred_deepeval_cli.preset_resolver import resolve_preset
from fred_deepeval_cli.structural_checks import build_structural_checks

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[1] / "tests" / "rag_dataset.json"
)

def load_dataset(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_scenario(
    scenario: dict,
    *,
    base_url: str,
    agent_id: str,
    user_id: str,
    team_id: str | None,
    access_token: str | None,
    search_policy: str | None,
) -> dict:
    session_id = f"{scenario['id']}-{uuid.uuid4().hex[:8]}"

    args = SimpleNamespace(
        base_url=base_url,
        agent_id=agent_id,
        input=scenario["input"],
        session_id=session_id,
        user_id=user_id,
        team_id=team_id,
        access_token=access_token,
        search_policy=search_policy,
    )

    trace = fetch_trace(args)
    outcome = classify_turn(trace)
    preset = resolve_preset(trace)
    checks = build_structural_checks(trace, preset=preset)
    expected_output = scenario.get("expected_answer")
    deepeval_result = score_trace(trace, preset=preset, expected_output=expected_output)

    metrics_by_name = {m["name"]: m for m in deepeval_result.get("metrics", [])}

    rag_ok = all(
        v for k, v in checks.items() if k != "preset" and isinstance(v, bool)
    )

    return {
        "id": scenario["id"],
        "input": scenario["input"],
        "outcome": outcome,
        "preset": preset,
        "rag_ok": rag_ok,
        "structural_checks": {k: v for k, v in checks.items() if k != "preset"},
        "metrics": metrics_by_name,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run RAG evaluation scenarios against a fred RAG agent."
    )
    parser.add_argument("--base-url", required=True, help="Fred pod base URL.")
    parser.add_argument(
        "--agent-id", default="fred.github.rag_expert", help="Agent identifier."
    )
    parser.add_argument("--user-id", default="alice", help="Runtime user identifier.")
    parser.add_argument("--team-id", help="Optional runtime team identifier.")
    parser.add_argument("--access-token", help="Optional bearer token.")
    parser.add_argument("--search-policy", default="semantic", help="Search policy.")
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to rag_dataset.json.",
    )
    parser.add_argument(
        "--use-temporal",
        action="store_true",
        default=False,
        help="Run via Temporal in-memory (durable, retriable). Default: mode séquentiel simple.",
    )
    parser.add_argument(
        "--temporal-server",
        default=None,
        help="URL du serveur Temporal (ex: localhost:7233). Si absent, mode in-memory.",
    )
    return parser


def _build_questions(dataset: list[dict], args: argparse.Namespace) -> list[dict]:
    """Prépare les paramètres de chaque question pour Temporal ou le mode simple."""
    questions = []
    for scenario in dataset:
        questions.append({
            "id": scenario["id"],
            "input": scenario["input"],
            "expected_answer": scenario.get("expected_answer"),
            "base_url": args.base_url,
            "agent_id": args.agent_id,
            "session_id": f"{scenario['id']}-{uuid.uuid4().hex[:8]}",
            "user_id": args.user_id,
            "team_id": args.team_id,
            "access_token": args.access_token,
            "search_policy": args.search_policy,
        })
    return questions


def main() -> int:
    args = build_parser().parse_args()
    dataset = load_dataset(Path(args.dataset))

    console.print(f"\n[bold cyan]RAG scenario campaign[/bold cyan] — {len(dataset)} question(s)\n")

    if args.use_temporal:
        from fred_deepeval_cli.dataset_workflow import run_with_temporal, run_with_temporal_server
        questions = _build_questions(dataset, args)
        if args.temporal_server:
            console.print(f"[dim]Mode Temporal — serveur : {args.temporal_server}[/dim]\n")
            results = asyncio.run(run_with_temporal_server(questions, args.temporal_server))
        else:
            console.print("[dim]Mode Temporal — in-memory (pas de serveur requis)[/dim]\n")
            results = asyncio.run(run_with_temporal(questions))
    else:
        results = []
        for i, scenario in enumerate(dataset, start=1):
            console.print(f"  [dim]{i}/{len(dataset)}[/dim] {scenario['id']}...")
            result = evaluate_scenario(
                scenario,
                base_url=args.base_url,
                agent_id=args.agent_id,
                user_id=args.user_id,
                team_id=args.team_id,
                access_token=args.access_token,
                search_policy=args.search_policy,
            )
            results.append(result)

    render_campaign(results)
    print(json.dumps({"results": results}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
