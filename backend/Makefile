.PHONY: help up down restart logs shell superuser seed test clean

help:
	@echo "Доступные команды:"
	@echo "  make up         - Запустить все сервисы"
	@echo "  make down       - Остановить все сервисы"
	@echo "  make restart    - Перезапустить сервисы"
	@echo "  make logs       - Показать логи"
	@echo "  make shell      - Django shell"
	@echo "  make superuser  - Создать суперпользователя"
	@echo "  make seed       - Загрузить тестовые данные"
	@echo "  make test       - Запустить тесты"
	@echo "  make clean      - Очистить volumes"

up:
	docker-compose up -d --build
	@echo ""
	@echo "✅ Сервисы запущены!"
	@echo "📍 API: http://localhost:8000/api/"
	@echo "📚 Swagger: http://localhost:8000/api/schema/swagger-ui/"
	@echo "⚙️  Admin: http://localhost:8000/admin/"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f web

shell:
	docker-compose exec web python manage.py shell

superuser:
	docker-compose exec web python manage.py createsuperuser

seed:
	docker-compose exec web python manage.py seed_data

test:
	docker-compose exec web pytest

clean:
	docker-compose down -v
	@echo "✓ Volumes удалены"
