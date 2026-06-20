"""
Использование:
    docker compose exec web python manage.py import_health_records data/records.csv --dry-run
    docker compose exec web python manage.py import_health_records data/records.csv --fci-hip --fci-elbow --verify --dry-run
    docker compose exec web python manage.py import_health_records data/records.csv --fci-hip --fci-elbow --verify
"""

import csv
import logging
from datetime import datetime, time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

FCI_TO_OFA_HIP = {
    "A": "GOOD", "B": "FAIR", "C": "MILD", "D": "MODERATE", "E": "SEVERE",
}
FCI_TO_OFA_ELBOW = {
    "0": "NORMAL", "1": "GRADE1", "2": "GRADE2", "3": "GRADE3",
}


def find_dog(Dog, regnum: str, expected_name: str, stdout, style, row_idx: int):
    digits_only = "".join(ch for ch in regnum if ch.isdigit()) if regnum else ""

    # Шаг 1: поиск по registration_number (если regnum осмысленный)
    if len(digits_only) >= 5:
        candidates = list(
            Dog.objects.filter(registration_number__icontains=digits_only)
            .order_by("id")[:5]
        )
        if candidates:
            if len(candidates) > 1:
                stdout.write(style.WARNING(
                    f"Строка {row_idx}: для regnum={regnum} найдено {len(candidates)} по RKF:"))
                for c in candidates:
                    stdout.write(
                        f"    id={c.id}  {c.display_name}  (regnum={c.registration_number})"
                    )
                return candidates[0], "multiple_regnum"
            return candidates[0], "found"

    # Шаг 2: поиск по имени
    if expected_name:
        name_upper = expected_name.upper()
        # Ищем в registered_name / call_name / link_name (case-insensitive)
        candidates = list(
            Dog.objects.filter(
                Q(registered_name__icontains=name_upper) |
                Q(call_name__icontains=name_upper) |
                Q(link_name__icontains=name_upper)
            ).order_by("id")[:10]
        )

        if not candidates:
            return None, "not_found"

        if len(candidates) == 1:
            dog = candidates[0]
            stdout.write(style.NOTICE(
                f"Строка {row_idx}: regnum пуст/не найден, но по имени '{expected_name}' "
                f"найден id={dog.id} {dog.display_name} (regnum={dog.registration_number})"
            ))
            return dog, "found"

        # Несколько по имени — однозначно сказать нельзя, не подставляем
        stdout.write(style.ERROR(
            f"Строка {row_idx}: по имени '{expected_name}' найдено {len(candidates)} кандидатов, "
            f"нужно уточнить regnum в CSV:"))
        for c in candidates:
            stdout.write(
                f"    id={c.id}  {c.display_name}  reg={c.registered_name}  "
                f"call={c.call_name}  link={c.link_name}  regnum={c.registration_number}"
            )
        return None, "multiple_name"

    return None, "not_found"


class Command(BaseCommand):
    help = "Импорт сертификатов из CSV в MedicalRecord. Поиск по regnum, затем по имени."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--dry-run", action="store_true",
                            help="Только показать что будет добавлено, без записи")
        parser.add_argument("--fci-hip", action="store_true",
                            help="Конвертировать HIPS=A/B/C/D/E в OFA")
        parser.add_argument("--fci-elbow", action="store_true",
                            help="Конвертировать ELBOW=0/1/2/3 в текст")
        parser.add_argument("--verify", action="store_true",
                            help="При найденной собаке по regnum проверять что её имя похоже на expected_name")

    def handle(self, *args, **opts):
        from ...models import Dog, MedicalRecord

        csv_path = Path(opts["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"Файл не найден: {csv_path}")

        dry_run = opts["dry_run"]
        fci_hip = opts["fci_hip"]
        fci_elbow = opts["fci_elbow"]
        verify = opts["verify"]

        stats = {"created": 0, "skipped_exists": 0, "skipped_no_dog": 0,
                 "skipped_name_mismatch": 0, "skipped_ambiguous": 0, "errors": 0}

        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            required = {"regnum", "registry", "conclusion"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f"В CSV отсутствуют колонки: {missing}")

            with transaction.atomic():
                for i, row in enumerate(reader, start=2):
                    try:
                        regnum = (row.get("regnum") or "").strip()
                        registry = (row.get("registry") or "").strip().upper()
                        conclusion = (row.get("conclusion") or "").strip().upper()
                        test_date_str = (row.get("test_date") or "").strip()
                        source = (row.get("source") or "manual").strip().lower()
                        expected_name = (row.get("expected_name") or "").strip()
                        ofa_number = (row.get("ofa_number") or "").strip() or None
                        notes = (row.get("notes") or "").strip() or None

                        if not registry or not conclusion:
                            self.stdout.write(self.style.WARNING(
                                f"Строка {i}: пропуск (пустые registry/conclusion)"))
                            stats["errors"] += 1
                            continue

                        if not regnum and not expected_name:
                            self.stdout.write(self.style.WARNING(
                                f"Строка {i}: пропуск (ни regnum, ни expected_name не указаны)"))
                            stats["errors"] += 1
                            continue

                        # Конверсии FCI → OFA
                        if fci_hip and registry == "HIPS" and conclusion in FCI_TO_OFA_HIP:
                            conclusion = FCI_TO_OFA_HIP[conclusion]
                        if fci_elbow and registry == "ELBOW" and conclusion in FCI_TO_OFA_ELBOW:
                            conclusion = FCI_TO_OFA_ELBOW[conclusion]

                        # Дата → aware datetime
                        test_date = None
                        if test_date_str:
                            try:
                                d = datetime.strptime(test_date_str, "%Y-%m-%d")
                                test_date = timezone.make_aware(
                                    datetime.combine(d.date(), time(12, 0))
                                )
                            except ValueError:
                                self.stdout.write(self.style.WARNING(
                                    f"Строка {i}: некорректная дата '{test_date_str}'"))

                        # Двухступенчатый поиск
                        dog, status = find_dog(
                            Dog, regnum, expected_name, self.stdout, self.style, i
                        )

                        if status == "not_found":
                            self.stdout.write(self.style.WARNING(
                                f"Строка {i}: regnum={regnum or '-'}, name='{expected_name or '-'}' "
                                f"→ собака не найдена"))
                            stats["skipped_no_dog"] += 1
                            continue

                        if status == "multiple_name":
                            stats["skipped_ambiguous"] += 1
                            continue

                        # status in ("found", "multiple_regnum") → dog не None
                        # При --verify дополнительная проверка имени (только когда искали по regnum)
                        if verify and expected_name and status in ("found", "multiple_regnum"):
                            exp = expected_name.upper()
                            dog_name = (dog.display_name or "").upper()
                            reg_name = (dog.registered_name or "").upper()
                            call_name = (dog.call_name or "").upper()
                            link_name = (dog.link_name or "").upper()

                            in_any = any(
                                exp in n or (n and n in exp)
                                for n in (dog_name, reg_name, call_name, link_name) if n
                            )
                            if not in_any:
                                self.stdout.write(self.style.ERROR(
                                    f"Строка {i}: ОЖИДАЛИ '{expected_name}', НАШЛИ "
                                    f"'{dog.display_name}' (regnum={dog.registration_number}) → пропуск"
                                ))
                                stats["skipped_name_mismatch"] += 1
                                continue

                        # Идемпотентность
                        existing = MedicalRecord.objects.filter(
                            dog=dog, registry=registry, conclusion=conclusion
                        ).exists()

                        if dry_run:
                            tag = "EXISTS" if existing else "WILL CREATE"
                            self.stdout.write(
                                f"[{tag}] id={dog.id} | {dog.display_name} | "
                                f"{registry} | {conclusion} | {test_date_str} | {source}"
                            )
                            if existing:
                                stats["skipped_exists"] += 1
                            else:
                                stats["created"] += 1
                        else:
                            if existing:
                                stats["skipped_exists"] += 1
                            else:
                                MedicalRecord.objects.create(
                                    dog=dog,
                                    registry=registry,
                                    conclusion=conclusion,
                                    test_date=test_date,
                                    source=source,
                                    ofa_number=ofa_number,
                                    notes=notes,
                                )
                                stats["created"] += 1
                                self.stdout.write(self.style.SUCCESS(
                                    f"OK строка {i}: {dog.display_name} → {registry}={conclusion}"
                                ))

                    except Exception as e:
                        logger.exception(f"Строка {i}: ошибка")
                        self.stdout.write(self.style.ERROR(f"Строка {i}: {e}"))
                        stats["errors"] += 1

                if dry_run:
                    transaction.set_rollback(True)

        verb = "Будет добавлено" if dry_run else "Добавлено"
        self.stdout.write(self.style.SUCCESS(
            f"\n=== ИТОГО ===\n"
            f"{verb}:                {stats['created']}\n"
            f"Уже есть в БД:             {stats['skipped_exists']}\n"
            f"Собака не найдена:         {stats['skipped_no_dog']}\n"
            f"Имя не совпало с regnum:   {stats['skipped_name_mismatch']}\n"
            f"Неоднозначно по имени:     {stats['skipped_ambiguous']}\n"
            f"Ошибки в данных:           {stats['errors']}"
        ))
