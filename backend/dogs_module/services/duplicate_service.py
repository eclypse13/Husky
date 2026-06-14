# dogs_module/services/duplicate_service.py
"""
Поиск и обработка вероятных дубликатов собак по нечёткому совпадению имени
+ подтверждению (родители / год / пол).
"""
import logging
from typing import Optional

from ..repositories import dog_repository as dog_repo
from ..utils.dog_matcher import classify_duplicate
from ..config.matching import YEAR_WINDOW, CANDIDATE_LIMIT

logger = logging.getLogger(__name__)


def find_duplicate(dog_fields: dict, exclude_pk: int = None) -> Optional[dict]:
    """
    Ищет лучший дубль для собаки. dog_fields: registered_name, sex,
    year_of_birth, sire_name, dam_name.
    → {'dog': Dog, 'verdict': 'merge'|'flag', 'score': float, 'reason': str} или None.
    """
    if not dog_fields.get("registered_name") or not dog_fields.get("sex"):
        return None

    candidates = dog_repo.get_duplicate_candidates(
        sex=dog_fields["sex"],
        year_of_birth=dog_fields.get("year_of_birth"),
        year_window=YEAR_WINDOW,
        exclude_pk=exclude_pk,
        limit=CANDIDATE_LIMIT,
    )

    best = None
    for cand in candidates:
        cand_fields = {
            "registered_name": cand.registered_name,
            "sex": cand.sex,
            "year_of_birth": cand.year_of_birth,
            "sire_name": cand.sire_name,
            "dam_name": cand.dam_name,
        }
        verdict, score, reason = classify_duplicate(dog_fields, cand_fields)
        if verdict == "different":
            continue
        if best is None or score > best["score"]:
            best = {"dog": cand, "verdict": verdict, "score": score, "reason": reason}

    return best


def flag_possible_duplicate(dog_pk: int, dup_pk: int, score: float, reason: str) -> None:
    """Помечает собаку как возможный дубль через поле conflicts (JSON)."""
    dog = dog_repo.get_by_id(dog_pk)
    if not dog:
        return
    conflicts = dog.conflicts or {}
    conflicts["possible_duplicate"] = {
        "dog_id": dup_pk, "score": round(score, 3), "reason": reason,
    }
    dog_repo.update_by_pk(dog_pk, {"has_conflicts": True, "conflicts": conflicts})
    logger.info(f"⚠️ dog {dog_pk}: возможный дубль dog_id={dup_pk} (score={score:.2f}, {reason})")
