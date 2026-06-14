import re
from django.core.management.base import BaseCommand
from ...models import Dog


class Command(BaseCommand):
    help = 'Убирает суффикс _s из photo_url в таблице Dog'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что изменится, не трогать БД',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        dogs = Dog.objects.using('dogs_db').filter(
            photo_url__icontains='breedarchive'
        ).exclude(photo_url=None).exclude(photo_url='')

        total = dogs.count()
        self.stdout.write(f'Найдено записей с breedarchive: {total}')

        if dry_run:
            for dog in dogs[:10]:
                new_url = self._fix_url(dog.photo_url)
                self.stdout.write(f'  [{dog.pk}] {repr(dog.photo_url)}')
                self.stdout.write(f'        → {repr(new_url)}')
            self.stdout.write('(dry-run, БД не изменена)')
            return

        updated = 0
        for dog in dogs.iterator(chunk_size=500):
            new_url = self._fix_url(dog.photo_url)
            if new_url != dog.photo_url:
                Dog.objects.using('dogs_db').filter(pk=dog.pk).update(photo_url=new_url)
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Готово. Обновлено: {updated}'))

    def _fix_url(self, url: str) -> str:
        # 1. Убираем мусорные непечатаемые байты с конца (\x01 и подобные)
        url = url.strip().rstrip('\x00\x01\x02\x03')

        # 2. Если нет расширения — добавляем .jpg
        if not re.search(r'\.[a-z]{3,4}$', url, re.IGNORECASE):
            url = url + '.jpg'

        # 3. Убираем _s перед расширением: photo_s.jpg → photo.jpg
        url = re.sub(r'_s(\.[a-z]{3,4})$', r'\1', url, flags=re.IGNORECASE)

        return url