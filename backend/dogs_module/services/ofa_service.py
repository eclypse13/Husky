# dogs_module/services/ofa_service.py
"""
OFA-специфичный сервис
"""

import logging

logger = logging.getLogger(__name__)


def save_ofa_records(dog_id: int, records: list) -> tuple:
    """
    Сохраняет медицинские записи OFA для собаки.

    Ключ update_or_create: (dog, ofa_number) — дублей не будет.
    Записи без ofa_number пропускаются — нечем идентифицировать.

    Возвращает (saved_count, failed_count).
    """
    from ..models import Dog, MedicalRecord

    try:
        dog = Dog.objects.using("dogs_db").get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"ofa_service: dog_id={dog_id} не найдена")
        return 0, len(records)

    saved = failed = 0
    for rec in records:
        ofa_num = (rec.get("ofa_number") or "").strip()
        if not ofa_num:
            failed += 1
            logger.debug(f"ofa_service: пропуск записи без ofa_number: {rec}")
            continue

        try:
            _, created = MedicalRecord.objects.using("dogs_db").update_or_create(
                dog=dog,
                ofa_number=ofa_num,
                defaults={
                    "registry":      rec.get("registry", ""),
                    "test_date":     rec.get("test_date"),
                    "report_date":   rec.get("report_date"),
                    "age_in_months": rec.get("age_in_months"),
                    "conclusion":    rec.get("conclusion", ""),
                    "source":        "ofa",
                },
            )
            saved += 1
            logger.debug(
                f"ofa_service: {ofa_num} — {'создана' if created else 'обновлена'}"
            )
        except Exception as e:
            failed += 1
            logger.warning(
                f"ofa_service: ошибка сохранения {ofa_num} "
                f"для dog_id={dog_id}: {e}"
            )

    logger.info(
        f"ofa_service: dog_id={dog_id} — сохранено={saved}, ошибок={failed}"
    )
    return saved, failed