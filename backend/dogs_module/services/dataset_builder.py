# dogs_module/services/dataset_builder.py
"""
Сборщик датасета для обучения ML модели.

Реальные данные берутся из БД (включая агрегаты по предкам).
"""

import logging

from ..domain.health_codes import (
    extract_scores,
    HIP_PROBLEM_THRESHOLD,
    EYE_PROBLEM_THRESHOLD,
)
from ..repositories import dog_repository as dog_repo
from ..repositories import medical_record_repository as med_repo
from .ancestor_features import ANCESTOR_DEPTH
from .feature_builder import build_feature_row

logger = logging.getLogger(__name__)


def _as_pct(value) -> float | None:
    """COI хранится в процентах; приводим к float или None."""
    return float(value) if value else None


def _load_parent_map(seed_ids: set[int], depth: int) -> dict[int, tuple]:
    """
    Строит скелет дерева предков {id: (sire_id, dam_id)} для всех seed_ids и их
    предков на `depth` поколений вверх. Один батч-запрос на поколение —
    никаких N+1. Используется для in-memory обхода в ancestor_features.
    """
    parent_map: dict[int, tuple] = {}
    front = {i for i in seed_ids if i}

    for _ in range(depth):
        unknown = {i for i in front if i not in parent_map}
        if not unknown:
            break
        rows = dog_repo.get_parents_batch_values(unknown)
        nxt: set[int] = set()
        for row in rows:
            parent_map[row["id"]] = (row.get("sire_id"), row.get("dam_id"))
            for pid in (row.get("sire_id"), row.get("dam_id")):
                if pid:
                    nxt.add(pid)
        front = nxt

    return parent_map


def _build_real_dataset() -> tuple[list[dict], int]:
    """Собирает реальные данные из БД. Возвращает (dataset, skipped)."""
    offspring_list = dog_repo.get_offspring_with_parents_values()
    if not offspring_list:
        return [], 0

    # 1) Скелет дерева предков (для агрегатов по предкам, in-memory обход).
    seed_parents: set[int] = set()
    for d in offspring_list:
        if d["sire_id"]:
            seed_parents.add(d["sire_id"])
        if d["dam_id"]:
            seed_parents.add(d["dam_id"])
    parent_map = _load_parent_map(seed_parents, ANCESTOR_DEPTH)

    # 2) Все id, для которых нужны OFA-записи: потомки + родители + все предки.
    all_ids: set[int] = set()
    for d in offspring_list:
        all_ids.update({d["id"], d["sire_id"], d["dam_id"]})
    all_ids.update(parent_map.keys())
    for s_id, d_id in parent_map.values():
        all_ids.update({s_id, d_id})
    all_ids.discard(None)

    records_raw = med_repo.get_ofa_records_for_dogs_values(all_ids)
    records_by_dog: dict[int, list] = {}
    for rec in records_raw:
        records_by_dog.setdefault(rec["dog_id"], []).append(rec)

    # 3) Баллы по каждой собаке (родители + предки) — единой extract_scores.
    scores_by_dog = {
        dog_id: extract_scores(recs) for dog_id, recs in records_by_dog.items()
    }

    # 4) COI родителей.
    parent_coi = dog_repo.get_coi_map(
        {d["sire_id"] for d in offspring_list} | {d["dam_id"] for d in offspring_list}
    )

    dataset: list[dict] = []
    skipped = 0

    for d in offspring_list:
        dog_id, sire_id, dam_id = d["id"], d["sire_id"], d["dam_id"]

        # Метка есть только если у потомка известен результат по бёдрам.
        offspring_scores = scores_by_dog.get(dog_id, {})
        if "hips" not in offspring_scores:
            skipped += 1
            continue

        row = build_feature_row(
            sire_scores=scores_by_dog.get(sire_id, {}),
            dam_scores=scores_by_dog.get(dam_id, {}),
            sire_coi=_as_pct(parent_coi.get(sire_id)),
            dam_coi=_as_pct(parent_coi.get(dam_id)),
            pair_coi=_as_pct(d.get("coi")),
            sire_id=sire_id,
            dam_id=dam_id,
            scores_by_dog=scores_by_dog,
            parent_map=parent_map,
        )
        row.update({
            "offspring_has_hip_problem": int(offspring_scores["hips"] >= HIP_PROBLEM_THRESHOLD),
            "offspring_has_eye_problem": int(offspring_scores.get("eyes", 0) >= EYE_PROBLEM_THRESHOLD),
            "_synthetic": False,
            "_offspring_id": dog_id,
            "_sire_id": sire_id,
            "_dam_id": dam_id,
        })
        dataset.append(row)

    return dataset, skipped


def build_dataset(augment: bool = False, n_synthetic: int = 3000) -> list[dict]:
    """
    Собирает датасет для обучения ML.

    augment     — добавить синтетические данные
    n_synthetic — сколько синтетических записей добавить

    Синтетические данные существуют только в памяти во время обучения.
    """
    logger.info("Сборка датасета...")

    offspring_count = dog_repo.count_offspring_with_parents()
    logger.info(f"Потомков с известными родителями: {offspring_count}")

    real_data, skipped = _build_real_dataset()
    logger.info(f"Реальных записей с меткой по бёдрам: {len(real_data)}")

    if not real_data:
        logger.warning("Нет реальных данных")
        return []

    total = len(real_data)
    hip_pos = sum(d["offspring_has_hip_problem"] for d in real_data)
    eye_pos = sum(d["offspring_has_eye_problem"] for d in real_data)

    logger.info(
        f"Реальный датасет: {total} записей, пропущено: {skipped}\n"
        f"  бёдра (Borderline+): {hip_pos} ({hip_pos / total:.1%})\n"
        f"  глаза: {eye_pos} ({eye_pos / total:.1%})"
    )

    if not augment:
        return real_data

    from .synthetic_generator import generate_synthetic_dataset
    synthetic = generate_synthetic_dataset(n_samples=n_synthetic)

    combined = real_data + synthetic
    total_c = len(combined)
    hip_c = sum(d["offspring_has_hip_problem"] for d in combined)
    eye_c = sum(d["offspring_has_eye_problem"] for d in combined)

    logger.info(
        f"Итоговый датасет (реальные + синтетика): {total_c} записей\n"
        f"  бёдра (Borderline+): {hip_c} ({hip_c / total_c:.1%})\n"
        f"  глаза: {eye_c} ({eye_c / total_c:.1%})"
    )

    return combined


def save_dataset_csv(path: str = "/tmp/ofa_dataset.csv", augment: bool = False) -> str:
    """Сохраняет датасет в CSV для анализа."""
    import csv
    dataset = build_dataset(augment=augment)
    if not dataset:
        return ""
    # Объединение ключи всех строк (у реальных и синтетических набор совпадает,
    # но на всякий случай берется union для устойчивости заголовка).
    fieldnames = list({k for row in dataset for k in row.keys()})
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dataset)
    logger.info(f"Сохранено: {path} ({len(dataset)} строк)")
    return path
