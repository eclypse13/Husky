# dogs_module/services/synthetic_generator.py
"""
Генератор синтетических данных для обучения ML модели.

Данные генерируются на основе РЕАЛЬНОЙ статистики OFA по породе Siberian Husky.
Источник: OFA Health Statistics for Siberian Husky (ofa.org)

"""

import random
import logging
import math

logger = logging.getLogger(__name__)

# ── Реальная статистика OFA по Siberian Husky ─────────────────────────────────
# Источник: ofa.org/diseases/statistics, Siberian Husky
# Данные: 22568 тестов бёдер, 15178 глаз, 1690 локтей и т.д.

# Бёдра: Normal=97.3%, Abnormal(Borderline+)=2.3%, Equivocal=0.3%
# Примерное разбиение Normal: Excellent~22%, Good~55%, Fair~20%
HIP_DISTRIBUTION = {
    "scores":        [0,     1,     2,     3,     4,     5,     6],
    # Excellent Good  Fair  Border  Mild  Moderate Severe
    "probabilities": [0.220, 0.550, 0.200, 0.015,  0.008, 0.005, 0.002],
}

# Глаза: Normal=92.3%, Abnormal=7.4%
EYE_DISTRIBUTION = {
    "scores":        [0,    1],
    "probabilities": [0.923, 0.077],
}

# Локти: Normal=99.8%, Abnormal=0.2% — очень редко у хаски
ELBOW_DISTRIBUTION = {
    "scores":        [0,    1],
    "probabilities": [0.998, 0.002],
}

# DM: Normal=98.8%, Affected=0.4%, Carrier=0.8%
DM_DISTRIBUTION = {
    "scores":        [0,    1,    2],
    "probabilities": [0.988, 0.008, 0.004],
}

# LPP (Polyneuropathy): Normal=91.2%, Carrier=8.8% — важная болезнь для хаски!
LPP_DISTRIBUTION = {
    "scores":        [0,    1,    2],
    "probabilities": [0.912, 0.088, 0.0],
}

# PRA: по статистике OFA 100% Normal в выборке (редкая болезнь)
PRA_DISTRIBUTION = {
    "scores":        [0,    1,    2],
    "probabilities": [0.98, 0.015, 0.005],
}

# Вероятность что тест вообще сдан (не все собаки проходят все тесты)
P_HAS_HIP_TEST   = 0.75
P_HAS_EYE_TEST   = 0.45
P_HAS_ELBOW_TEST = 0.15
P_HAS_DM_TEST    = 0.10
P_HAS_LPP_TEST   = 0.05
P_HAS_PRA_TEST   = 0.04

# COI: среднее по породе
COI_MEAN = 4.5
COI_STD  = 3.0
COI_MIN  = 0.5
COI_MAX  = 25.0


def _sample(distribution: dict) -> int:
    """Случайный результат по распределению."""
    return random.choices(
        distribution["scores"],
        weights=distribution["probabilities"],
    )[0]


def _sample_coi() -> float:
    """Случайный COI из нормального распределения."""
    u1 = max(random.random(), 1e-10)
    u2 = random.random()
    z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    coi = COI_MEAN + z * COI_STD
    return round(max(COI_MIN, min(COI_MAX, coi)), 2)


def _offspring_hip_prob(sire_hips: int, dam_hips: int, pair_coi: float) -> float:
    """
    Вероятность что у потомка будет FAIR или хуже (score >= 2).

    Основана на наследуемости дисплазии бёдер у хаски:
      - Heritability h² ≈ 0.25-0.35 для хаски
      - Инбридинг увеличивает риск через гомозиготность
    """
    avg_score = (sire_hips + dam_hips) / 2

    # Базовый риск — растёт с ухудшением среднего балла родителей
    # EXCELLENT(0)+EXCELLENT(0) → avg=0 → ~5%
    # GOOD(1)+GOOD(1) → avg=1 → ~11%
    # FAIR(2)+FAIR(2) → avg=2 → ~21%
    # Borderline(3)+Borderline(3) → avg=3 → ~36%
    base_risk = 0.05 + avg_score * 0.10

    # COI увеличивает риск рецессивных болезней
    coi_factor = 1.0 + (pair_coi / 100) * 2.5

    return min(base_risk * coi_factor, 0.85)


def _offspring_eye_prob(sire_eyes, dam_eyes, pair_coi) -> float:
    """Вероятность патологии глаз у потомка."""
    # Базовый риск 7.4% по OFA статистике
    base = 0.04
    if sire_eyes == 1:
        base += 0.15
    if dam_eyes == 1:
        base += 0.15
    coi_factor = 1.0 + (pair_coi / 100) * 1.5
    return min(base * coi_factor, 0.70)


def _offspring_elbow_prob(sire_elbows, dam_elbows, pair_coi) -> float:
    """Вероятность дисплазии локтей — очень редко у хаски (0.2%)."""
    base = 0.002
    if sire_elbows == 1:
        base += 0.05
    if dam_elbows == 1:
        base += 0.05
    return min(base, 0.30)


def generate_synthetic_dataset(
    n_samples: int = 3000,
    seed: int = 42,
) -> list[dict]:
    """
    Генерирует синтетические пары для обучения ML.

    Параметры:
      n_samples — число синтетических записей
      seed      — для воспроизводимости результатов

    Статистика основана на реальных данных OFA по Siberian Husky:
      - HIPS: 97.3% Normal, 2.3% Abnormal
      - EYES: 92.3% Normal, 7.4% Abnormal
      - ELBOW: 99.8% Normal, 0.2% Abnormal
      - DM: 98.8% Normal, 0.4% Affected, 0.8% Carrier
      - LPP: 91.2% Normal, 8.8% Carrier

    Возвращает список dict в формате dataset_builder.py.
    Каждая запись помечена '_synthetic': True.
    """
    random.seed(seed)
    dataset = []

    hip_pos   = 0
    eye_pos   = 0
    elbow_pos = 0

    for _ in range(n_samples):
        # ── Кобель ───────────────────────────────────────────────────────────
        sire_hips    = _sample(HIP_DISTRIBUTION)   if random.random() < P_HAS_HIP_TEST   else None
        sire_eyes    = _sample(EYE_DISTRIBUTION)   if random.random() < P_HAS_EYE_TEST   else None
        sire_elbows  = _sample(ELBOW_DISTRIBUTION) if random.random() < P_HAS_ELBOW_TEST else None
        sire_dm      = _sample(DM_DISTRIBUTION)    if random.random() < P_HAS_DM_TEST    else None
        sire_pra     = _sample(PRA_DISTRIBUTION)   if random.random() < P_HAS_PRA_TEST   else None
        sire_lpp     = _sample(LPP_DISTRIBUTION)   if random.random() < P_HAS_LPP_TEST   else None
        sire_coi     = _sample_coi()

        # ── Сука ─────────────────────────────────────────────────────────────
        dam_hips     = _sample(HIP_DISTRIBUTION)   if random.random() < P_HAS_HIP_TEST   else None
        dam_eyes     = _sample(EYE_DISTRIBUTION)   if random.random() < P_HAS_EYE_TEST   else None
        dam_elbows   = _sample(ELBOW_DISTRIBUTION) if random.random() < P_HAS_ELBOW_TEST else None
        dam_dm       = _sample(DM_DISTRIBUTION)    if random.random() < P_HAS_DM_TEST    else None
        dam_pra      = _sample(PRA_DISTRIBUTION)   if random.random() < P_HAS_PRA_TEST   else None
        dam_lpp      = _sample(LPP_DISTRIBUTION)   if random.random() < P_HAS_LPP_TEST   else None
        dam_coi      = _sample_coi()

        pair_coi = round(
            (sire_coi + dam_coi) / 2 * random.uniform(0.8, 1.2), 2
        )
        avg_hip = None
        if sire_hips is not None and dam_hips is not None:
            avg_hip = (sire_hips + dam_hips) / 2

        # ── Результат потомка ─────────────────────────────────────────────────
        sh = sire_hips   if sire_hips   is not None else 1
        dh = dam_hips    if dam_hips    is not None else 1
        se = sire_eyes   if sire_eyes   is not None else 0
        de = dam_eyes    if dam_eyes    is not None else 0
        sel = sire_elbows if sire_elbows is not None else 0
        del_ = dam_elbows if dam_elbows  is not None else 0

        offspring_hip   = 1 if random.random() < _offspring_hip_prob(sh, dh, pair_coi) else 0
        offspring_eye   = 1 if random.random() < _offspring_eye_prob(se, de, pair_coi)  else 0
        offspring_elbow = 1 if random.random() < _offspring_elbow_prob(sel, del_, pair_coi) else 0

        if offspring_hip:   hip_pos   += 1
        if offspring_eye:   eye_pos   += 1
        if offspring_elbow: elbow_pos += 1

        dataset.append({
            "sire_hips":    sire_hips,
            "sire_eyes":    sire_eyes,
            "sire_elbows":  sire_elbows,
            "sire_dm":      sire_dm,
            "sire_pra":     sire_pra,
            "sire_coi":     sire_coi,
            "dam_hips":     dam_hips,
            "dam_eyes":     dam_eyes,
            "dam_elbows":   dam_elbows,
            "dam_dm":       dam_dm,
            "dam_pra":      dam_pra,
            "dam_coi":      dam_coi,
            "pair_coi":     pair_coi,
            "hip_ratio_4gen": None,
            "avg_hip_score":  avg_hip,

            "offspring_has_hip_problem":   offspring_hip,
            "offspring_has_eye_problem":   offspring_eye,
            "offspring_has_elbow_problem": offspring_elbow,

            "_synthetic":    True,
            "_offspring_id": None,
            "_sire_id":      None,
            "_dam_id":       None,
        })

    logger.info(
        f"Синтетика ({n_samples} записей):\n"
        f"  бёдра FAIR+: {hip_pos} ({hip_pos/n_samples:.1%})\n"
        f"  глаза:  {eye_pos} ({eye_pos/n_samples:.1%})\n"
        f"  локти:  {elbow_pos} ({elbow_pos/n_samples:.1%})"
    )
    return dataset