.PHONY: help install run v2 v3 run_app lint format clean

help:  ## Show available commands
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv sync

run_demo:  ## Run the demo script
	uv run python scripts/demo.py

run_v2:  ## Run the case study, version 2 (script with cells)
	uv run scripts/02_diabetes_cells.py

run_v3:  ## Run the case study, version 3 (script with functions)
	uv run scripts/03_diabetes_functions.py

run_app:  ## Run the Streamlit app
	uv run streamlit run app/app.py

lint:  ## Check code with ruff
	uv run ruff check .

format:  ## Format code with ruff
	uv run ruff format .

clean:  ## Remove caches
	find . -name __pycache__ -not -path "./.venv/*" -prune -exec rm -rf {} +
	rm -rf .mypy_cache .ruff_cache
