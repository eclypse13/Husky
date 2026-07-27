"""
Management-команда: пересчитывает задним числом баллы уже сохранённых
результатов

Использование:
    python manage.py recalc_show_points
    python manage.py recalc_show_points --years 2025 2026
    python manage.py recalc_show_points --dry-run
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Пересчитывает задним числом show_type, rating_points, nomination и рейтинги"

    def add_arguments(self, parser):
        parser.add_argument(
            "--years", nargs="*", type=int, default=None,
            help="Пересчитать рейтинг только для этих рейтинговых годов "
                 "(по умолчанию — для всех годов, встретившихся в датах выставок)",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Только посчитать и вывести статистику изменений, ничего не сохранять",
        )

    def handle(self, *args, **options):
        from ...models import ShowEvent, ShowResult
        from ...services.show_service import (
            detect_show_type,
            calc_result_points,
            detect_nomination,
            recalculate_all_ratings,
            get_rating_year,
        )
        from ...config import SHOW_MULTIPLIERS

        dry_run = options["dry_run"]

        # --- 1. Переопределяем show_type/multiplier у ShowEvent ---
        events = ShowEvent.objects.using("dogs_db").all()
        events_total = events.count()
        events_changed = 0

        self.stdout.write(f"Проверяю {events_total} выставок…")

        for event in events.iterator(chunk_size=500):
            new_type = detect_show_type(event.title or "", event.rank or "")
            new_multiplier = SHOW_MULTIPLIERS.get(new_type, 0.0)
            if new_type != event.show_type or new_multiplier != event.multiplier:
                events_changed += 1
                if not dry_run:
                    event.show_type = new_type
                    event.multiplier = new_multiplier
                    event.save(update_fields=["show_type", "multiplier"])

        self.stdout.write(self.style.SUCCESS(
            f"Выставок с изменённым типом: {events_changed} из {events_total}"
        ))

        # --- 2. Переопределяем rating_points/nomination у ShowResult ---
        results = (
            ShowResult.objects.using("dogs_db")
            .select_related("event")
            .filter(event__isnull=False, dog__isnull=False)
        )
        results_total = results.count()
        results_changed = 0
        years_touched = set()

        self.stdout.write(f"Проверяю {results_total} результатов…")

        for r in results.iterator(chunk_size=500):
            new_points = calc_result_points(
                r.titles_won,
                r.event.show_type,
                r.catalog_count or 0,
                r.bonus_points or 0,
            )
            new_nomination = detect_nomination(r.show_class, r.titles_won)

            if new_points != r.rating_points or new_nomination != r.nomination:
                results_changed += 1
                if not dry_run:
                    r.rating_points = new_points
                    r.nomination = new_nomination
                    r.save(update_fields=["rating_points", "nomination"])

            if r.event.event_date:
                years_touched.add(get_rating_year(r.event.event_date))

        self.stdout.write(self.style.SUCCESS(
            f"Результатов с изменёнными баллами/номинацией: {results_changed} из {results_total}"
        ))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "--dry-run: изменения не сохранены, рейтинги НЕ пересчитаны"
            ))
            return

        # --- 3. Пересобираем кэш ShowYearlyRating / Dog.rating ---
        target_years = options["years"] or sorted(years_touched)
        if not target_years:
            self.stdout.write(self.style.WARNING("Нет годов для пересчёта рейтинга"))
            return

        for year in target_years:
            result = recalculate_all_ratings(rating_year=year)
            self.stdout.write(
                f"Год {year}: обновлено {result['updated']} собак "
                f"({result['date_from']} — {result['date_to']})"
            )

        self.stdout.write(self.style.SUCCESS("Готово."))
