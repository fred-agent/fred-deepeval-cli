# fred-deepeval-cli

External CLI for evaluating one Fred agent turn through `POST /agents/evaluate`.

## Purpose

This project provides a small external CLI that:
- calls a Fred pod `/agents/evaluate` endpoint
- receives an `EvalTrace`
- classifies the turn outcome
- optionally scores the trace with DeepEval

## Commands

```bash
make dev
make eval-dev
make test
make code-quality
make cli
make eval BASE_URL=http://127.0.0.1:8000/fred/agents/v2 AGENT_ID=fred.test.assistant INPUT="echo bonjour" SESSION_ID=eval-001 USER_ID=alice
make score BASE_URL=http://127.0.0.1:8000/fred/agents/v2 AGENT_ID=fred.test.assistant INPUT="echo bonjour" SESSION_ID=eval-001 USER_ID=alice
