"""
Команда для исправления Django admin пользователя
Изменяет username существующего пользователя на email для удобства входа
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User as DjangoUser


class Command(BaseCommand):
    help = 'Исправляет Django admin пользователя - изменяет username на email'

    def handle(self, *args, **options):
        self.stdout.write('Исправление Django admin пользователя...')

        # Ищем пользователя по email
        user = DjangoUser.objects.filter(email='admin@example.com').first()

        if not user:
            # Ищем по username
            user = DjangoUser.objects.filter(username='admin').first()

            if not user:
                self.stdout.write(self.style.ERROR('Пользователь не найден!'))
                self.stdout.write('Запустите: python manage.py seed_data')
                return

        # Сохраняем старый username для сообщения
        old_username = user.username

        # Изменяем username на email
        user.username = 'admin@example.com'
        user.email = 'admin@example.com'

        # Убеждаемся, что это суперпользователь
        user.is_superuser = True
        user.is_staff = True

        # Устанавливаем пароль, если нужно
        user.set_password('admin123')

        user.save()

        self.stdout.write(self.style.SUCCESS(
            f'✅ Пользователь исправлен!\n'
            f'   Старый username: {old_username}\n'
            f'   Новый username: {user.username}\n'
            f'   Email: {user.email}\n'
            f'   Пароль: admin123'
        ))
        self.stdout.write('')
        self.stdout.write('Теперь вы можете войти в Django admin:')
        self.stdout.write('  Username: admin@example.com')
        self.stdout.write('  Password: admin123')

