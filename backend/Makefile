.PHONY: install dev test migrate seed worker
install: ; python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
dev: ; uvicorn app.main:app --reload --port 8000
test: ; pytest -q
migrate: ; alembic upgrade head
seed: ; python -m scripts.seed
worker: ; celery -A app.worker.celery_app worker -l info
