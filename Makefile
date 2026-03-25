PYTHON ?= python3
UV := $(shell command -v uv 2>/dev/null)

.PHONY: install lint typecheck test run simulate fmt

install:
ifdef UV
	uv sync --dev
else
	$(PYTHON) -m pip install -e ".[dev]"
endif

lint:
ifdef UV
	uv run ruff check .
else
	ruff check .
endif

typecheck:
ifdef UV
	uv run mypy src
else
	mypy src
endif

test:
ifdef UV
	uv run pytest
else
	pytest
endif

run:
ifdef UV
	uv run python -m raccoon_guardian.app
else
	$(PYTHON) -m raccoon_guardian.app
endif

simulate:
ifdef UV
	uv run python -m raccoon_guardian.simulation.replay
else
	$(PYTHON) -m raccoon_guardian.simulation.replay
endif

fmt:
ifdef UV
	uv run ruff format .
else
	ruff format .
endif

