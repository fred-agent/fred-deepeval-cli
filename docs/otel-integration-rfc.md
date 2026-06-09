# RFC — OpenTelemetry Integration for Fred Evaluation Pipeline

> **Status**: proposal — no implementation before validation
> **Author**: Odelia Cohen
> **Date**: 2026-06-09
> **Related**: `langfuse-integration-scoping.md`

---

## Context

`fred-deepeval-cli` currently evaluates Fred agents locally and produces a JSON report per run. There is no history, no comparison between runs, and no visibility into the internal execution of the agent during scoring.

The goal of this RFC is to define how OpenTelemetry (OTel) enables continuous evaluation with full observability — without coupling Fred or the CLI to any specific observability vendor.

---

## Problem

Three gaps in the current evaluation pipeline:

1. **No history** — each run is independent. It is impossible to detect regressions between two agent versions, model changes, or corpus updates.

2. **No execution visibility** — the CLI receives a final `EvalTrace` (output + scores) but cannot see what happened inside Fred: which LangGraph nodes ran, how long each `knowledge_search` took, how many tokens were consumed.

3. **Vendor coupling risk** — any direct integration with Langfuse or MLflow in Fred's code creates a lock-in. If the observability backend changes, Fred must be modified.

---

## Proposed Solution

Instrument Fred's execution layer (`fred-runtime`) to emit traces in the **OpenTelemetry standard**. The CLI links its DeepEval scores to these traces via `session_id`. An OTel Collector routes everything to the chosen observability backend (Langfuse, MLflow, or other).

```
fred-runtime (agent execution)
    └── emits OTel spans ──► OTel Collector ──► Langfuse
                                           ──► MLflow
                                           ──► other

fred-deepeval-cli (scoring)
    └── DeepEval scores
    └── linked to Fred's trace via session_id
    └── emits own OTel spans (campaign metadata, corpus snapshot)
```

Fred never imports Langfuse or MLflow. Swapping backends = one line in the Collector config.

---

## What OTel Provides vs What It Does Not

### With OTel

Langfuse (or any OTel backend) receives the full execution trace:

```
Trace: "What is BidGPT?"
  ├── node: query_planner       12ms
  ├── node: knowledge_search   340ms   8 chunks retrieved
  ├── llm_call: mistral-medium   2.1s   1200 tokens
  └── node: final_answer
        + AnswerRelevancy : 0.87   ← DeepEval score attached
        + Faithfulness    : 1.00
```

### Without OTel (SDK-only push)

Langfuse only receives scores:

```
AnswerRelevancy : 0.87
Faithfulness    : 1.00
```

No execution context. No way to understand why a score changed.

---

## Architecture

### Three Options Evaluated

**Option 1 — CLI pushes scores to Langfuse via SDK**
- Effort: low
- Fred untouched
- Vendor lock-in in the CLI — if Langfuse changes, rewrite the CLI
- Langfuse sees scores only, not execution internals

**Option 2 — Fred emits OTel (this RFC)**
- Effort: high
- Fred speaks a standard — backend is swappable
- Langfuse sees full execution + scores linked
- No vendor dependency in Fred or the CLI

**Option 3 — Langfuse orchestrates**
- Effort: medium
- Strong coupling to Langfuse from day one
- Not retained

**Decision: Option 2.** Option 1 can be used as an intermediate step while OTel instrumentation is being built.

---

## Implementation Plan

### Phase 1 — fred-runtime (emit OTel spans)

| Step | File | Action |
|---|---|---|
| 1 | `fred/libs/fred-runtime/pyproject.toml` | Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp` |
| 2 | `fred_runtime/otel.py` | **Create** — configure OTel tracer, read `OTEL_EXPORTER_OTLP_ENDPOINT` from env |
| 3 | `fred_runtime/app/agent_app.py` | Add root span per `/agents/evaluate` call — attributes: `agent_id`, `model_name`, `input`, `latency_ms`, `session_id` as trace ID |
| 4 | LangGraph node wrappers | Add child spans per node — attributes: node name, duration, chunks returned, tokens |

### Phase 2 — fred-deepeval-cli (link scores to traces)

| Step | File | Action |
|---|---|---|
| 5 | `pyproject.toml` | Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp` to `[eval]` extras |
| 6 | `fred_deepeval_cli/otel.py` | **Create** — configure CLI tracer, read `OTEL_EXPORTER_OTLP_ENDPOINT` from env |
| 7 | `fred_deepeval_cli/dataset_workflow.py` | Emit root span `eval-campaign` — attributes: `agent_id`, `date`, `judge_model`, `corpus_snapshot` (list of KF documents), `dataset_hash` |
| 8 | `fred_deepeval_cli/deepeval_runner.py` | After scoring, emit span `deepeval-scores` linked to Fred's `session_id` — attributes: one per metric (name, score, passed) |

### Phase 3 — Infrastructure

| Step | File | Action |
|---|---|---|
| 9 | `deploy/otel-collector-config.yaml` | **Create** — OTel Collector: receivers (otlp), exporters (langfuse or mlflow), pipelines |
| 10 | Langfuse deployment | Enable OTel ingestion (port 4317 gRPC / 4318 HTTP) — no code, config only |
| 11 | `config/.env` (both repos) | Add `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME` |

---

## Corpus Snapshot

A score change between two runs can come from:
- a model change,
- a corpus change (documents added or removed from Knowledge Flow),
- a dataset change (new questions),
- a judge change.

Without capturing the corpus state at evaluation time, history is uninterpretable.

**Solution**: at the start of each campaign, the CLI calls `POST /knowledge-flow/v1/documents/browse` to snapshot the list of indexed documents, then attaches it as an attribute on the root OTel span.

```json
"corpus_snapshot": {
  "size": 36,
  "documents": ["CIR_TSN_2024_BIDGPT.docx", "2509.03768v1.pdf (RAGuard)", "..."]
}
```

---

## UI Strategy

Three options for displaying evaluation results in Fred UI:

**Option A — Display in Langfuse (recommended for V1)**
Fred schedules the run via its task system. The user opens Langfuse for history and drill-down. Zero frontend work. Langfuse already provides a rich UI (per-scenario drill-down, run comparison, regression graphs).

**Option B — Fred reads Langfuse API and displays in its own tab (V2)**
Fred backend normalizes the Langfuse API response and exposes a stable Fred API:
```
GET /api/eval/experiments
GET /api/eval/experiments/{id}/scenarios
```
The frontend calls Fred, not Langfuse. Swapping to MLflow = update Fred backend adapter only, frontend unchanged.

**Option C — Generic adapter (not retained)**
Build adapters for Langfuse, MLflow, etc. behind a Fred API. OTel already solves vendor agnosticism on the emission side — building adapters on the consumption side duplicates the effort without proportional value.

**Recommendation**: V1 → Option A. V2 → Option B if UX unification becomes a real team constraint, accepting that the Fred frontend adapter is tied to one backend's API shape.

---

## Versioned Datasets

Langfuse natively versions datasets (every modification creates a new version, historical versions are replayable). This is independent of OTel — available as soon as Langfuse is deployed.

```
rag-eval-fred  v1  (5 questions)
rag-eval-fred  v2  (8 questions — arxiv enriched)
```

Combined with the corpus snapshot, this allows full reproducibility: given a run ID, you can know exactly which questions, which documents, which model, and which judge were used.

---

## Alternatives Considered

### Direct Langfuse SDK in Fred

Adding Langfuse's `CallbackHandler` to fred-runtime would capture LangChain/LangGraph traces automatically, with minimal code. Rejected because:
- Fred becomes dependent on a vendor library in its core
- If Langfuse changes API or license, Fred must be modified
- In sovereign/qualified environments, adding a vendor dependency to the execution core is a high-cost decision to undo

### MLflow instead of Langfuse

MLflow stores in SQLite/PostgreSQL + filesystem. Lighter than Langfuse (no ClickHouse). However:
- MLflow is designed for ML training experiments, not LLM traces
- No native LLM-as-a-judge, no prompt management, no dataset versioning for conversational data
- Langfuse covers our use case natively

Both are valid OTel consumers — the choice of backend does not affect this RFC.

---

## Open Questions

1. Does the fred-runtime team have bandwidth to instrument LangGraph nodes in Phase 1?
2. Can ClickHouse be allocated in the target K8s cluster? (Langfuse's mandatory dependency)
3. Should the OTel Collector be shared across Fred services or dedicated to evaluation?
4. What is the `session_id` → OTel `trace_id` mapping convention? Should Fred guarantee a stable `session_id` per evaluation call?

---

## Guard Rails

The following constraints must be respected throughout implementation:

- `POST /agents/evaluate` (`validation=true`) must never import a vendor observability library. OTel SDK is acceptable (it is a CNCF standard, not a vendor).
- The CLI's `--otel` flag must be optional. Evaluation must work without OTel configured.
- If the OTel Collector is unreachable, the CLI must degrade gracefully — scores are still computed and emitted as JSON, OTel push fails silently.
