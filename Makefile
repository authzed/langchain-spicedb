.PHONY: test integration_test unit_test format lint install help

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package with all dependencies
	pip install -e ".[all,dev]"

test:  ## Run all unit tests
	pytest tests/unit_tests/ -v

integration_test:  ## Run integration tests (requires SpiceDB)
	pytest tests/integration_tests/ -v

test_all:  ## Run all tests (unit + integration)
	pytest tests/ -v

test_watch:  ## Run tests in watch mode
	pytest-watch tests/unit_tests/

coverage:  ## Run tests with coverage report
	pytest --cov=langchain_spicedb --cov-report=html --cov-report=term tests/
	@echo "Coverage report generated in htmlcov/index.html"

format:  ## Format code with black and isort
	black langchain_spicedb/ tests/
	isort langchain_spicedb/ tests/

lint:  ## Lint code with ruff
	ruff check langchain_spicedb/ tests/

type_check:  ## Type check with mypy
	mypy langchain_spicedb/

clean:  ## Clean up generated files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Build distribution packages
	python -m build

publish:  ## Publish to PyPI (requires credentials)
	python -m twine upload dist/*

publish_test:  ## Publish to Test PyPI
	python -m twine upload --repository testpypi dist/*
