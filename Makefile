.PHONY: help install install-uv init-db run dev test test-api generate-openapi clean

help:
	@echo "Phishing Detection API - Available commands:"
	@echo ""
	@echo "  make install        - Install dependencies using pip"
	@echo "  make install-uv     - Install dependencies using uv (recommended)"
	@echo "  make init-db        - Initialize database"
	@echo "  make run            - Run development server"
	@echo "  make dev            - Run development server with auto-reload"
	@echo "  make test           - Run all tests"
	@echo "  make test-api       - Test API endpoints"
	@echo "  make generate-openapi - Generate OpenAPI schema"
	@echo "  make clean          - Clean temporary files"
	@echo ""

install:
	pip install -r requirements.txt

install-uv:
	uv venv
	uv pip install -e .

init-db:
	python scripts/init_database.py

run:
	python run.py

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 5000

test:
	python scripts/test_api.py

test-api:
	python scripts/test_api.py

generate-openapi:
	python scripts/generate_openapi.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	@echo "✓ Cleaned temporary files"
