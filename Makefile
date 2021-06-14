test-and-lint:
	venv/bin/pytest --mypy-ignore-missing-imports
	venv/bin/flake8 --count --verbose --show-source --statistics
	venv/bin/black . --check -S -l 120
	venv/bin/isort . --profile black -l 120