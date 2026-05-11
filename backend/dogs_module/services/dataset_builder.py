# dogs_module/services/dataset_builder.py
"""
Сборщик датасета для обучения ML модели.

Реальные данные берутся из БД.
Синтетические данные генерируются в памяти и НЕ сохраняются в БД.
"""

import logging

logger = logging.getLogger(__name__)

HIP_MAP = {
    "EXCELLENT": 0, "GOOD": 1, "FAIR": 2,
    "BORDERLINE": 3, "MILD": 4, "MODERATE": 5, "SEVERE": 6,
}
ELBOW_MAP = {
    "NORMAL": 0, "GRADE I": 1, "GRADE II": 2, "GRADE III": 3,
    "GRADE1": 1, "GRADE2": 2, "GRADE3": 3,
}
EYE_MAP     = {"NORMAL": 0, "NORMAL W/BO": 0, "AFFECTED": 1}
GENETIC_MAP = {
    "CLEAR/NORMAL": 0, "CLEAR": 0, "NORMAL/CLEAR": 0,
    "CARRIER": 1, "CARRIER-PROBABLE": 1,
    "AFFECTED": 2,
}

REGISTRY_GROUPS = {
    "HIPS": "hips",
    "ELBOW": "elbows",
    "EYES": "eyes",
    "CERF": "eyes",
    "SIBERIAN HUSKY OPTH. REGISTRY": "eyes",
    "PRIMARY LENS LUXATION": "pll",
    "PROGRESSIVE RETINAL ATROPHY": "pra",
    "PRA - CONE ROD DYSTROPHY 3": "pra",
    "EARLY ONSET PRA": "pra",
    "DEGENERATIVE MYELOPATHY": "dm",
    "JUVENILE LARYNGEAL PARALYSIS & POLYNEUROPATHY (LPP)": "lpp",
    "BASIC CARDIAC": "cardiac",
    "ADVANCED CARDIAC": "cardiac",
    "CONGENITAL CARDIAC": "cardiac",
    "THYROID": "thyroid",
    "PATELLA": "patella",
}

GROUP_MAPS = {
    "hips":    HIP_MAP,
    "elbows":  ELBOW_MAP,
    "eyes":    EYE_MAP,
    "pll":     GENETIC_MAP,
    "pra":     GENETIC_MAP,
    "dm":      GENETIC_MAP,
    "lpp":     GENETIC_MAP,
    "cardiac": {
        "NORMAL": 0, "NORMAL-PRACTITIONER": 0,
        "NORMAL-CARDIOLOGIST": 0, "NORMAL AUSC+ECHO": 0,
        "ABNORMAL": 1,
    },
    "thyroid": {"NORMAL": 0, "ABNORMAL": 1},
    "patella": {"NORMAL": 0, "ABNORMAL": 1},
}

HIP_PROBLEM_THRESHOLD   = 2
ELBOW_PROBLEM_THRESHOLD = 1
EYE_PROBLEM_THRESHOLD   = 1


def _extract_scores(records: list) -> dict:
    by_group = {}
    for rec in records:
        registry = rec["registry"].upper().strip()
        group = REGISTRY_GROUPS.get(registry)
        if not group:
            continue
        if group not in by_group:
            by_group[group] = []
        by_group[group].append(rec)

    scores = {}
    for group, recs in by_group.items():
        latest = max(recs, key=lambda r: r["test_date"] or "")
        conclusion = (latest["conclusion"] or "").upper().strip()
        score = GROUP_MAPS[group].get(conclusion)
        if score is None and "CLEAR" in conclusion:
            score = 0
        if score is None and "NORMAL" in conclusion:
            score = 0
        if score is None and "CARRIER" in conclusion:
            score = 1
        if score is not None:
            scores[group] = score
    return scores


def _build_real_dataset() -> list[dict]:
    """Собирает реальные данные из БД."""
    from ..models import Dog, MedicalRecord

    offspring_list = list(
        Dog.objects.using("dogs_db")
        .filter(sire_id__isnull=False, dam_id__isnull=False)
        .values("id", "sire_id", "dam_id", "coi")
    )

    if not offspring_list:
        return []

    all_ids = set()
    for dog in offspring_list:
        all_ids.add(dog["id"])
        all_ids.add(dog["sire_id"])
        all_ids.add(dog["dam_id"])

    records_raw = list(
        MedicalRecord.objects.using("dogs_db")
        .filter(dog_id__in=all_ids, source="ofa")
        .values("dog_id", "registry", "conclusion", "test_date")
    )

    records_by_dog = {}
    for rec in records_raw:
        did = rec["dog_id"]
        if did not in records_by_dog:
            records_by_dog[did] = []
        records_by_dog[did].append(rec)

    parent_ids = (
        {d["sire_id"] for d in offspring_list} |
        {d["dam_id"]  for d in offspring_list}
    )
    parent_coi = dict(
        Dog.objects.using("dogs_db")
        .filter(id__in=parent_ids)
        .values_list("id", "coi")
    )

    dataset = []
    skipped = 0

    for dog in offspring_list:
        dog_id  = dog["id"]
        sire_id = dog["sire_id"]
        dam_id  = dog["dam_id"]

        offspring_scores = _extract_scores(records_by_dog.get(dog_id, []))
        if "hips" not in offspring_scores:
            skipped += 1
            continue

        sire_scores = _extract_scores(records_by_dog.get(sire_id, []))
        dam_scores  = _extract_scores(records_by_dog.get(dam_id, []))
        sire_coi    = parent_coi.get(sire_id)
        dam_coi     = parent_coi.get(dam_id)
        pair_coi    = dog.get("coi")

        avg_hip = None
        if sire_scores.get("hips") is not None and dam_scores.get("hips") is not None:
            avg_hip = (sire_scores["hips"] + dam_scores["hips"]) / 2

        dataset.append({
            "sire_hips":    sire_scores.get("hips"),
            "sire_eyes":    sire_scores.get("eyes"),
            "sire_elbows":  sire_scores.get("elbows"),
            "sire_dm":      sire_scores.get("dm"),
            "sire_pra":     sire_scores.get("pra"),
            "sire_coi":     float(sire_coi) if sire_coi else None,
            "dam_hips":     dam_scores.get("hips"),
            "dam_eyes":     dam_scores.get("eyes"),
            "dam_elbows":   dam_scores.get("elbows"),
            "dam_dm":       dam_scores.get("dm"),
            "dam_pra":      dam_scores.get("pra"),
            "dam_coi":      float(dam_coi) if dam_coi else None,
            "pair_coi":     float(pair_coi) if pair_coi else None,
            "hip_ratio_4gen": None,
            "avg_hip_score":  avg_hip,
            "offspring_has_hip_problem":   int(offspring_scores["hips"] >= HIP_PROBLEM_THRESHOLD),
            "offspring_has_eye_problem":   int(offspring_scores.get("eyes", 0) >= EYE_PROBLEM_THRESHOLD),
            "offspring_has_elbow_problem": int(offspring_scores.get("elbows", 0) >= ELBOW_PROBLEM_THRESHOLD),
            "_synthetic":    False,
            "_offspring_id": dog_id,
            "_sire_id":      sire_id,
            "_dam_id":       dam_id,
        })

    return dataset, skipped


def build_dataset(augment: bool = False, n_synthetic: int = 3000) -> list[dict]:
    """
    Собирает датасет для обучения ML.

    Параметры:
      augment     — добавить синтетические данные
      n_synthetic — сколько синтетических записей добавить

    Синтетические данные НЕ сохраняются в БД.
    Они существуют только в памяти во время обучения.
    """
    logger.info("Сборка датасета...")

    from ..models import Dog
    offspring_count = Dog.objects.using("dogs_db").filter(
        sire_id__isnull=False, dam_id__isnull=False
    ).count()
    logger.info(f"Потомков с известными родителями: {offspring_count}")

    real_data, skipped = _build_real_dataset()
    logger.info(f"OFA записей для реальных собак: {len(real_data)}")

    if not real_data:
        logger.warning("Нет реальных данных")
        return []

    hip_pos   = sum(d["offspring_has_hip_problem"]   for d in real_data)
    eye_pos   = sum(d["offspring_has_eye_problem"]   for d in real_data)
    elbow_pos = sum(d["offspring_has_elbow_problem"] for d in real_data)
    total     = len(real_data)

    logger.info(
        f"Реальный датасет: {total} записей, пропущено: {skipped}\n"
        f"  бёдра (FAIR+): {hip_pos} ({hip_pos/total:.1%})\n"
        f"  глаза: {eye_pos} ({eye_pos/total:.1%})\n"
        f"  локти: {elbow_pos} ({elbow_pos/total:.1%})"
    )

    if not augment:
        return real_data

    # Добавляем синтетические данные
    from .synthetic_generator import generate_synthetic_dataset
    synthetic = generate_synthetic_dataset(n_samples=n_synthetic)

    combined = real_data + synthetic
    total_c  = len(combined)
    hip_c    = sum(d["offspring_has_hip_problem"]   for d in combined)
    eye_c    = sum(d["offspring_has_eye_problem"]   for d in combined)
    elbow_c  = sum(d["offspring_has_elbow_problem"] for d in combined)

    logger.info(
        f"Итоговый датасет (реальные + синтетика): {total_c} записей\n"
        f"  бёдра (FAIR+): {hip_c} ({hip_c/total_c:.1%})\n"
        f"  глаза: {eye_c} ({eye_c/total_c:.1%})\n"
        f"  локти: {elbow_c} ({elbow_c/total_c:.1%})"
    )

    return combined


def save_dataset_csv(path: str = "/tmp/ofa_dataset.csv", augment: bool = False) -> str:
    """Сохраняет датасет в CSV для анализа."""
    import csv
    dataset = build_dataset(augment=augment)
    if not dataset:
        return ""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
        writer.writeheader()
        writer.writerows(dataset)
    logger.info(f"Сохранено: {path} ({len(dataset)} строк)")
    return path