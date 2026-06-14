# dogs_module/services/synthetic_generator.py
"""
Генератор синтетических данных для обучения ML модели.

Данные генерируются на основе реальной статистики OFA по породе Siberian Husky.

ВАЖНО:
  • Синтетика существует только в памяти и не сохраняется в БД.
  • Метка «дисплазия» = Borderline+ (порог 3, как HIP_PROBLEM_THRESHOLD),
    т.е. редкое событие (~3% протестированных у хаски). Вероятности ниже
    подобраны под этот порог и являются ПРИБЛИЖЕНИЕМ — их нужно перекалибровать,
    когда накопится достаточно реальных данных.
  • У синтетических собак нет родословной → агрегаты по предкам пустые
    (tested_ratio=0, остальное None) — совпадает с реальными собаками без предков.
"""

import random
import logging
import math

from .ancestor_features import empty_side_features

logger = logging.getLogger(__name__)

# Распределения по реальной статистике OFA (Siberian Husky)

# Бёдра: Excellent~22%, Good~55%, Fair~20%, Borderline+ ~3.0%
HIP_DISTRIBUTION = {
    "scores": [0, 1, 2, 3, 4, 5, 6],
    "probabilities": [0.220, 0.550, 0.200, 0.015, 0.008, 0.005, 0.002],
}

# Глаза: Normal=92.3%, Abnormal=7.7%
EYE_DISTRIBUTION = {
    "scores": [0, 1],
    "probabilities": [0.923, 0.077],
}

# Локти: Normal=99.8% — очень редко у хаски (как фича, не как таргет)
ELBOW_DISTRIBUTION = {
    "scores": [0, 1],
    "probabilities": [0.998, 0.002],
}

# DM: Normal/Affected/Carrier
DM_DISTRIBUTION = {
    "scores": [0, 1, 2],
    "probabilities": [0.988, 0.008, 0.004],
}

# PRA: редкая болезнь
PRA_DISTRIBUTION = {
    "scores": [0, 1, 2],
    "probabilities": [0.98, 0.015, 0.005],
}

# Вероятность что тест вообще сдан
P_HAS_HIP_TEST = 0.75
P_HAS_EYE_TEST = 0.45
P_HAS_ELBOW_TEST = 0.15
P_HAS_DM_TEST = 0.10
P_HAS_PRA_TEST = 0.04

# COI по породе, ПРОЦЕНТЫ
COI_MEAN = 4.5
COI_STD = 3.0
COI_MIN = 0.5
COI_MAX = 25.0


def _sample(distribution: dict) -> int:
    """Случайный результат по распределению."""
    return random.choices(
        distribution["scores"],
        weights=distribution["probabilities"],
    )[0]


def _sample_coi() -> float:
    """Случайный COI (%) из усечённого нормального распределения."""
    u1 = max(random.random(), 1e-10)
    u2 = random.random()
    z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    coi = COI_MEAN + z * COI_STD
    return round(max(COI_MIN, min(COI_MAX, coi)), 2)


def _offspring_hip_prob(sire_hips: int, dam_hips: int, pair_coi: float) -> float:
    """
    Вероятность ДИСПЛАЗИИ (Borderline+) у потомка.
    Перекалибровано под редкое событие: базовый риск низкий, растёт с баллами
    родителей и инбридингом. pair_coi — проценты.
    """
    avg_score = (sire_hips + dam_hips) / 2
    base_risk = 0.015 + avg_score * 0.030
    coi_factor = 1.0 + (pair_coi / 100) * 2.5
    return min(base_risk * coi_factor, 0.60)


def _offspring_eye_prob(sire_eyes, dam_eyes, pair_coi) -> float:
    """Вероятность патологии глаз у потомка. pair_coi — проценты."""
    base = 0.04
    if sire_eyes == 1:
        base += 0.15
    if dam_eyes == 1:
        base += 0.15
    coi_factor = 1.0 + (pair_coi / 100) * 1.5
    return min(base * coi_factor, 0.70)


def generate_synthetic_dataset(n_samples: int = 3000, seed: int = 42) -> list[dict]:
    """
    Генерирует синтетические пары для обучения ML.
    Каждая запись помечена '_synthetic': True. Формат совпадает с dataset_builder
    (включая агрегаты по предкам — пустые, т.к. родословной нет).
    """
    random.seed(seed)
    dataset = []

    hip_pos = eye_pos = 0

    for _ in range(n_samples):
        # Кобель
        sire_hips = _sample(HIP_DISTRIBUTION) if random.random() < P_HAS_HIP_TEST else None
        sire_eyes = _sample(EYE_DISTRIBUTION) if random.random() < P_HAS_EYE_TEST else None
        sire_elbows = _sample(ELBOW_DISTRIBUTION) if random.random() < P_HAS_ELBOW_TEST else None
        sire_dm = _sample(DM_DISTRIBUTION) if random.random() < P_HAS_DM_TEST else None
        sire_pra = _sample(PRA_DISTRIBUTION) if random.random() < P_HAS_PRA_TEST else None
        sire_coi = _sample_coi()

        # Сука
        dam_hips = _sample(HIP_DISTRIBUTION) if random.random() < P_HAS_HIP_TEST else None
        dam_eyes = _sample(EYE_DISTRIBUTION) if random.random() < P_HAS_EYE_TEST else None
        dam_elbows = _sample(ELBOW_DISTRIBUTION) if random.random() < P_HAS_ELBOW_TEST else None
        dam_dm = _sample(DM_DISTRIBUTION) if random.random() < P_HAS_DM_TEST else None
        dam_pra = _sample(PRA_DISTRIBUTION) if random.random() < P_HAS_PRA_TEST else None
        dam_coi = _sample_coi()

        pair_coi = round((sire_coi + dam_coi) / 2 * random.uniform(0.8, 1.2), 2)
        avg_hip = None
        if sire_hips is not None and dam_hips is not None:
            avg_hip = (sire_hips + dam_hips) / 2

        # ── Результат потомка (None → дефолт для расчёта вероятности) ─────────
        sh = sire_hips if sire_hips is not None else 1
        dh = dam_hips if dam_hips is not None else 1
        se = sire_eyes if sire_eyes is not None else 0
        de = dam_eyes if dam_eyes is not None else 0

        offspring_hip = 1 if random.random() < _offspring_hip_prob(sh, dh, pair_coi) else 0
        offspring_eye = 1 if random.random() < _offspring_eye_prob(se, de, pair_coi) else 0

        hip_pos += offspring_hip
        eye_pos += offspring_eye

        row = {
            "sire_hips": sire_hips,
            "sire_eyes": sire_eyes,
            "sire_elbows": sire_elbows,
            "sire_dm": sire_dm,
            "sire_pra": sire_pra,
            "sire_coi": sire_coi,
            "dam_hips": dam_hips,
            "dam_eyes": dam_eyes,
            "dam_elbows": dam_elbows,
            "dam_dm": dam_dm,
            "dam_pra": dam_pra,
            "dam_coi": dam_coi,
            "pair_coi": pair_coi,
            "avg_hip_score": avg_hip,
            "offspring_has_hip_problem": offspring_hip,
            "offspring_has_eye_problem": offspring_eye,
            "_synthetic": True,
            "_offspring_id": None,
            "_sire_id": None,
            "_dam_id": None,
        }
        # Агрегаты по предкам — пустые (родословной у синтетики нет).
        row.update(empty_side_features("sire"))
        row.update(empty_side_features("dam"))
        dataset.append(row)

    logger.info(
        f"Синтетика ({n_samples} записей):\n"
        f"  бёдра Borderline+: {hip_pos} ({hip_pos / n_samples:.1%})\n"
        f"  глаза: {eye_pos} ({eye_pos / n_samples:.1%})"
    )
    return dataset
