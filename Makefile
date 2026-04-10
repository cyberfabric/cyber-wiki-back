# Makefile for CyberWiki Backend

.PHONY: help install test coverage clean run migrate shell

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:  ## Run tests
	pytest -v

test-fast:  ## Run tests in parallel
	pytest -n auto

test-watch:  ## Run tests in watch mode (requires pytest-watch)
	ptw

coverage:  ## Run tests with coverage report
	pytest --cov=src --cov-report=html --cov-report=term-missing

coverage-open:  ## Run coverage and open HTML report
	pytest --cov=src --cov-report=html
	open htmlcov/index.html

test-module:  ## Run tests for specific module (usage: make test-module MODULE=users)
	pytest src/$(MODULE)/tests/ -v

clean:  ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name '.coverage' -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf *.egg-info/

run:  ## Run development server
	python manage.py runserver

migrate:  ## Run database migrations
	python manage.py migrate

makemigrations:  ## Create new migrations
	python manage.py makemigrations

shell:  ## Open Django shell
	python manage.py shell

check:  ## Run Django system check
	python manage.py check

format:  ## Format code with black and isort
	black src/
	isort src/

lint:  ## Run linters
	flake8 src/
	pylint src/

type-check:  ## Run type checking with mypy
	mypy src/

quality:  ## Run all quality checks (format, lint, type-check)
	make format
	make lint
	make type-check

ci:  ## Run CI checks (tests + coverage + quality)
	make test
	make coverage
	make lint

schema:  ## Generate OpenAPI schema
	python manage.py spectacular --file schema.yml

docs:  ## Open API documentation in browser
	python manage.py runserver & sleep 2 && open http://localhost:8000/api/docs/

superuser:  ## Create superuser
	python manage.py createsuperuser

reset-db:  ## Reset database (WARNING: deletes all data)
	rm -f db.sqlite3
	python manage.py migrate

seed-db:  ## Seed database with test data (requires custom management command)
	python manage.py seed_data
