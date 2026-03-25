.PHONY: up down migrate createsuperuser worker logs start

up:
	docker-compose up -d --build

down:
	docker-compose down

migrate:
	docker-compose run --rm web python manage.py migrate

createsuperuser:
	docker-compose run --rm web python manage.py createsuperuser

worker:
	docker-compose up -d worker

logs:
	docker-compose logs -f

start: up migrate
	@echo "Ambiente iniciado. Use 'make worker' para subir o worker Celery." 
