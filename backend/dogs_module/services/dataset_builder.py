# dogs_module/services/dataset_builder.py
"""
Сборщик датасета для обучения ML модели.

Достаёт из БД исторические данные о парах и их потомках.
Результат — список записей готовых для отправки в ML сервис.

Можно запустить в любой момент:
  from dogs_module.services.dataset_builder import build_dataset
  dataset = build_dataset()
  print(f"Собрано {len(dataset)} записей")
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Маппинг OFA результатов в числа
HIP_SCORE_MAP = {
    "EXCELLENT":  0,
    "GOOD":       1,
    "FAIR":       2,
    "BORDERLINE": 3,
    "MILD":       4,
    "MODERATE":   5,
    "SEVERE":     6,
}

EYE_SCORE_MAP = {
    "NORMAL":   0,
    "AFFECTED": 1,
}

# Дисплазия = Borderline и хуже
DYSPLASIA_THRESHOLD = 3


def _get_hip_score(dog_id: int, records_by_dog: dict) -> Optional[int]:
    """Берёт последний результат теста бёдер для собаки."""
    records = records_by_dog.get(dog_id, [])
    hip_records = [r for r in records if r["registry"] == "HIPS"]
    if not hip_records:
        return None
    # Берём последний по дате
    latest = max(hip_records, key=lambda r: r["test_date"] or "")
    conclusion = (latest["conclusion"] or "").upper().strip()
    return HIP_SCORE_MAP.get(conclusion)


def _get_eye_score(dog_id: int, records_by_dog: dict) -> Optional[int]:
    """Берёт результат теста глаз."""
    records = records_by_dog.get(dog_id, [])
    eye_records = [
        r for r in records
        if "EYE" in r["registry"].upper() or "OPTH" in r["registry"].upper()
    ]
    if not eye_records:
        return None
    latest = max(eye_records, key=lambda r: r["test_date"] or "")
    conclusion = (latest["conclusion"] or "").upper().strip()
    return EYE_SCORE_MAP.get(conclusion)


def build_dataset() -> list[dict]:
    """
    Собирает датасет из БД.

    Алгоритм:
    1. Берём всех потомков у которых есть тест бёдер
    2. Для каждого достаём родителей (sire, dam)
    3. Берём данные здоровья родителей
    4. Формируем запись: признаки пары → результат потомка

    Возвращает список dict готовых для отправки в /breeding/train
    """
    from ..models import Dog, MedicalRecord

    logger.info("Сборка датасета...")

    # Шаг 1: все потомки у которых есть тест бёдер И известны оба родителя
    offspring_qs = (
        Dog.objects
        .using("dogs_db")
        .filter(
            sire_id__isnull=False,
            dam_id__isnull=False,
        )
        .values("id", "sire_id", "dam_id", "coi")
    )
    offspring_list = list(offspring_qs)
    logger.info(f"Потомков с известными родителями: {len(offspring_list)}")

    if not offspring_list:
        logger.warning("Нет потомков с известными родителями")
        return []

    # Собираем все ID которые нам нужны
    all_dog_ids = set()
    for dog in offspring_list:
        all_dog_ids.add(dog["id"])
        all_dog_ids.add(dog["sire_id"])
        all_dog_ids.add(dog["dam_id"])

    # Шаг 2: все медицинские записи OFA для этих собак одним запросом
    records_qs = (
        MedicalRecord.objects
        .using("dogs_db")
        .filter(
            dog_id__in=all_dog_ids,
            source="ofa",
        )
        .values("dog_id", "registry", "conclusion", "test_date")
    )

    # Группируем по dog_id для быстрого доступа
    records_by_dog: dict = {}
    for rec in records_qs:
        dog_id = rec["dog_id"]
        if dog_id not in records_by_dog:
            records_by_dog[dog_id] = []
        records_by_dog[dog_id].append(rec)

    logger.info(f"Загружено OFA записей для {len(records_by_dog)} собак")

    # Шаг 3: берём COI для родителей
    parent_ids = {d["sire_id"] for d in offspring_list} | {d["dam_id"] for d in offspring_list}
    parents_coi = dict(
        Dog.objects
        .using("dogs_db")
        .filter(id__in=parent_ids)
        .values_list("id", "coi")
    )

    # Шаг 4: формируем датасет
    dataset = []
    skipped = 0

    for dog in offspring_list:
        dog_id = dog["id"]
        sire_id = dog["sire_id"]
        dam_id = dog["dam_id"]

        # Результат потомка — тест бёдер
        offspring_hip = _get_hip_score(dog_id, records_by_dog)
        if offspring_hip is None:
            skipped += 1
            continue  # нет теста у потомка — не можем обучить

        # Целевая переменная: 1 = дисплазия, 0 = здоров
        has_dysplasia = 1 if offspring_hip >= DYSPLASIA_THRESHOLD else 0

        # Признаки родителей
        sire_hips = _get_hip_score(sire_id, records_by_dog)
        sire_eyes = _get_eye_score(sire_id, records_by_dog)
        sire_coi = parents_coi.get(sire_id)

        dam_hips = _get_hip_score(dam_id, records_by_dog)
        dam_eyes = _get_eye_score(dam_id, records_by_dog)
        dam_coi = parents_coi.get(dam_id)

        # COI потомства (уже есть в БД)
        pair_coi = dog.get("coi")

        # Средний балл бёдер родителей
        scores = [s for s in [sire_hips, dam_hips] if s is not None]
        avg_hip = sum(scores) / len(scores) if scores else None

        dataset.append({
            # Признаки
            "sire_hips":         sire_hips,
            "sire_eyes":         sire_eyes,
            "sire_coi":          float(sire_coi) if sire_coi else None,
            "dam_hips":          dam_hips,
            "dam_eyes":          dam_eyes,
            "dam_coi":           float(dam_coi) if dam_coi else None,
            "pair_coi":          float(pair_coi) if pair_coi else None,
            "hip_ratio_4gen":    None,  # TODO: считать из родословной
            "avg_hip_score":     avg_hip,

            # Целевая переменная
            "offspring_has_dysplasia": has_dysplasia,

            # Мета (не используется в обучении, для анализа)
            "_offspring_id": dog_id,
            "_sire_id":      sire_id,
            "_dam_id":       dam_id,
            "_hip_raw":      offspring_hip,
        })

    logger.info(
        f"Датасет: {len(dataset)} записей, "
        f"пропущено (нет теста): {skipped}, "
        f"дисплазия: {sum(d['offspring_has_dysplasia'] for d in dataset)} "
        f"({sum(d['offspring_has_dysplasia'] for d in dataset)/len(dataset):.1%})"
        if dataset else "датасет пустой"
    )

    return dataset


def save_dataset_csv(path: str = "/tmp/ofa_dataset.csv") -> str:
    """
    Сохраняет датасет в CSV файл.
    Удобно для анализа и отладки перед обучением.
    """
    import csv

    dataset = build_dataset()
    if not dataset:
        logger.warning("Датасет пустой, CSV не создан")
        return ""

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
        writer.writeheader()
        writer.writerows(dataset)

    logger.info(f"Датасет сохранён: {path} ({len(dataset)} строк)")
    return path
