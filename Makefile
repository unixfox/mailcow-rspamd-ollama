.PHONY: help test test-cov test-watch install clean lint

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make test-cov   - Run tests with coverage report"
	@echo "  make lint       - Run code linters"
	@echo "  make clean      - Remove generated files"

install:
	pip install -r requirements-dev.txt

test:
	pytest -v

test-cov:
	pytest --cov --cov-report=html --cov-report=term-missing

test-watch:
	pytest-watch

lint:
	flake8 server.py tests/ --max-line-length=127
	@echo "✅ Linting complete!"

clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete!"
