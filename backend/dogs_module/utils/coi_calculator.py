# dogs_module/utils/coi_calculator.py
"""
Расчёт коэффициента инбридинга (COI) по методу Райта.

ФОРМУЛА РАЙТА:
  F(I) = Σ_A Σ_путей (0.5)^(n1 + n2 + 1) × (1 + F_A)
  Где:
    A   — общий предок отца и матери
    n1  — шагов от отца до A
    n2  — шагов от матери до A
    F_A — COI самого предка A (по умолчанию 0)

ПУБЛИЧНОЕ API:
  calculate_coi(dog, generations, use_ancestor_coi, check_completeness) → CoiResult
  save_coi(dog, result) → Dog
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CoiResult:
    """
    Результат расчёта COI.
      coi                    — COI в процентах (например 6.25)
      generations            — сколько поколений использовано
      common_ancestors       — найдено общих предков
      total_ancestors_sire   — уникальных предков по отцу
      total_ancestors_dam    — уникальных предков по матери
      ancestor_contributions — {ancestor_id: вклад_%}
      error                  — текст ошибки если расчёт невозможен
    """
    coi: float
    generations: int
    common_ancestors: int
    total_ancestors_sire: int
    total_ancestors_dam: int
    ancestor_contributions: Dict[int, float] = field(default_factory=dict)
    error: Optional[str] = None

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


# ── ОСНОВНОЙ РАСЧЁТ ───────────────────────────────────────────────────────────

def calculate_coi(
    dog,
    generations: int = 10,
    use_ancestor_coi: bool = False,
    check_completeness: bool = False,
) -> CoiResult:
    """
    Рассчитывает COI для одной собаки по формуле Райта.

    ПАРАМЕТРЫ:
      dog              — объект Dog (нужны .sire_id, .dam_id)
      generations      — глубина поиска предков (1–10, стандарт FCI = 5)
      use_ancestor_coi — учитывать COI самих предков (1 + F_A)
      check_completeness — параметр оставлен для совместимости, не используется
    """
    generations = max(1, min(generations, 10))

    # Граничные случаи
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

    # Собираем пути предков за generations-1 уровней
    depth = generations - 1
    paths_sire = _collect_ancestor_paths(dog.sire_id, depth)
    paths_dam  = _collect_ancestor_paths(dog.dam_id,  depth)

    # Общие предки — если нет, COI = 0
    common_ids: Set[int] = set(paths_sire.keys()) & set(paths_dam.keys())

    if not common_ids:
        return CoiResult(
            coi=0.0,
            generations=generations,
            common_ancestors=0,
            total_ancestors_sire=len(paths_sire),
            total_ancestors_dam=len(paths_dam),
        )

    # COI предков (опционально)
    ancestor_fa: Dict[int, float] = {}
    if use_ancestor_coi:
        ancestor_fa = _fetch_ancestor_coi(common_ids)

    # Формула Райта
    total_coi = 0.0
    contributions: Dict[int, float] = {}

    for ancestor_id in common_ids:
        fa = ancestor_fa.get(ancestor_id, 0.0) / 100.0
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


# ── BFS + БАТЧ-ЗАГРУЗКА ──────────────────────────────────────────────────────

def _collect_ancestor_paths(
    root_id: int,
    max_depth: int,
) -> Dict[int, List[int]]:
    """
    BFS по дереву предков. Один SQL на поколение.
    Возвращает {ancestor_id: [depth1, depth2, ...]}
    """
    paths: Dict[int, List[int]] = defaultdict(list)
    paths[root_id].append(0)
    current_front: Dict[int, List[int]] = {root_id: [0]}

    for _depth in range(1, max_depth + 1):
        if not current_front:
            break

        parent_rows = _fetch_parents_batch(set(current_front.keys()))
        next_front: Dict[int, List[int]] = defaultdict(list)

        for dog_id, (sire_id, dam_id) in parent_rows.items():
            for parent_id in filter(None, (sire_id, dam_id)):
                for d in current_front.get(dog_id, []):
                    new_depth = d + 1
                    paths[parent_id].append(new_depth)
                    next_front[parent_id].append(new_depth)

        current_front = dict(next_front)

    return dict(paths)


def _fetch_parents_batch(
    dog_ids: Set[int],
) -> Dict[int, Tuple[Optional[int], Optional[int]]]:
    """Загружает (sire_id, dam_id) для набора ids одним SQL."""
    from ..models import Dog
    rows = (
        Dog.objects.using('dogs_db')
        .filter(id__in=dog_ids)
        .values('id', 'sire_id', 'dam_id')
    )
    return {row['id']: (row['sire_id'], row['dam_id']) for row in rows}


def _fetch_ancestor_coi(ancestor_ids: Set[int]) -> Dict[int, float]:
    """Читает сохранённые Dog.coi для предков."""
    from ..models import Dog
    rows = (
        Dog.objects.using('dogs_db')
        .filter(id__in=ancestor_ids, coi__isnull=False)
        .values('id', 'coi')
    )
    return {row['id']: row['coi'] for row in rows}


# ── СОХРАНЕНИЕ ────────────────────────────────────────────────────────────────

def save_coi(dog, result: CoiResult):
    """Сохраняет COI в Dog. Обновляет только coi + coi_updated_on."""
    from django.utils import timezone

    dog.coi = result.coi if result.is_valid else None
    dog.coi_updated_on = timezone.now()
    dog.save(using='dogs_db', update_fields=['coi', 'coi_updated_on'])

    label = f"{result.coi:.4f}%" if result.is_valid else "null"
    logger.info(f"💾 COI: {dog.registered_name} (id={dog.id}) → {label}")
    return dog


# ── МАССОВЫЙ ПЕРЕСЧЁТ ─────────────────────────────────────────────────────────

def recalculate_all_coi(
    generations: int = 10,
    batch_size: int = 100,
    only_missing: bool = True,
    use_ancestor_coi: bool = False,
) -> Dict:
    """Массовый пересчёт COI. Вызывается из tasks_coi.py."""
    from ..models import Dog

    start = time.time()

    qs = (
        Dog.objects.using('dogs_db')
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
                # check_completeness=True — сохраняем только надёжные значения
                result = calculate_coi(
                    dog,
                    generations=generations,
                    use_ancestor_coi=use_ancestor_coi,
                    check_completeness=True,
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
        'total': total, 'updated': updated,
        'skipped': skipped, 'errors': errors,
        'duration_sec': duration,
    }