.PHONY: help install test build docker-build docker-run clean check

help:
	@echo "Slides Repository Catalog - Make Commands"
	@echo ""
	@echo "  make install       - Install Python dependencies"
	@echo "  make check         - Validate setup"
	@echo "  make test          - Test individual components"
	@echo "  make build         - Build catalog locally"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run in Docker container"
	@echo "  make clean         - Remove generated files"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

check:
	@echo "Validating setup..."
	python3 test_setup.py

test:
	@echo "Testing Graph client..."
	python3 src/graph_client.py
	@echo ""
	@echo "To test renderer, run:"
	@echo "  python3 src/slides_renderer.py path/to/presentation.pptx"

build:
	@echo "Building catalog..."
	python3 src/build_catalog.py
	@echo ""
	@echo "Preview with: cd site && python3 -m http.server 8000"

docker-build:
	@echo "Building Docker image..."
	docker build -t slides-catalog-builder .

docker-run:
	@echo "Running in Docker..."
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Copy .env.example and configure."; \
		exit 1; \
	fi
	docker run --rm \
		--env-file .env \
		-v $(PWD)/site:/app/site \
		slides-catalog-builder

clean:
	@echo "Cleaning generated files..."
	rm -rf site/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Done."
