# dogs_module/management/commands/clear_photos.py
"""
Удаляет все фото с Яндекс.Диска и очищает поля photo_yadisk_* и photo_hash в БД.

Использование:
  python manage.py clear_photos # удалить всё
  python manage.py clear_photos --dry-run # только показать что будет удалено
  python manage.py clear_photos --db-only # только очистить БД (ЯД не трогать)
  python manage.py clear_photos --yadisk-only # только удалить с ЯД (БД не трогать)
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Удаляет фото с Яндекс.Диска и очищает photo_yadisk_* и photo_hash в БД'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что будет удалено, не трогать ЯД и БД',
        )
        parser.add_argument(
            '--db-only',
            action='store_true',
            help='Только очистить БД, не трогать ЯД',
        )
        parser.add_argument(
            '--yadisk-only',
            action='store_true',
            help='Только удалить файлы с ЯД, не трогать БД',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        db_only = options['db_only']
        yadisk_only = options['yadisk_only']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN: изменения не применяются'))

        # ── Яндекс.Диск ───────────────────────────────────────────────────────
        if not db_only:
            from ...services import yadisk_client as yd

            self.stdout.write('Получаем список файлов с ЯД...')
            files = yd.list_files()
            self.stdout.write(f'Файлов на ЯД: {len(files)}')

            if dry_run:
                for f in files[:10]:
                    self.stdout.write(f"  {f.get('path')}")
                if len(files) > 10:
                    self.stdout.write(f'  ... и ещё {len(files) - 10}')
            else:
                deleted = failed = 0
                for f in files:
                    path = f.get('path', '').replace('disk:/', '')
                    if not path:
                        continue
                    ok = yd.delete(path, permanently=True)
                    if ok:
                        deleted += 1
                    else:
                        failed += 1
                        self.stdout.write(self.style.WARNING(f'  Не удалось удалить: {path}'))

                if failed:
                    self.stdout.write(self.style.WARNING(f'Удалено с ЯД: {deleted}, ошибок: {failed}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Удалено с ЯД: {deleted}'))

        # ── База данных ────────────────────────────────────────────────────────
        if not yadisk_only:
            from ...models import Dog

            count = Dog.objects.using('dogs_db').exclude(
                photo_yadisk_path=None,
                photo_yadisk_url=None,
                photo_hash=None,
            ).count()
            self.stdout.write(f'Собак с заполненными полями фото: {count}')

            if not dry_run:
                updated = Dog.objects.using('dogs_db').update(
                    photo_yadisk_path=None,
                    photo_yadisk_url=None,
                    photo_hash=None,
                )
                self.stdout.write(self.style.SUCCESS(f'Очищено в БД: {updated} собак'))
            else:
                self.stdout.write('DRY-RUN: БД не изменена')
