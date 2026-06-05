.PHONY: build up down logs shell-backend shell-db migrate-db chaos-run chaos-stop

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

shell-backend:
	docker-compose exec backend bash

shell-db:
	docker-compose exec postgres psql -U trading_user -d trading_db

init-db:
	docker-compose exec backend python scripts/init_db.py

migrate-db:
	python scripts/migrate_db.py

chaos-run:
	python scripts/chaos_run.py --allow-disabled --experiment all

chaos-stop:
	python scripts/chaos_stop.py
