# Prism Adapted EvalTrace in `fred-deepeval-cli`

## Context

`fred-deepeval-cli` was originally built for runtimes that already expose a native `EvalTrace` through `POST /agents/evaluate`.

This works well for Fred runtimes that directly return the trace contract expected by the CLI.

Prism is different today:
- it exposes agent execution through its chat/session/WebSocket transport,
- but it does not currently expose a native `/agents/evaluate` endpoint returning an `EvalTrace`.

The product situation today is the following:
- **Kea 1.5** is the current production release,
- its runtime is **`agentic-backend`**,
- **Swift 2.0** is the target direction,
- Swift already aligns naturally with a native `EvalTrace` flow,
- but Swift is still a developer-preview track, not the production runtime currently used by Kea.

That creates a temporary but important gap:
- the long-term target is to evaluate agents through the native Swift-style `EvalTrace` flow,
- but the short-term need is to evaluate the agents that are actually running today in **Kea / Prism / `agentic-backend`**,
- and those agents do not yet expose a native `EvalTrace`.

For that reason, evaluating Prism runs with the CLI required an intermediate path.

---

## What We Added

We added an adapted trace mode in `fred-deepeval-cli`.

The CLI can now obtain a trace in two ways:
- `native`: call a backend that already returns an `EvalTrace`,
- `adapted`: execute a Prism run and reconstruct an `EvalTrace` from the observable session data.

We also added an `auto` mode:
- `auto` first tries the native path,
- if the runtime does not expose a native `EvalTrace` endpoint, it falls back to the adapted path.

This keeps the CLI centered on one stable contract:
- the CLI consumes an `EvalTrace`,
- regardless of whether that trace was returned directly or reconstructed from another runtime.

---

## Why We Did It This Way

The goal was not to make the CLI permanently "Prism-specific".

The goal was to create an intermediate evaluation layer for Kea:
- usable now with the agents that currently run in production on `agentic-backend`,
- compatible later with the Swift-native trace model.

In other words, we wanted to avoid two bad outcomes:
- blocking evaluation until Swift is fully production-ready,
- or building a one-off Prism-only solution that would have to be thrown away later.

Instead, the CLI is now capable of evaluating any runtime that either:
- already exposes an `EvalTrace`,
- or exposes enough observable execution data to rebuild one.

This is a better abstraction boundary than hard-coding separate "Fred mode" and "Prism mode".

It keeps the evaluation pipeline stable:
1. obtain an `EvalTrace`,
2. classify the outcome,
3. run structural checks,
4. optionally score with DeepEval.

---

## How the Prism Adaptation Works

In adapted mode, the CLI does not call `/agents/evaluate`.

Instead, it:
1. creates a Prism chatbot session,
2. updates the session preferences,
3. opens the Prism WebSocket transport,
4. sends the user message to the target agent,
5. waits for the run to complete,
6. reads the persisted session history,
7. converts that history into an `EvalTrace`.

The reconstructed trace includes:
- `input`
- `output`
- `error`
- `steps`
- `tools_called`
- `retrieval_context`
- `latency_ms`

The key idea is simple:
- Prism gives us execution events and persisted messages,
- the CLI maps those observable artifacts into the same `EvalTrace` shape already used everywhere else.

---

## Trace Modes

### `native`

Use this mode when the target runtime already exposes an `EvalTrace`.

This is the expected steady-state path for Swift-style runtimes.

### `adapted`

Use this mode when the target runtime does not expose an `EvalTrace` natively, but does expose enough observable execution data to rebuild one.

This is the current path used for Prism / Kea agents running on `agentic-backend`.

### `auto`

This is the default compatibility mode.

The CLI:
1. tries the native path first,
2. if no native `EvalTrace` endpoint is available, falls back to the adapted path.

This is useful because it lets the same CLI command continue to work across the transition from Kea to Swift.

---

## Files Modified and Their Role

### [fred_deepeval_cli/main.py](/Users/odeliacohen/Documents/Thales/fred/ignored/fred-deepeval-cli/fred_deepeval_cli/main.py)

Purpose:
- add the `--trace-mode` CLI argument,
- support `auto`, `native`, and `adapted`,
- keep `evaluate` and `score` on the same user-facing interface.

### [fred_deepeval_cli/eval_client.py](/Users/odeliacohen/Documents/Thales/fred/ignored/fred-deepeval-cli/fred_deepeval_cli/eval_client.py)

Purpose:
- keep the shared payload/header helpers,
- dispatch trace acquisition to the appropriate trace source,
- implement the `auto` fallback behavior.

### [fred_deepeval_cli/trace_sources.py](/Users/odeliacohen/Documents/Thales/fred/ignored/fred-deepeval-cli/fred_deepeval_cli/trace_sources.py)

Purpose:
- introduce the trace-source abstraction,
- implement the native source (`/agents/evaluate`),
- implement the adapted Prism source,
- reconstruct an `EvalTrace` from Prism session history and WebSocket execution.

### [pyproject.toml](/Users/odeliacohen/Documents/Thales/fred/ignored/fred-deepeval-cli/pyproject.toml)

Purpose:
- add the WebSocket dependency required by the Prism adapted flow.

### [docs/prism-adapted-evaltrace.md](/Users/odeliacohen/Documents/Thales/fred/ignored/fred-deepeval-cli/docs/prism-adapted-evaltrace.md)

Purpose:
- document the rationale,
- explain the temporary Kea-to-Swift bridge,
- describe how the adapted `EvalTrace` path works.

---

## Current Status

This adapted flow is now working for local Prism runs such as `Luigi v2`.

That means `fred-deepeval-cli` can now evaluate Prism even though Prism does not yet expose a native `EvalTrace` endpoint.

This is the intended intermediate step for Kea:
- it unblocks evaluation immediately on the current production-style agents running on `agentic-backend`,
- it avoids breaking the existing evaluation model,
- and it keeps the target contract aligned with the future Swift-native flow.

---

## Long-Term Direction

This adapted path should be seen as an intermediate compatibility layer, not necessarily the final architecture.

More importantly, once Swift becomes the production runtime for these agents, the same CLI can continue to work through the native trace path.

If that happens:
- the CLI can keep the same contract,
- and simply use the native path instead of the adapted one.

That is why this design is useful:
- it solves the current Kea need now,
- without breaking the future move toward Swift-native agent evaluation.
