LINE ?= config/line.yaml
MINUTES ?= 60
MWA = .venv/bin/mwa --line $(LINE)

.PHONY: install route record context verify tts simulate pipeline test lint format

install:
	python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

route:
	$(MWA) route

record:
	$(MWA) record --minutes $(MINUTES)

context:
	$(MWA) context

verify:
	$(MWA) verify

tts:
	$(MWA) tts

simulate:
	$(MWA) simulate $(REC)

pipeline: route context verify tts

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	npx prettier@3.3.3 --check .

format:
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .
	npx prettier@3.3.3 --write .
