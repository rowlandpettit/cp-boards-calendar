PYTHON := $(shell if test -x .venv/bin/python; then printf .venv/bin/python; else command -v python3.13 || command -v python3.12 || command -v python3; fi)

.PHONY: generate test validate
generate:
	$(PYTHON) scripts/generate_calendar.py
test:
	$(PYTHON) -m unittest discover -s tests -v
validate: test generate
