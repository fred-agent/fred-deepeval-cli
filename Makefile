PROJECT_NAME=fred-deepeval-cli
PY_PACKAGE=fred_deepeval_cli

include scripts/makefiles/python-vars.mk

include scripts/makefiles/python-deps.mk
include scripts/makefiles/python-code-quality.mk
include scripts/makefiles/python-test.mk
include scripts/makefiles/python-clean.mk
include scripts/makefiles/help.mk

.PHONY: cli
cli: dev ## Run the external EvalTrace CLI
	VIRTUAL_ENV= $(UV) run python -m fred_deepeval_cli.main --help

.PHONY: eval-dev
eval-dev: ## Install dev + DeepEval dependencies
	VIRTUAL_ENV= $(UV) sync --extra dev --extra eval

.PHONY: eval
eval: dev ## Evaluate one Fred agent turn
	@if [ -z "$(BASE_URL)" ] || [ -z "$(AGENT_ID)" ] || [ -z "$(INPUT)" ] || [ -z "$(SESSION_ID)" ] || [ -z "$(USER_ID)" ]; then \
		echo "Usage (native):  make eval BASE_URL=http://127.0.0.1:8000/fred/agents/v2 AGENT_ID=fred.test.assistant INPUT='echo bonjour' SESSION_ID=eval-001 USER_ID=alice [TEAM_ID=my-team] [TRACE_MODE=native]"; \
		echo "Usage (adapted): make eval BASE_URL=http://127.0.0.1:8000/agentic/v1 AGENT_ID='Luigi v2' INPUT='Proposer une offre commerciale' SESSION_ID=prism-eval-001 USER_ID=admin TRACE_MODE=adapted ACCESS_TOKEN=dev-token SEARCH_POLICY=semantic"; \
		exit 1; \
	fi
	VIRTUAL_ENV= $(UV) run python -m fred_deepeval_cli.main evaluate \
		--base-url "$(BASE_URL)" \
		--agent-id "$(AGENT_ID)" \
		--input "$(INPUT)" \
		--session-id "$(SESSION_ID)" \
		--user-id "$(USER_ID)" \
		$(if $(TRACE_MODE),--trace-mode "$(TRACE_MODE)",) \
		$(if $(TEAM_ID),--team-id "$(TEAM_ID)",) \
		$(if $(ACCESS_TOKEN),--access-token "$(ACCESS_TOKEN)",) \
		$(if $(SEARCH_POLICY),--search-policy "$(SEARCH_POLICY)",)

.PHONY: score
score: eval-dev ## Evaluate and score one Fred agent turn with DeepEval
	@if [ -z "$(BASE_URL)" ] || [ -z "$(AGENT_ID)" ] || [ -z "$(INPUT)" ] || [ -z "$(SESSION_ID)" ] || [ -z "$(USER_ID)" ]; then \
		echo "Usage (native):  make score BASE_URL=http://127.0.0.1:8000/fred/agents/v2 AGENT_ID=fred.test.assistant INPUT='echo bonjour' SESSION_ID=eval-001 USER_ID=alice [TEAM_ID=my-team] [TRACE_MODE=native]"; \
		echo "Usage (adapted): make score BASE_URL=http://127.0.0.1:8000/agentic/v1 AGENT_ID='Luigi v2' INPUT='Proposer une offre commerciale' SESSION_ID=prism-score-001 USER_ID=admin TRACE_MODE=adapted ACCESS_TOKEN=dev-token SEARCH_POLICY=semantic"; \
		exit 1; \
	fi
	VIRTUAL_ENV= $(UV) run python -m fred_deepeval_cli.main score \
		--base-url "$(BASE_URL)" \
		--agent-id "$(AGENT_ID)" \
		--input "$(INPUT)" \
		--session-id "$(SESSION_ID)" \
		--user-id "$(USER_ID)" \
		$(if $(TRACE_MODE),--trace-mode "$(TRACE_MODE)",) \
		$(if $(TEAM_ID),--team-id "$(TEAM_ID)",) \
		$(if $(ACCESS_TOKEN),--access-token "$(ACCESS_TOKEN)",) \
		$(if $(SEARCH_POLICY),--search-policy "$(SEARCH_POLICY)",)

.PHONY: sql-scenarios
sql-scenarios: eval-dev ## Run the SQL scenario campaign against fred.github.sql_expert
	@if [ -z "$(BASE_URL)" ]; then \
		echo "Usage: make sql-scenarios BASE_URL=http://127.0.0.1:8000/fred/agents/v2 [USER_ID=alice] [TEAM_ID=my-team]"; \
		exit 1; \
	fi
	VIRTUAL_ENV= $(UV) run python scripts/run_sql_scenarios.py \
		--base-url "$(BASE_URL)" \
		--agent-id "fred.github.sql_expert" \
		--user-id "$(or $(USER_ID),alice)" \
		$(if $(TEAM_ID),--team-id "$(TEAM_ID)",) \
		$(if $(ACCESS_TOKEN),--access-token "$(ACCESS_TOKEN)",)


.PHONY: luigi-scenarios
luigi-scenarios: eval-dev ## Run the Luigi scenario campaign against Luigi v2
	@if [ -z "$(BASE_URL)" ]; then \
		echo "Usage: make luigi-scenarios BASE_URL=http://127.0.0.1:8000/agentic/v1 [USER_ID=admin] [TEAM_ID=personal] [ACCESS_TOKEN=dev-token] [SEARCH_POLICY=semantic] [TRACE_MODE=adapted]"; \
		exit 1; \
	fi
	VIRTUAL_ENV= $(UV) run python scripts/run_luigi_scenarios.py \
		--base-url "$(BASE_URL)" \
		--trace-mode "$(or $(TRACE_MODE),adapted)" \
		--user-id "$(or $(USER_ID),admin)" \
		$(if $(TEAM_ID),--team-id "$(TEAM_ID)",) \
		$(if $(ACCESS_TOKEN),--access-token "$(ACCESS_TOKEN)",) \
		--search-policy "$(or $(SEARCH_POLICY),semantic)"
