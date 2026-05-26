# Running a Local RAG Evaluation

## Objective

This guide explains how to run a local evaluation of `fred.github.rag_expert` using `fred-deepeval-cli`.

It covers:
- the role of the bearer token;
- the `SEARCH_POLICY=semantic` configuration;
- starting the required local services;
- the `make score` command.

---

## Prerequisites

The following services must be running locally before any evaluation:

- **`fred-agents`** — the agent runtime
- **Knowledge Flow** — the document search engine

---

## Why You Need to Start Knowledge Flow

`fred.github.rag_expert` can invoke the `knowledge_search` tool.

This tool does not perform the document search itself — it delegates to **Knowledge Flow**, which runs the actual search against the indexed corpus.

Without Knowledge Flow running:
- the agent may attempt a retrieval;
- but no document context will be returned;
- or a connection error will appear.

**Example error:**

```text
All connection attempts failed
```

---

## Why a Bearer Token Is Required

In some RAG scenarios, `knowledge_search` requires an **authenticated user context** to perform the search.

Without a valid bearer token, the following error may appear:

```text
Agent runtime_context has no access_token and refresh failed.
```

---

## Retrieving the Bearer Token

1. Start the application front end and open it in your browser.
2. Open the developer tools: **Inspect → Console**.
3. Run one of the following commands depending on your context:

```js
localStorage.getItem("keycloak_token")
```

or:

```js
localStorage.getItem("dev_admin_token")
```

4. Export the retrieved token in your shell:

```bash
export FRED_ACCESS_TOKEN="<token>"
```

---

## Why Use `SEARCH_POLICY=semantic`

Locally with **ChromaDB**, the default search policy may be set to `hybrid`, which is not always suited to a local setup.

For local RAG evaluations, semantic search is explicitly enforced:

```
SEARCH_POLICY=semantic
```

---

## `make score` Command

Fetches the trace, resolves the evaluation preset from `agent_tags`, computes structural checks, and runs DeepEval metrics:

```bash
make score \
  BASE_URL=http://127.0.0.1:8000/fred/agents/v2 \
  AGENT_ID=fred.github.rag_expert \
  INPUT='What are the three RAG evaluation metrics mentioned in the documents?' \
  SESSION_ID=rag-score-001 \
  USER_ID=alice \
  ACCESS_TOKEN="$FRED_ACCESS_TOKEN" \
  SEARCH_POLICY=semantic
```

### Affichage et sortie machine

Le CLI utilise [Rich](https://github.com/Textualize/rich) pour un affichage lisible dans le terminal (`stderr`), tout en émettant le résultat complet en JSON sur `stdout` — ce qui permet de le consommer directement depuis une UI ou un script.

| Cas d'usage | Commande |
|---|---|
| Affichage Rich seul dans le terminal | `make score ... > /dev/null` |
| JSON seul (pour un script ou une UI) | `make score ... 2> /dev/null` |
| Les deux (comportement par défaut) | `make score ...` |

---

### `PRESET` override

`PRESET` is optional. By default, the CLI resolves the preset from `agent_tags` in the trace. To force the RAG preset explicitly:

```bash
make score \
  ... \
  PRESET=rag
```
