# dogs_module/repositories/medical_record_repository.py
"""
Доступ к данным MedicalRecord.
"""

import logging

logger = logging.getLogger(__name__)


def filter_records(dog_id=None, source: str = None):
    """
    QuerySet MedicalRecord с опциональными фильтрами для API.
    Используется MedicalRecordViewSet.get_queryset.
    """
    from ..models import MedicalRecord
    qs = MedicalRecord.objects.using('dogs_db')
    if dog_id:
        qs = qs.filter(dog_id=dog_id)
    if source:
        qs = qs.filter(source=source)
    return qs.order_by('-test_date')


# ЧТЕНИЕ (.values)

def get_ofa_records_for_dogs_values(dog_ids) -> list:
    """OFA-записи (registry, conclusion, test_date) для набора собак — один SQL."""
    from ..models import MedicalRecord
    if not dog_ids:
        return []
    return list(
        MedicalRecord.objects.using('dogs_db')
        .filter(dog_id__in=dog_ids, source='ofa')
        .values('dog_id', 'registry', 'conclusion', 'test_date')
    )


def get_ofa_hips_for_dogs_values(dog_ids) -> list:
    """Только HIPS OFA-записи для набора собак (для расчёта дисплазии по родословной)."""
    from ..models import MedicalRecord
    if not dog_ids:
        return []
    return list(
        MedicalRecord.objects.using('dogs_db')
        .filter(dog_id__in=dog_ids, source='ofa', registry='HIPS')
        .values('dog_id', 'registry', 'conclusion', 'test_date')
    )


def get_ofa_records_for_dog_values(dog_id: int) -> list:
    """OFA registry+conclusion одной собаки (для подготовки данных в ML)."""
    from ..models import MedicalRecord
    return list(
        MedicalRecord.objects.using('dogs_db')
        .filter(dog_id=dog_id, source='ofa')
        .values('registry', 'conclusion')
    )


def get_dog_ids_with_ofa() -> set:
    """
    id всех собак у которых уже есть хотя бы одна OFA-запись.
    Используется в dog_service для исключения уже обработанных собак из bulk-импорта.
    """
    from ..models import MedicalRecord
    return set(
        MedicalRecord.objects.using('dogs_db')
        .filter(source='ofa')
        .values_list('dog_id', flat=True)
        .distinct()
    )


# ЗАПИСЬ

def upsert_ofa_record(dog, ofa_number: str, fields: dict) -> bool:
    """update_or_create одной OFA-записи. Возвращает created (True/False)."""
    from ..models import MedicalRecord
    _, created = MedicalRecord.objects.using('dogs_db').update_or_create(
        dog=dog,
        ofa_number=ofa_number,
        defaults=fields,
    )
    return created


def bulk_upsert_ofa_records(dog, records: list) -> tuple:
    """
    Батч update_or_create OFA-записей для одной собаки.
    Возвращает (saved_count, failed_count). Дубликаты по (dog, ofa_number)
    идемпотентны — запускать можно сколько угодно раз.
    """
    from ..models import MedicalRecord
    if dog is None or not records:
        return 0, 0
    saved = failed = 0
    for rec in records:
        ofa_num = (rec.get("ofa_number") or "").strip()
        # У OFA бывают записи без OFA Number (например, CHIC summary).
        # Их не сохраняем — идемпотентность по (dog, ofa_number) ломается.
        if not ofa_num:
            continue
        try:
            MedicalRecord.objects.using('dogs_db').update_or_create(
                dog=dog,
                ofa_number=ofa_num,
                defaults={
                    "registry": rec.get("registry", ""),
                    "test_date": rec.get("test_date"),
                    "report_date": rec.get("report_date"),
                    "age_in_months": rec.get("age_in_months"),
                    "conclusion": rec.get("conclusion", ""),
                    "source": "ofa",
                },
            )
            saved += 1
        except Exception as e:
            failed += 1
            logger.warning(f"OFA upsert record {ofa_num} for dog {dog.id}: {e}")
    return saved, failed
