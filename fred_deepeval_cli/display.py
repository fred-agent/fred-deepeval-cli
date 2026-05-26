from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

console = Console(stderr=True)


def _check_icon(value: object) -> str:
    return "✅" if value is True else "❌"


def _outcome_text(outcome: str) -> Text:
    if outcome == "execution_error":
        return Text(f"  {outcome}", style="bold red")
    return Text(f"  {outcome}", style="bold green")


def _check_detail(name: str, trace: dict) -> str:
    """Retourne la valeur concrète observée dans la trace pour chaque check."""
    if name == "rag_tool_used_ok":
        tools = trace.get("tools_called", [])
        return ", ".join(tools) if tools else "aucun outil appelé"

    if name == "rag_context_nonempty_ok":
        chunks = trace.get("retrieval_context", [])
        return f"{len(chunks)} chunk(s)" if chunks else "retrieval_context vide"

    if name == "sql_query_executed_ok":
        steps = trace.get("steps", [])
        calls = [s for s in steps if s.get("kind") == "tool_call" and s.get("tool_name") == "read_query"]
        return f"read_query appelé {len(calls)} fois" if calls else "read_query non appelé"

    if name == "sql_no_execution_error_ok":
        error = trace.get("error")
        return f"erreur : {error}" if error else "aucune erreur détectée"

    return "—"


def render_score(payload: dict) -> None:
    trace: dict = payload.get("trace", {})
    outcome: str = payload.get("outcome", "unknown")
    preset: str = payload.get("preset", "default")
    structural: dict = payload.get("structural_checks", {})
    deepeval: dict = payload.get("deepeval", {})
    run_meta: dict = payload.get("run_metadata", {})
    errors: list = payload.get("scoring_errors", [])

    # ── Header ──────────────────────────────────────────────────────────────
    header = Table.grid(padding=(0, 2))
    header.add_column(style="bold cyan")
    header.add_column()
    header.add_row("Agent", trace.get("agent_id", "—"))
    header.add_row("Session", trace.get("session_id", "—"))
    header.add_row("User", trace.get("user_id", "—"))
    header.add_row("Preset", preset)
    header.add_row("Input", trace.get("input", "—"))

    console.print()
    console.print(Panel(header, title="[bold]fred-deepeval-cli[/bold]", border_style="cyan"))

    # ── Output agent ────────────────────────────────────────────────────────
    agent_output = trace.get("output") or "—"
    console.print(Panel(agent_output, title="Output", border_style="yellow"))

    # ── Outcome ─────────────────────────────────────────────────────────────
    console.print(Panel(
        _outcome_text(outcome),
        title="Outcome",
        border_style="green" if outcome != "execution_error" else "red",
    ))

    # ── Structural Checks ───────────────────────────────────────────────────
    check_items = {k: v for k, v in structural.items() if k != "preset"}
    if check_items:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta")
        table.add_column("Check", style="cyan")
        table.add_column("", justify="center")
        table.add_column("Observé dans la trace", style="dim", no_wrap=False, max_width=50)

        for name, value in check_items.items():
            table.add_row(name, _check_icon(value), _check_detail(name, trace))

        console.print(Panel(table, title=f"Structural Checks [{preset}]", border_style="magenta"))

    # ── DeepEval Metrics ────────────────────────────────────────────────────
    metrics: list[dict] = deepeval.get("metrics", [])
    if metrics:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold blue")
        table.add_column("Metric", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("", justify="center")
        table.add_column("Reason", style="dim", no_wrap=False, max_width=60)

        for m in metrics:
            score_val = m.get("score")
            score_str = f"{score_val:.2f}" if isinstance(score_val, float) else str(score_val)
            table.add_row(
                m.get("name", "—"),
                score_str,
                _check_icon(m.get("success")),
                m.get("reason") or "—",
            )

        console.print(Panel(table, title="DeepEval Metrics", border_style="blue"))

    # ── Erreurs ─────────────────────────────────────────────────────────────
    if errors:
        console.print(Panel(
            "\n".join(str(e) for e in errors),
            title="Scoring Errors",
            border_style="red",
        ))

    # ── Métadonnées ─────────────────────────────────────────────────────────
    if run_meta:
        meta_table = Table.grid(padding=(0, 2))
        meta_table.add_column(style="dim")
        meta_table.add_column(style="dim")
        for k, v in run_meta.items():
            meta_table.add_row(k, str(v))
        console.print(Panel(meta_table, title="Run Metadata", border_style="dim"))

    console.print()
