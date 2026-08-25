"""Синхронизация породного рейтинга bestrussian.dog с локальной базой."""
import logging

from ..parsers.bestrussian import fetch_husky_breed_rating
from ..repositories import dog_repository as dog_repo
from ..repositories import show_repository as show_repo
from ..utils.text import normalize_for_similarity
from ..utils.dog_matcher import name_similarity
from ..config.matching import BESTRUSSIAN_MATCH_MIN_SCORE

logger = logging.getLogger(__name__)


def sync_husky_rating(year: int) -> dict:
    entries = fetch_husky_breed_rating(year)
    if not entries:
        return {'year': year, 'matched': 0, 'pending': 0, 'unmatched': 0, 'total_on_site': 0}

    by_name = {normalize_for_similarity(e['name']): e for e in entries}
    all_dogs = list(dog_repo.iter_id_registered_names())
    matched_ids = set()

    matched = 0
    for dog_id, registered_name in all_dogs:
        entry = by_name.pop(normalize_for_similarity(registered_name), None)
        if not entry:
            continue
        show_repo.upsert_bestrussian_rating(dog_id, year, entry['position'], entry['points'])
        matched_ids.add(dog_id)
        matched += 1

    candidates = [(i, n) for i, n in all_dogs if i not in matched_ids]

    pending = 0
    unmatched = 0
    for entry in by_name.values():
        best_id, best_name, best_score = _closest_name(entry['name'], candidates)

        if best_score >= BESTRUSSIAN_MATCH_MIN_SCORE:
            _flag_pending_match(best_id, year, entry, best_name, best_score)
            pending += 1
        else:
            logger.info(f"bestrussian {year}: не найдено в базе — '{entry['name']}'")
            unmatched += 1

    logger.info(f"bestrussian sync {year}: matched={matched} pending={pending} unmatched={unmatched}")
    return {
        'year': year, 'matched': matched, 'pending': pending,
        'unmatched': unmatched, 'total_on_site': len(entries),
    }


def _closest_name(name: str, candidates) -> tuple:
    best_id, best_name, best_score = None, None, 0.0
    for dog_id, registered_name in candidates:
        score = name_similarity(name, registered_name)
        if score > best_score:
            best_id, best_name, best_score = dog_id, registered_name, score
    return best_id, best_name, best_score


def _flag_pending_match(dog_id: int, year: int, entry: dict, db_name: str, score: float) -> None:
    dog = dog_repo.get_by_id(dog_id)
    if not dog:
        return
    conflicts = dog.conflicts or {}
    conflicts['bestrussian_pending_match'] = {
        'year': year,
        'site_name': entry['name'],
        'db_name': db_name,
        'position': entry['position'],
        'points': entry['points'],
        'score': round(score, 3),
    }
    dog_repo.update_by_pk(dog_id, {'has_conflicts': True, 'conflicts': conflicts})
    logger.info(f"bestrussian {year}: заявка на рассмотрение — '{entry['name']}' -> '{db_name}' ({score:.2f})")


def resolve_pending_match(dog_id: int, approve: bool) -> bool:
    dog = dog_repo.get_by_id(dog_id)
    if not dog:
        return False
    conflicts = dog.conflicts or {}
    pending = conflicts.pop('bestrussian_pending_match', None)
    if not pending:
        return False

    if approve:
        show_repo.upsert_bestrussian_rating(dog_id, pending['year'], pending['position'], pending['points'])

    dog_repo.update_by_pk(dog_id, {'conflicts': conflicts, 'has_conflicts': bool(conflicts)})
    return True
