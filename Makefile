.PHONY: up down build migrate shell logs score sync validate-events test createsuperuser

SEASON ?= $(shell read -p "Season: " s && echo $$s)
EPISODE ?= $(shell read -p "Episode: " e && echo $$e)

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose exec backend python manage.py migrate

shell:
	docker compose exec backend python manage.py shell

logs:
	docker compose logs -f

score:
	docker compose exec backend python manage.py score_episode_now $(SEASON) $(EPISODE)

sync:
	docker compose exec backend python manage.py sync_season $(SEASON)

validate-events:
	docker compose exec backend python manage.py validate_event_strings $(SEASON)

test:
	docker compose exec backend python manage.py test apps

createsuperuser:
	docker compose exec backend python manage.py createsuperuser
