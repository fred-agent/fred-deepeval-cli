# RAG Evaluation in `fred-deepeval-cli`

## Context

`fred-deepeval-cli` is used to evaluate Fred agent runs through `/agents/evaluate` and to optionally score them with DeepEval.

For RAG-oriented agents such as `fred.github.rag_expert`, evaluating only the final answer is not sufficient. A response can look correct while:
- no retrieval tool was actually called,
- no retrieval context was surfaced in the trace,
- citations were missing or unreliable.

For that reason, the current design combines:
1. semantic scoring with DeepEval,
2. structural checks on observable RAG behavior.

---

## Goal

The goal of the current implementation is to provide a first practical evaluation layer for RAG scenarios in local development.

It is designed to answer two complementary questions:
- Is the final answer good?
- Did the run exhibit observable RAG behavior?

---

## Two Evaluation Layers

### 1. DeepEval metrics

DeepEval metrics evaluate the semantic quality of the final output.

Current metrics:
- `AnswerRelevancyMetric`
- `FaithfulnessMetric` when `retrieval_context` is non-empty

### 2. Structural checks

Structural checks evaluate the observable execution behavior of the run.

They are especially useful when:
- the final answer looks good,
- but the retrieval path is absent, partial, or unclear.

---

## Current DeepEval Metrics

### `AnswerRelevancyMetric`

Checks whether the final answer is relevant to the user input.

This metric is always enabled.

### `FaithfulnessMetric`

Checks whether the final answer stays faithful to the retrieved context.

This metric is enabled only when `retrieval_context` is present in the trace.

---

## Current RAG Structural Checks

### `rag_tool_used_ok`

Checks whether `knowledge_search` was called.

### `rag_context_nonempty_ok`

Checks whether the trace contains a non-empty `retrieval_context`.

### `rag_context_count_ok`

Checks whether the amount of retrieved context stays within a reasonable range.

Current rule:
- `1 <= len(retrieval_context) <= 8`

### `rag_citations_present_ok`

Checks whether the final answer contains source-like or citation-like markers.

This remains a deliberately simple output-shape check.

### `rag_no_hallucinated_source_ok`

Heuristic check aimed at verifying that explicit source labels cited in the final answer can also be found in the retrieved context.

This check is intended to help detect:
- invented sources;
- documents cited in the answer but never actually retrieved;
- inconsistent file labels compared to the surfaced context.

Current implementation:
- extracts explicit source-like labels from the answer;
- normalizes those labels;
- verifies that they appear in `retrieval_context`.

This is a heuristic v1, not a formal citation validation mechanism.


### `rag_no_hallucinated_source_ok`

Heuristic check ensuring that explicit source labels cited in the answer can also be found in the retrieved context.

Current implementation:
- extracts explicit file-like labels from the answer,
- normalizes them,
- verifies they appear in `retrieval_context`.

This is a heuristic v1, not a fully reliable citation-validation system.

---

## Example Execution Profiles Observed

### Case A: Good answer, no observable retrieval

Observed trace:
- `tools_called = []`
- `retrieval_context = []`

Interpretation:
- the answer may still look correct,
- but no observable RAG behavior is present in the trace.

Typical structural result:
- `rag_tool_used_ok = false`
- `rag_context_nonempty_ok = false`
- `rag_context_count_ok = false`

Typical DeepEval result:
- `AnswerRelevancyMetric` only

### Case B: Observable retrieval and grounded answer

Observed trace:
- `tools_called = ["knowledge_search"]`
- non-empty `retrieval_context`

Interpretation:
- the run exhibits observable RAG behavior,
- semantic faithfulness can also be evaluated.

Typical structural result:
- all `rag_*` checks true

Typical DeepEval result:
- `AnswerRelevancyMetric`
- `FaithfulnessMetric`

### Case C: Retrieval attempted but failed

Observed trace:
- `tools_called = ["knowledge_search"]`
- `retrieval_context = []`
- execution error from retrieval layer

Interpretation:
- the agent attempted RAG,
- but the retrieval backend failed or was unreachable.

Typical structural result:
- `rag_tool_used_ok = true`
- `rag_context_nonempty_ok = false`

---

## Why `ContextualPrecisionMetric` Is Not Used in Live Scoring

`ContextualPrecisionMetric` was explored but removed from the live scoring flow.

Reason:
- DeepEval requires `expected_output` for that metric,
- the current `make score` flow evaluates ad hoc live prompts,
- no ground-truth expected output is available in that mode.

This metric may be reintroduced later in a dataset-driven or scenario-driven evaluation mode.

---

## Current Limitations

### `expected_outcome_ok`

`expected_outcome_ok` is currently a placeholder set to `true`.

It is intended to evolve into a scenario/profile-based contract check.

### `rag_no_hallucinated_source_ok`

This check is heuristic and depends on:
- explicit source labels appearing in the answer,
- comparable labels being present in `retrieval_context`.

It should not be interpreted as a formal proof of citation correctness.

### Retrieval observability is not guaranteed

For some prompts, the same agent may:
- perform observable retrieval,
- or produce an answer without retrieval being surfaced in the trace.

The CLI reflects the trace it receives; it does not infer hidden retrieval behavior.

---

## Future Directions

Possible next steps:
- add evaluation profiles,
- support scenario-level `expected_outcome`,
- support dataset-driven evaluation with `expected_output`,
- reintroduce `ContextualPrecisionMetric` in annotated evaluation mode,
- extend the framework to SQL-oriented agents.

---

## Summary

The current implementation provides a first RAG-aware evaluation layer for `fred-deepeval-cli` by combining:
- semantic scoring of the final answer,
- structural checks on observable retrieval behavior.

This makes it possible to distinguish:
- a good answer,
- a grounded RAG answer,
- a good-looking answer without observable retrieval,
- and a retrieval attempt that failed.
