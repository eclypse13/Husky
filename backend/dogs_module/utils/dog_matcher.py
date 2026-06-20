from datetime import datetime, date
from typing import Any, Dict, Tuple
from ..utils.text import normalize_for_similarity
from ..config.matching import (
    NAME_AUTO_MERGE, NAME_FLAG_REVIEW, PARENT_NAME_MATCH, YEAR_WINDOW,
)

# Поля, по которым проверяются конфликты между источниками
_CONFLICT_FIELDS = (
    'call_name', 'sex', 'date_of_birth', 'date_of_death',
    'land_of_birth', 'land_of_standing', 'color', 'color_marking',
    'eyes_color', 'registration_number', 'brand_chip', 'coi',
    'photo_url', 'kennel', 'sire_name', 'dam_name',
)

# Числовые поля, требующие приведения типов перед сравнением
_NUMERIC_FIELDS = ('size', 'weight', 'coi')


# Приводит значение числового поля к float для сравнения
def _to_comparable(field: str, value: Any) -> Any:
    if field in _NUMERIC_FIELDS and isinstance(value, str):
        try:
            return float(value.strip())
        except (ValueError, TypeError):
            pass
    return value


# Конвертирует дату/время в ISO-строку для JSON-сериализации
def _serialize(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


# Сравнивает поля существующей записи Dog с новыми данными
def detect_conflicts(
        existing_dog: Any,
        new_data: Dict[str, Any],
        source: str,
) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
    existing_dict = {f: getattr(existing_dog, f, None) for f in _CONFLICT_FIELDS}
    existing_source = getattr(existing_dog, 'source', None) or 'unknown'
    return detect_dict_conflicts(existing_dict, new_data, existing_source, source)


# Детектирует конфликты между двумя словарями данных (до сохранения в БД)
def detect_dict_conflicts(
        left: Dict[str, Any],
        right: Dict[str, Any],
        left_source: str,
        right_source: str,
) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
    conflicts: Dict[str, Dict[str, Any]] = {}

    for key in set(left) & set(right):
        lv, rv = left.get(key), right.get(key)
        if lv in (None, '') or rv in (None, ''):
            continue
        if lv == rv:
            continue
        # registered_name — без учёта регистра
        if key == 'registered_name':
            if str(lv).upper() == str(rv).upper():
                continue
        conflicts[key] = {
            left_source: _serialize(lv),
            right_source: _serialize(rv),
        }

    return bool(conflicts), conflicts


try:
    from rapidfuzz.distance import JaroWinkler


    def _jw(a: str, b: str) -> float:
        return JaroWinkler.similarity(a, b)
except ImportError:  # fallback без зависимости
    def _jw(a: str, b: str) -> float:
        # упрощённый Jaro-Winkler на чистом Python (если будут проблемы при импоре бибилотеки)
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0
        la, lb = len(a), len(b)
        win = max(la, lb) // 2 - 1
        ma = [False] * la
        mb = [False] * lb
        matches = 0
        for i in range(la):
            lo, hi = max(0, i - win), min(i + win + 1, lb)
            for j in range(lo, hi):
                if not mb[j] and a[i] == b[j]:
                    ma[i] = mb[j] = True
                    matches += 1
                    break
        if matches == 0:
            return 0.0
        t = k = 0
        for i in range(la):
            if ma[i]:
                while not mb[k]:
                    k += 1
                if a[i] != b[k]:
                    t += 1
                k += 1
        t /= 2
        jaro = (matches / la + matches / lb + (matches - t) / matches) / 3
        prefix = 0
        for i in range(min(4, la, lb)):
            if a[i] == b[i]:
                prefix += 1
            else:
                break
        return jaro + prefix * 0.1 * (1 - jaro)


# Jaro-Winkler похожести двух имён собак после нормализации (0..1)
def name_similarity(a: str, b: str) -> float:
    na, nb = normalize_for_similarity(a), normalize_for_similarity(b)
    if not na or not nb:
        return 0.0
    return _jw(na, nb)


# Сравнение родителей по именам
def _parents_match(new: dict, cand: dict) -> str:
    pairs = []
    for role in ("sire_name", "dam_name"):
        n, c = new.get(role), cand.get(role)
        if n and c:
            pairs.append(name_similarity(n, c) >= PARENT_NAME_MATCH)
    if not pairs:
        return "unknown"
    if all(pairs) and len(pairs) == 2:
        return "both"
    if any(pairs):
        return "one"
    return "none"


def _year_match(new: dict, cand: dict) -> bool:
    y1, y2 = new.get("year_of_birth"), cand.get("year_of_birth")
    if not y1 or not y2:
        return False
    return abs(int(y1) - int(y2)) <= YEAR_WINDOW


# Решение по паре (новая собака, кандидат из БД)
def classify_duplicate(new: dict, cand: dict) -> tuple:
    # Пол обязан совпадать — иначе разные точно
    if new.get("sex") and cand.get("sex") and new["sex"] != cand["sex"]:
        return "different", 0.0, "разный пол"

    score = name_similarity(new.get("registered_name", ""), cand.get("registered_name", ""))
    if score < NAME_FLAG_REVIEW:
        return "different", score, f"имя не похоже ({score:.2f})"

    parents = _parents_match(new, cand)
    year_ok = _year_match(new, cand)

    # Высокая уверенность → слияние
    if score >= NAME_AUTO_MERGE and (parents == "both" or (parents == "one" and year_ok)):
        return "merge", score, f"имя={score:.2f}, родители={parents}, год={'ok' if year_ok else '-'}"
    if score >= 0.95 and year_ok and parents != "none":
        return "merge", score, f"имя={score:.2f}, год совпал"

    # Средняя → пометка
    if parents == "none":
        return "different", score, "родители различаются"
    if year_ok or parents in ("both", "one"):
        return "flag", score, f"имя={score:.2f}, родители={parents}, год={'ok' if year_ok else '-'}"

    return "different", score, f"недостаточно подтверждений ({score:.2f})"
