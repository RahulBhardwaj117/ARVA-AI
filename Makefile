.PHONY: setup start up check verify status down reset migrate seed test lint build audit demo

setup:
	cp -n .env.example .env || true
	python -m pip install -e ".[dev]"
	npm --prefix frontend install

start:
	docker compose config --quiet
	docker compose up --build -d --wait
	node scripts/verify_runtime.mjs --read-only

up:
	docker compose up --build -d

check:
	docker compose up -d --wait
	node scripts/verify_runtime.mjs --read-only

verify: lint test audit build
	docker compose config --quiet
	docker compose up --build -d --wait
	node scripts/verify_runtime.mjs

status:
	docker compose ps

down:
	docker compose down

reset:
	docker compose down -v
	docker compose up --build -d

migrate:
	docker compose exec backend alembic -c backend/alembic.ini upgrade head

seed:
	docker compose exec backend python scripts/seed_database.py

test:
	pytest
	npm --prefix frontend test

lint:
	ruff check backend scripts
	npm --prefix frontend run lint

build:
	npm --prefix frontend run build

audit:
	npm --prefix frontend audit

demo:
	docker compose exec -T backend python scripts/run_demo.py
