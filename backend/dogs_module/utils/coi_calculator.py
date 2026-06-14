# dogs_module/utils/coi_calculator.py
"""
Расчёт коэффициента инбридинга (COI) по методу Райта.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from ..repositories import dog_repository as dog_repo

logger = logging.getLogger(__name__)


@dataclass
class CoiResult:
    """Результат расчёта COI (coi в процентах; error — если расчёт невозможен)."""
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
            f"COI={self.coi:.4f}% | {self.generations} поколений | "
            f"{self.common_ancestors} общих предков"
        )


# ОСНОВНОЙ РАСЧЁТ
def calculate_coi(
        dog,
        generations: int = 10,
        use_ancestor_coi: bool = False,
        check_completeness: bool = False,
) -> CoiResult:
    """
    COI для одной собаки по формуле Райта.
      dog — объект с .sire_id, .dam_id
      generations — глубина (1–10, стандарт FCI = 5)
      use_ancestor_coi — учитывать COI самих предков (1 + F_A)
      check_completeness — оставлен для совместимости, не используется
    """
    generations = max(1, min(generations, 10))

    if not dog.sire_id or not dog.dam_id:
        return CoiResult(
            coi=0.0, generations=generations, common_ancestors=0,
            total_ancestors_sire=0, total_ancestors_dam=0,
            error="Нет данных об одном или обоих родителях",
        )

    if dog.sire_id == dog.dam_id:
        return CoiResult(
            coi=50.0, generations=generations, common_ancestors=1,
            total_ancestors_sire=0, total_ancestors_dam=0,
        )

    depth = generations - 1
    paths_sire = _collect_ancestor_paths(dog.sire_id, depth)
    paths_dam = _collect_ancestor_paths(dog.dam_id, depth)

    common_ids: Set[int] = set(paths_sire.keys()) & set(paths_dam.keys())

    if not common_ids:
        return CoiResult(
            coi=0.0, generations=generations, common_ancestors=0,
            total_ancestors_sire=len(paths_sire), total_ancestors_dam=len(paths_dam),
        )

    ancestor_fa: Dict[int, float] = {}
    if use_ancestor_coi:
        ancestor_fa = dog_repo.get_coi_for_ancestors(common_ids)

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


# BFS
def _collect_ancestor_paths(root_id: int, max_depth: int) -> Dict[int, List[int]]:
    """BFS по дереву предков. Один SQL на поколение → {ancestor_id: [depth, ...]}."""
    paths: Dict[int, List[int]] = defaultdict(list)
    paths[root_id].append(0)
    current_front: Dict[int, List[int]] = {root_id: [0]}

    for _depth in range(1, max_depth + 1):
        if not current_front:
            break

        parent_rows = dog_repo.get_parents_batch_values(set(current_front.keys()))
        next_front: Dict[int, List[int]] = defaultdict(list)

        for row in parent_rows:
            dog_id = row['id']
            for parent_id in filter(None, (row['sire_id'], row['dam_id'])):
                for d in current_front.get(dog_id, []):
                    new_depth = d + 1
                    paths[parent_id].append(new_depth)
                    next_front[parent_id].append(new_depth)

        current_front = dict(next_front)

    return dict(paths)


# СОХРАНЕНИЕ

def save_coi(dog, result: CoiResult):
    """Сохраняет COI в Dog (только coi + coi_updated_on)."""
    from django.utils import timezone
    coi_value = result.coi if result.is_valid else None
    dog_repo.save_coi(dog, coi_value, timezone.now())

    label = f"{result.coi:.4f}%" if result.is_valid else "null"
    logger.info(f"💾 COI: {dog.registered_name} (id={dog.id}) → {label}")
    return dog


def calculate_coi_for_pair(
        sire_id: int,
        dam_id: int,
        generations: int = 10,
        use_ancestor_coi: bool = False,
) -> CoiResult:
    """
    Рассчитывает ожидаемый COI потомства для пары (sire_id, dam_id)
    без создания объекта Dog.
    """
    from types import SimpleNamespace
    virtual = SimpleNamespace(id=None, sire_id=sire_id, dam_id=dam_id)
    return calculate_coi(virtual, generations, use_ancestor_coi, check_completeness=False)
