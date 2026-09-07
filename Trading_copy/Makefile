.PHONY: help install run test docker-up docker-down clean

help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies"
	@echo "  run          - Run the application locally"
	@echo "  test         - Run tests"
	@echo "  docker-up    - Start all services with Docker"
	@echo "  docker-down  - Stop all services"
	@echo "  clean        - Clean cache files"
	@echo "  migrate      - Run database migrations"
	@echo "  lint         - Run code linting"

install:
	pip install -r requirements.txt
	pip install -e .

run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=src --cov-report=html

docker-up:
	docker-compose -f docker/docker-compose.yml up -d

docker-down:
	docker-compose -f docker/docker-compose.yml down

docker-logs:
	docker-compose -f docker/docker-compose.yml logs -f

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +

migrate:
	alembic upgrade head

lint:
	flake8 src/
	black src/ --check
	isort src/ --check-only

format:
	black src/
	isort src/

setup-dev: install
	cp .env.example .env
	@echo "Please update .env with your configuration"
	docker-compose -f docker/docker-compose.yml up -d postgres redis rabbitmq
	sleep 5
	make migrate