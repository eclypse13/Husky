# dogs_module/services/ancestor_features.py
"""
Агрегаты здоровья по предкам.

ЕДИНЫЙ источник признаков-по-предкам для обучения (dataset_builder) и для
инференса (ml_dog_service).

"""

from ..repositories import dog_repository as dog_repo
from ..domain.health_codes import HIP_DYSPLASIA_THRESHOLD, EYE_PROBLEM_THRESHOLD

# Глубина обхода предков (поколений вверх). 4 ≈ до прапрапредков.
ANCESTOR_DEPTH = 4

# Группы, по которым считаем агрегаты, и порог «болен» для каждой.
_AFFECTED_THRESHOLD = {
    "hips": HIP_DYSPLASIA_THRESHOLD,
    "eyes": EYE_PROBLEM_THRESHOLD,
}

# Группы, для которых считаем агрегаты (порядок важен для стабильности ключей).
_GROUPS = ("hips", "eyes")


def collect_ancestor_ids(
        root_id: int,
        depth: int = ANCESTOR_DEPTH,
        parent_map: dict[int, tuple] | None = None,
) -> set[int]:
    """
    BFS вверх по дереву предков от root_id (сам root_id НЕ включается).

    parent_map — {id: (sire_id, dam_id)} для in-memory обхода при обучении
                 (без запросов в БД). Если None — данные тянутся из БД пачками
                 через dog_repository.get_parents_batch_values.
    """
    seen: set[int] = set()
    front: set[int] = {root_id}

    for _ in range(depth):
        if not front:
            break

        if parent_map is not None:
            rows = [
                {"sire_id": parent_map.get(i, (None, None))[0],
                 "dam_id": parent_map.get(i, (None, None))[1]}
                for i in front
            ]
        else:
            rows = dog_repo.get_parents_batch_values(front)

        nxt: set[int] = set()
        for row in rows:
            for pid in (row.get("sire_id"), row.get("dam_id")):
                if pid and pid not in seen:
                    seen.add(pid)
                    nxt.add(pid)
        front = nxt

    return seen


def side_features(
        root_id: int,
        scores_by_dog: dict[int, dict],
        depth: int = ANCESTOR_DEPTH,
        parent_map: dict[int, tuple] | None = None,
) -> dict:
    """
    Агрегаты по предкам ОДНОЙ стороны (одного из родителей пары). Без префикса:
        anc_<group>_tested_ratio    — доля протестированных предков
        anc_<group>_mean            — средний балл по известным (None если нет)
        anc_<group>_affected_ratio  — доля больных среди известных (None если нет)

    scores_by_dog — {dog_id: {'hips': 2, 'eyes': 0, ...}} (результат extract_scores).
    """
    ancestors = collect_ancestor_ids(root_id, depth, parent_map)
    n_anc = len(ancestors)
    out: dict[str, float | None] = {}

    for group in _GROUPS:
        vals = [
            scores_by_dog[a][group]
            for a in ancestors
            if a in scores_by_dog and group in scores_by_dog[a]
        ]
        tested = len(vals)
        thr = _AFFECTED_THRESHOLD[group]

        # tested_ratio = 0.0 если предков нет — это валидный сигнал «нет данных».
        out[f"anc_{group}_tested_ratio"] = (tested / n_anc) if n_anc else 0.0
        # mean/affected — None если никто не тестирован (CatBoost ест NaN нативно).
        out[f"anc_{group}_mean"] = (sum(vals) / tested) if tested else None
        out[f"anc_{group}_affected_ratio"] = (
            sum(v >= thr for v in vals) / tested if tested else None
        )

    return out


def prefixed_side_features(side: str, *args, **kwargs) -> dict:
    """side_features с префиксом стороны: 'sire_' / 'dam_'."""
    return {f"{side}_{k}": v for k, v in side_features(*args, **kwargs).items()}


def empty_side_features(side: str) -> dict:
    """
    Агрегаты для случая «предки неизвестны» — синтетика и собаки без родословной.
    tested_ratio = 0.0, остальное None. Совпадает с тем, что вернёт
    prefixed_side_features для собаки без предков.
    """
    out: dict[str, float | None] = {}
    for group in _GROUPS:
        out[f"{side}_anc_{group}_tested_ratio"] = 0.0
        out[f"{side}_anc_{group}_mean"] = None
        out[f"{side}_anc_{group}_affected_ratio"] = None
    return out
