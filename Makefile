test-and-lint:
	venv/bin/isort . --profile black -l 120
	venv/bin/black . --check -S -l 120
	venv/bin/pytest --mypy-ignore-missing-imports
	venv/bin/flake8 --count --verbose --show-source --statistics

start:
	python3 back_office/app.py

heroku-deploy:
	git push heroku main:master

heroku-add-remote:
	heroku git:remote -a envinorma-back-office

heroku-logs:
	heroku logs --tail