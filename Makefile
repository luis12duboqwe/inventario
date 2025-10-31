.PHONY: install run-backend run-frontend test lint seed build-backend build-frontend

install:
	python -m pip install -r backend/requirements.txt
	cd frontend && npm ci

run-backend:
	uvicorn backend.app.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

lint:
	ruff backend || true
	black --check backend || true
	cd frontend && npm run lint

 test:
	pytest -q

seed:
	python scripts/seed_demo.py

build-backend:
	python -m compileall backend

build-frontend:
	cd frontend && npm run build
