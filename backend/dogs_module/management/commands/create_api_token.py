"""
Создание API токена для импорта.

Использование:
    python manage.py create_api_token
    python manage.py create_api_token --username admin@example.com
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = 'Создаёт API токен для пользователя (по умолчанию admin)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default='admin@example.com',
            help='Username пользователя (default: admin@example.com)'
        )

    def handle(self, *args, **options):
        username = options['username']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Пользователь "{username}" не найден'))
            self.stdout.write('Доступные пользователи:')
            for u in User.objects.all():
                self.stdout.write(f'  - {u.username} (staff={u.is_staff})')
            return

        token, created = Token.objects.get_or_create(user=user)

        if created:
            self.stdout.write(self.style.SUCCESS(f'Токен создан!'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Токен уже существует:'))

        self.stdout.write('')
        self.stdout.write(f' Username: {user.username}')
        self.stdout.write(f' Token: {token.key}')
        self.stdout.write(f' Staff: {user.is_staff}')
        self.stdout.write('')
        self.stdout.write('Использование в curl:')
        self.stdout.write(f' curl -X POST http://localhost:8000/api/dogs/import/search-page/ \\')
        self.stdout.write(f' -H "Authorization: Token {token.key}" \\')
        self.stdout.write(f' -H "Content-Type: application/json" \\')
        self.stdout.write(f' -d \'{{"page": 1, "max_dogs": 5}}\'')
