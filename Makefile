.PHONY: up down build test logs

up:
	docker compose up -d --build

down:
	docker compose down -v
build:
	docker compose build

test:
	pytest -q
logs:
	docker compose logs -f
