# fred-deepeval-cli

External CLI for evaluating one Fred agent turn through `POST /agents/evaluate`.

## Purpose

This project provides a small external CLI that:
- calls a Fred pod `/agents/evaluate` endpoint
- receives an `EvalTrace`
- classifies the turn outcome
- prints a stable JSON payload for evaluation workflows

## Example

```bash
uv run python -m fred_deepeval_cli.main evaluate \
  --base-url http://127.0.0.1:8000/fred/agents/v2 \
  --agent-id fred.test.assistant \
  --input "echo bonjour" \
  --session-id eval-001 \
  --user-id alice
