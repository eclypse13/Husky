# dogs_module/utils/coi_calculator.py
"""
Расчёт коэффициента инбридинга (COI) по методу Райта.

═══════════════════════════════════════════════════════════════════════════════
ФОРМУЛА РАЙТА:
═══════════════════════════════════════════════════════════════════════════════

  F(I) = Σ_A  Σ_путей  (0.5)^(n1 + n2 + 1) × (1 + F_A)

  Где:
    A   — общий предок отца и матери
    n1  — шагов от отца до A
    n2  — шагов от матери до A
    F_A — COI самого предка A (по умолчанию 0)

  Пример: предок через отца (2 шага) и через мать (3 шага):
    вклад = (0.5)^(2+3+1) = (0.5)^6 ≈ 1.5625%

═══════════════════════════════════════════════════════════════════════════════
ОПТИМИЗАЦИИ:
═══════════════════════════════════════════════════════════════════════════════

  1. БАТЧ-ЗАПРОСЫ — каждое поколение загружается одним SQL:
       Dog.objects.filter(id__in=[...]).values('id', 'sire_id', 'dam_id')
     Итого: max_depth+1 запросов вместо 2^depth.

  2. ДЕДУПЛИКАЦИЯ — предок в нескольких ветках хранится как
     {id: [depth1, depth2, ...]}, не перезагружается.

  3. ГЛУБИНА 1–10 — стандарт FCI = 5 поколений. Глубже 10 вклад < 0.001%.

  4. use_ancestor_coi — учёт F_A. Даёт +0.1–2% точности при сильном
     инбридинге. Берёт сохранённые Dog.coi из БД, не рекурсивен.

═══════════════════════════════════════════════════════════════════════════════
ПУБЛИЧНОЕ API:
═══════════════════════════════════════════════════════════════════════════════

  calculate_coi(dog, generations, use_ancestor_coi) → CoiResult
  save_coi(dog, result)                              → Dog
  recalculate_all_coi(...)                           → dict (статистика)
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# РЕЗУЛЬТАТ
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CoiResult:
    """
    Результат расчёта COI с диагностикой.

      coi                    — COI в процентах (например 6.25)
      generations            — сколько поколений использовано
      common_ancestors       — найдено общих предков
      total_ancestors_sire   — уникальных предков по отцу
      total_ancestors_dam    — уникальных предков по матери
      ancestor_contributions — {ancestor_id: вклад_%} для дебага
      error                  — текст ошибки если расчёт невозможен
    """
    coi:                    float
    generations:            int
    common_ancestors:       int
    total_ancestors_sire:   int
    total_ancestors_dam:    int
    ancestor_contributions: Dict[int, float] = field(default_factory=dict)
    error:                  Optional[str]    = None

    @property
    def is_valid(self) -> bool:
        return self.error is None

    def __str__(self) -> str:
        if not self.is_valid:
            return f"COI: ошибка ({self.error})"
        return (
            f"COI={self.coi:.4f}% | "
            f"{self.generations} поколений | "
            f"{self.common_ancestors} общих предков"
        )


# ══════════════════════════════════════════════════════════════════════════════
# ОСНОВНОЙ РАСЧЁТ
# ══════════════════════════════════════════════════════════════════════════════

def calculate_coi(
    dog,
    generations: int = 5,
    use_ancestor_coi: bool = False,
) -> CoiResult:
    """
    Рассчитывает COI для одной собаки по формуле Райта.

    Только читает БД — не сохраняет. Для сохранения вызвать save_coi().

    ПАРАМЕТРЫ:
      dog              — объект Dog (нужны .id, .sire_id, .dam_id)
      generations      — глубина поиска предков (1–10, стандарт = 5)
      use_ancestor_coi — учитывать COI самих предков (1 + F_A) в формуле
    """
    generations = max(1, min(generations, 10))

    # ── Граничные случаи ──────────────────────────────────────────────────────
    if not dog.sire_id or not dog.dam_id:
        return CoiResult(
            coi=0.0,
            generations=generations,
            common_ancestors=0,
            total_ancestors_sire=0,
            total_ancestors_dam=0,
            error="Нет данных об одном или обоих родителях",
        )

    if dog.sire_id == dog.dam_id:
        return CoiResult(
            coi=50.0,
            generations=generations,
            common_ancestors=1,
            total_ancestors_sire=0,
            total_ancestors_dam=0,
        )

    # ── Сбор путей ────────────────────────────────────────────────────────────
    # {ancestor_id: [depth1, depth2, ...]}  — все глубины на которых встречается предок
    paths_sire = _collect_ancestor_paths(dog.sire_id, generations)
    paths_dam  = _collect_ancestor_paths(dog.dam_id,  generations)

    # ── Общие предки ─────────────────────────────────────────────────────────
    common_ids: Set[int] = set(paths_sire.keys()) & set(paths_dam.keys())

    if not common_ids:
        return CoiResult(
            coi=0.0,
            generations=generations,
            common_ancestors=0,
            total_ancestors_sire=len(paths_sire),
            total_ancestors_dam=len(paths_dam),
        )

    # ── COI предков (опционально) ─────────────────────────────────────────────
    ancestor_fa: Dict[int, float] = {}
    if use_ancestor_coi:
        ancestor_fa = _fetch_ancestor_coi(common_ids)

    # ── Формула Райта ─────────────────────────────────────────────────────────
    total_coi     = 0.0
    contributions: Dict[int, float] = {}

    for ancestor_id in common_ids:
        fa              = ancestor_fa.get(ancestor_id, 0.0) / 100.0  # % → доли
        ancestor_contrib = 0.0

        for n1 in paths_sire[ancestor_id]:
            for n2 in paths_dam[ancestor_id]:
                ancestor_contrib += (0.5 ** (n1 + n2 + 1)) * (1.0 + fa)

        contributions[ancestor_id] = round(ancestor_contrib * 100, 6)
        total_coi += ancestor_contrib

    return CoiResult(
        coi=round(total_coi * 100, 4),
        generations=generations,
        common_ancestors=len(common_ids),
        total_ancestors_sire=len(paths_sire),
        total_ancestors_dam=len(paths_dam),
        ancestor_contributions=contributions,
    )


# ══════════════════════════════════════════════════════════════════════════════
# BFS + БАТЧ-ЗАГРУЗКА ПРЕДКОВ
# ══════════════════════════════════════════════════════════════════════════════

def _collect_ancestor_paths(
    root_id: int,
    max_depth: int,
) -> Dict[int, List[int]]:
    """
    BFS по дереву предков. Каждое поколение — один SQL-запрос.

    Возвращает {ancestor_id: [depth1, depth2, ...]} — все глубины
    на которых встречается каждый предок (один предок может быть
    в нескольких ветках при инбридинге).

    Итого SQL: max_depth запросов.
    """
    paths: Dict[int, List[int]] = defaultdict(list)

    # {dog_id: [depths]} — фронт BFS: собаки чьих родителей ищем на след. шаге
    current_front: Dict[int, List[int]] = {root_id: [0]}

    for _depth in range(1, max_depth + 1):
        if not current_front:
            break

        parent_rows = _fetch_parents_batch(set(current_front.keys()))
        next_front: Dict[int, List[int]] = defaultdict(list)

        for dog_id, (sire_id, dam_id) in parent_rows.items():
            for parent_id in filter(None, (sire_id, dam_id)):
                for d in current_front[dog_id]:
                    new_depth = d + 1
                    paths[parent_id].append(new_depth)
                    next_front[parent_id].append(new_depth)

        current_front = dict(next_front)

    return dict(paths)


def _fetch_parents_batch(
    dog_ids: Set[int],
) -> Dict[int, Tuple[Optional[int], Optional[int]]]:
    """Загружает (sire_id, dam_id) для набора ids одним SQL-запросом."""
    from ..models import Dog

    rows = (
        Dog.objects
        .using('dogs_db')
        .filter(id__in=dog_ids)
        .values('id', 'sire_id', 'dam_id')
    )
    return {row['id']: (row['sire_id'], row['dam_id']) for row in rows}


def _fetch_ancestor_coi(ancestor_ids: Set[int]) -> Dict[int, float]:
    """
    Читает уже сохранённые Dog.coi для предков.
    Используется только при use_ancestor_coi=True.
    """
    from ..models import Dog

    rows = (
        Dog.objects
        .using('dogs_db')
        .filter(id__in=ancestor_ids, coi__isnull=False)
        .values('id', 'coi')
    )
    return {row['id']: row['coi'] for row in rows}


# ══════════════════════════════════════════════════════════════════════════════
# СОХРАНЕНИЕ
# ══════════════════════════════════════════════════════════════════════════════

def save_coi(dog, result: CoiResult):
    """
    Сохраняет COI в Dog. Обновляет ТОЛЬКО coi + coi_updated_on.

    Если result.is_valid == False → сохраняет coi=None
    (означает: расчёт пытался выполниться, но данных недостаточно).
    """
    from django.utils import timezone

    dog.coi            = result.coi if result.is_valid else None
    dog.coi_updated_on = timezone.now()
    dog.save(using='dogs_db', update_fields=['coi', 'coi_updated_on'])

    label = f"{result.coi:.4f}%" if result.is_valid else "null"
    logger.info(f"💾 COI: {dog.registered_name} (id={dog.id}) → {label}")
    return dog


# ══════════════════════════════════════════════════════════════════════════════
# МАССОВЫЙ ПЕРЕСЧЁТ (вызывается из Celery)
# ══════════════════════════════════════════════════════════════════════════════

def recalculate_all_coi(
    generations: int = 5,
    batch_size: int = 100,
    only_missing: bool = True,
    use_ancestor_coi: bool = False,
) -> Dict:
    """
    Массовый пересчёт COI. Вызывается из tasks_coi.py.

    ПАРАМЕТРЫ:
      generations      — глубина расчёта
      batch_size       — размер батча для загрузки в память
      only_missing     — True = только Dog.coi IS NULL
                         False = пересчитать всех (полный refresh)
      use_ancestor_coi — учитывать F_A предков

    ВОЗВРАЩАЕТ:
      {total, updated, skipped, errors, duration_sec}
    """
    from ..models import Dog

    start = time.time()

    qs = (
        Dog.objects
        .using('dogs_db')
        .filter(sire_id__isnull=False, dam_id__isnull=False)
        .only('id', 'registered_name', 'sire_id', 'dam_id', 'coi')
    )
    if only_missing:
        qs = qs.filter(coi__isnull=True)

    total   = qs.count()
    updated = skipped = errors = 0

    logger.info(
        f"🔄 Массовый пересчёт COI: {total} собак | "
        f"gen={generations} | only_missing={only_missing}"
    )

    offset = 0
    while offset < total:
        batch  = list(qs[offset: offset + batch_size])
        offset += batch_size

        for dog in batch:
            try:
                result = calculate_coi(
                    dog,
                    generations=generations,
                    use_ancestor_coi=use_ancestor_coi,
                )
                if not result.is_valid:
                    skipped += 1
                    continue

                save_coi(dog, result)
                updated += 1

            except Exception as exc:
                errors += 1
                logger.error(f"❌ COI ошибка dog.id={dog.id}: {exc}")

        logger.info(f"  ⏳ {min(offset, total)}/{total} обработано")

    duration = round(time.time() - start, 2)
    logger.info(
        f"✅ Готово: обновлено={updated}, пропущено={skipped}, "
        f"ошибок={errors}, время={duration}с"
    )

    return {
        'total':        total,
        'updated':      updated,
        'skipped':      skipped,
        'errors':       errors,
        'duration_sec': duration,
    }