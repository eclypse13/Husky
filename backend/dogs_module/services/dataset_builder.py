"""
Сборщик датасета для обучения ML модели.
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
    return float(value) if value else None


def _load_parent_map(seed_ids: set[int], depth: int) -> dict[int, tuple]:
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
    offspring_list = dog_repo.get_offspring_with_parents_values()
    if not offspring_list:
        return [], 0

    seed_parents: set[int] = set()
    for d in offspring_list:
        if d["sire_id"]:
            seed_parents.add(d["sire_id"])
        if d["dam_id"]:
            seed_parents.add(d["dam_id"])
    parent_map = _load_parent_map(seed_parents, ANCESTOR_DEPTH)

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

    scores_by_dog = {
        dog_id: extract_scores(recs) for dog_id, recs in records_by_dog.items()
    }

    parent_coi = dog_repo.get_coi_map(
        {d["sire_id"] for d in offspring_list} | {d["dam_id"] for d in offspring_list}
    )

    dataset: list[dict] = []
    skipped = 0

    for d in offspring_list:
        dog_id, sire_id, dam_id = d["id"], d["sire_id"], d["dam_id"]

        offspring_scores = scores_by_dog.get(dog_id, {})
        has_hips = "hips" in offspring_scores
        has_eyes = "eyes" in offspring_scores

        # Потомок попадает в выборку, если есть хотя бы один из двух тестов.
        if not has_hips and not has_eyes:
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
        # Метки: None если соответствующего теста нет
        row.update({
            "offspring_has_hip_problem": (
                int(offspring_scores["hips"] >= HIP_PROBLEM_THRESHOLD)
                if has_hips else None
            ),
            "offspring_has_eye_problem": (
                int(offspring_scores["eyes"] >= EYE_PROBLEM_THRESHOLD)
                if has_eyes else None
            ),
            "_synthetic": False,
            "_offspring_id": dog_id,
            "_sire_id": sire_id,
            "_dam_id": dam_id,
        })
        dataset.append(row)

    return dataset, skipped


def build_dataset(augment: bool = False, n_synthetic: int = 3000) -> list[dict]:
    logger.info("Сборка датасета...")

    offspring_count = dog_repo.count_offspring_with_parents()
    logger.info(f"Потомков с известными родителями: {offspring_count}")

    real_data, skipped = _build_real_dataset()
    logger.info(f"Реальных записей с меткой (hips или eyes): {len(real_data)}")

    if not real_data:
        logger.warning("Нет реальных данных")
        return []

    total = len(real_data)
    # Корректный подсчёт: исключаем None при суммировании
    hip_labeled = [d for d in real_data if d["offspring_has_hip_problem"] is not None]
    eye_labeled = [d for d in real_data if d["offspring_has_eye_problem"] is not None]
    hip_pos = sum(d["offspring_has_hip_problem"] for d in hip_labeled)
    eye_pos = sum(d["offspring_has_eye_problem"] for d in eye_labeled)

    logger.info(
        f"Реальный датасет: {total} записей, пропущено: {skipped}\n"
        f" с меткой по бёдрам: {len(hip_labeled)} (позитивов {hip_pos})\n"
        f" с меткой по глазам: {len(eye_labeled)} (позитивов {eye_pos})"
    )

    if not augment:
        return real_data

    from .synthetic_generator import generate_synthetic_dataset
    synthetic = generate_synthetic_dataset(n_samples=n_synthetic)

    combined = real_data + synthetic
    total_c = len(combined)
    hip_labeled_c = [d for d in combined if d.get("offspring_has_hip_problem") is not None]
    eye_labeled_c = [d for d in combined if d.get("offspring_has_eye_problem") is not None]
    hip_c = sum(d["offspring_has_hip_problem"] for d in hip_labeled_c)
    eye_c = sum(d["offspring_has_eye_problem"] for d in eye_labeled_c)

    logger.info(
        f"Итоговый датасет (реальные + синтетика): {total_c} записей\n"
        f" с меткой по бёдрам: {len(hip_labeled_c)} (позитивов {hip_c})\n"
        f" с меткой по глазам: {len(eye_labeled_c)} (позитивов {eye_c})"
    )

    return combined


def save_dataset_csv(path: str = "/tmp/ofa_dataset.csv", augment: bool = False) -> str:
    import csv
    dataset = build_dataset(augment=augment)
    if not dataset:
        return ""
    fieldnames = list({k for row in dataset for k in row.keys()})
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dataset)
    logger.info(f"Сохранено: {path} ({len(dataset)} строк)")
    return path
