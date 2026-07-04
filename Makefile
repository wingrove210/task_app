.PHONY: up up-scale down build test logs

up:
	docker compose up -d --build

up-scale:
	docker compose up -d --build --scale identity=2 --scale project=2 --scale task=2
down:
	docker compose down -v
build:
	docker compose build

test:
	pytest -q
logs:
	docker compose logs -f
