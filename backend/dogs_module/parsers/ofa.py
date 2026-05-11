# dogs_module/parsers/ofa.py
"""
OFA парсер — только HTTP и парсинг.

Два запроса к https://api.ofa.org/api/as.php:
  1. POST as_action[search]  → appnum + рег.номер из таблицы результатов
  2. POST api_nav D1         → CSV по рег.номеру → парсинг в памяти

Использование рег.номера для скачивания CSV гарантирует что получим
данные именно той собаки которую нашли, а не всех однофамильцев.
"""

import logging
import re
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from ..config import (
    OFA_API_URL,
    OFA_BB_URL,
    OFA_HEADERS,
    BREED_CODE,
    OFA_BROWSE_BY_BREED_CHOOSE_BREED_PATH,
)

logger = logging.getLogger(__name__)

_BASE_FORM = {
    "api_action":                  "as_action",
    "api_key":                     "",
    "api_preset":                  "dog",
    "api_sort":                    "",
    "api_sort_prior":              "name",
    "api_sort_dir":                "A",
    "api_page":                    "",
    "api_layout":                  "S",
    "as_filter[quicksearch]":      "",
    "as_filter[favorites]":        "",
    "as_filter[fullpart]":         "F",
    "as_filter[special][chic]":    "N",
    "as_filter[special][dnabank]": "N",
    "as_filter[special][photo]":   "N",
    "as_action[search]":           "",
}

_SEX_MAP = {1: "M", 2: "F"}


# ── Сессия ────────────────────────────────────────────────────────────────────

def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(OFA_HEADERS)
    try:
        session.get(f"{OFA_API_URL}?a=/advanced-search/", timeout=15)
        logger.debug("OFA: сессия инициализирована")
    except requests.RequestException as e:
        logger.warning(f"OFA: ошибка инициализации сессии: {e}")
    return session


# ── Шаг 1: поиск → (appnum, reg_num) ─────────────────────────────────────────

def _search_appnum(
    session,
    *,
    reg_name=None,
    reg_num=None,
    ofa_num=None,
    expected_sex=None,
    expected_year=None,
) -> tuple:
    """
    POST-запрос — поиск собаки.

    Возвращает (appnum, reg_num) или (None, None).
    reg_num — рег.номер из таблицы результатов (используется для скачивания CSV).

    Логика при нескольких результатах:
      1. Фильтр по полу
      2. Среди совпавших по полу — фильтр по году рождения
      3. Если год не совпал — берём первого по полу
    """
    data = dict(_BASE_FORM)
    if reg_name:
        data["as_filter[regname]"] = reg_name
    if reg_num:
        data["as_filter[regnum]"] = reg_num
    if ofa_num:
        data["as_filter[ofanum]"] = ofa_num

    files = {k: (None, v) for k, v in data.items()}

    try:
        resp = session.post(OFA_API_URL, files=files, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"OFA search POST error: {e}")
        return None, None

    if not resp.text or not resp.text.strip():
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select(".as_results_row[data-appnum]")

    if not rows:
        key_input = soup.find("input", {"name": "api_key"})
        if key_input and key_input.get("value"):
            appnum = key_input["value"]
            logger.info(f"OFA search: единственный результат, appnum={appnum}")
            return appnum, None
        logger.info("OFA search: результатов нет")
        return None, None

    def _get_reg_from_row(row):
        """Берёт рег.номер из колонки 2 строки результатов."""
        cells = row.find_all("td")
        if len(cells) >= 3:
            return cells[2].get_text(strip=True) or None
        return None

    if len(rows) == 1:
        appnum = rows[0].get("data-appnum")
        found_reg = _get_reg_from_row(rows[0])
        logger.info(f"OFA search: 1 результат, appnum={appnum}, reg={found_reg}")
        return appnum, found_reg

    # Несколько результатов — фильтруем
    logger.info(f"OFA search: {len(rows)} результатов, фильтрую по полу и году")

    ofa_sex_str = _SEX_MAP.get(expected_sex) if expected_sex else None

    # Шаг 1: фильтр по полу
    # Структура: [пусто, имя, рег.номер, порода, пол, цвет, дата]
    sex_matched = []
    for row in rows:
        cells = row.find_all("td")
        if ofa_sex_str and len(cells) >= 5:
            row_sex = cells[4].get_text(strip=True).upper()
            if row_sex == ofa_sex_str:
                sex_matched.append(row)
        else:
            sex_matched.append(row)

    if not sex_matched:
        appnum = rows[0].get("data-appnum")
        found_reg = _get_reg_from_row(rows[0])
        logger.warning(f"OFA search: ни один не совпал по полу, берём первый appnum={appnum}")
        return appnum, found_reg

    if len(sex_matched) == 1:
        appnum = sex_matched[0].get("data-appnum")
        found_reg = _get_reg_from_row(sex_matched[0])
        logger.info(f"OFA search: 1 совпадение по полу, appnum={appnum}, reg={found_reg}")
        return appnum, found_reg

    # Шаг 2: среди совпавших по полу — ищем по году рождения
    if expected_year:
        for row in sex_matched:
            cells = row.find_all("td")
            if len(cells) >= 7:
                birth_raw = cells[6].get_text(strip=True)
                birth_date = _parse_date(birth_raw)
                if birth_date and abs(birth_date.year - expected_year) <= 1:
                    appnum = row.get("data-appnum")
                    found_reg = _get_reg_from_row(row)
                    logger.info(
                        f"OFA search: совпал по полу и году {expected_year}, "
                        f"appnum={appnum}, reg={found_reg}"
                    )
                    return appnum, found_reg

        appnum = sex_matched[0].get("data-appnum")
        found_reg = _get_reg_from_row(sex_matched[0])
        logger.warning(
            f"OFA search: {len(sex_matched)} совпадений по полу, "
            f"ни один не совпал по году {expected_year}, "
            f"берём первого appnum={appnum}"
        )
        return appnum, found_reg

    appnum = sex_matched[0].get("data-appnum")
    found_reg = _get_reg_from_row(sex_matched[0])
    logger.warning(
        f"OFA search: {len(sex_matched)} совпадений по полу, "
        f"год не передан, берём первого appnum={appnum}"
    )
    return appnum, found_reg


# ── Шаг 2: скачать CSV ────────────────────────────────────────────────────────

def _fetch_csv(session, appnum, *, reg_name=None, reg_num=None) -> Optional[str]:
    """
    POST api_nav D1 — скачать CSV.

    Используем reg_num если есть — он уникален и гарантирует
    что CSV придёт именно для найденной собаки, а не для всех однофамильцев.
    """
    data = dict(_BASE_FORM)
    data["api_action"] = "api_nav"
    data["api_key"] = "D1"

    if reg_num:
        data["as_filter[regnum]"] = reg_num
    elif reg_name:
        data["as_filter[regname]"] = reg_name

    files = {k: (None, v) for k, v in data.items()}

    try:
        resp = session.post(OFA_API_URL, files=files, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"OFA CSV download error: {e}")
        return None

    text = resp.text.strip()
    if not text or "Registration" not in text:
        logger.warning(f"OFA CSV: невалидный ответ для appnum={appnum}")
        return None

    logger.info(f"OFA CSV: получен для appnum={appnum}, длина={len(text)}")
    return text


# ── Парсинг CSV ───────────────────────────────────────────────────────────────

def _parse_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    cleaned = " ".join(raw.split())
    for fmt in ("%b %d %Y", "%b %d, %Y"):
        try:
            return timezone.make_aware(datetime.strptime(cleaned, fmt))
        except ValueError:
            continue
    logger.warning(f"OFA: не удалось распарсить дату '{raw}'")
    return None


def _parse_age(raw: str) -> Optional[int]:
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return None


def _parse_csv(csv_text: str) -> dict:
    """
    Парсит CSV от OFA.

    Колонки:
      Registration, Name, Breed, Variety, Color, Sex, Birth_Date,
      Sire, Dam, AppNum, CHIC, Test_Date, Age(mos), Registry, Results, OFA_#
    """
    import csv as csv_module
    import io

    result = {"appnum": None, "dog_info": {}, "medical_records": []}
    first_row = True

    reader = csv_module.DictReader(io.StringIO(csv_text))
    for row in reader:
        normalized = {k.strip(): v.strip() for k, v in row.items() if k}

        if first_row:
            result["dog_info"] = {
                "name":                normalized.get("Name", ""),
                "registration_number": normalized.get("Registration", ""),
                "sex_raw":             normalized.get("Sex", "").upper(),
                "date_of_birth":       _parse_date(normalized.get("Birth_Date", "")),
                "sire_reg":            normalized.get("Sire", ""),
                "dam_reg":             normalized.get("Dam", ""),
            }
            result["appnum"] = normalized.get("AppNum", "")
            first_row = False

        ofa_num = normalized.get("OFA_#", "").strip()
        registry = normalized.get("Registry", "").strip()
        if not registry or not ofa_num:
            continue

        result["medical_records"].append({
            "registry":      registry,
            "test_date":     _parse_date(normalized.get("Test_Date", "")),
            "report_date":   None,
            "age_in_months": _parse_age(normalized.get("Age(mos)", "")),
            "conclusion":    normalized.get("Results", "").strip(),
            "ofa_number":    ofa_num,
        })

    logger.info(
        f"OFA CSV parsed: appnum={result['appnum']}, "
        f"records={len(result['medical_records'])}"
    )
    return result


# ── Публичный API ─────────────────────────────────────────────────────────────

def fetch_ofa_data(
    *,
    registered_name=None,
    registration_number=None,
    ofa_number=None,
    expected_sex=None,
    expected_year=None,
) -> Optional[dict]:
    """
    Ищет собаку в OFA и возвращает данные через CSV.

    Два запроса:
      1. POST as_action[search] → appnum + рег.номер из таблицы
      2. POST api_nav D1        → CSV по рег.номеру → парсинг в памяти
    """
    if not any([registered_name, registration_number, ofa_number]):
        raise ValueError("Нужен хотя бы один параметр поиска")

    session = _make_session()

    appnum, found_reg_num = _search_appnum(
        session,
        reg_name=registered_name,
        reg_num=registration_number,
        ofa_num=ofa_number,
        expected_sex=expected_sex,
        expected_year=expected_year,
    )
    if not appnum:
        logger.info(
            f"OFA: не найдена — "
            f"name={registered_name!r}, reg={registration_number!r}"
        )
        return None

    # Используем рег.номер из результатов поиска если есть —
    # это гарантирует что CSV придёт именно для этой собаки
    csv_text = _fetch_csv(
        session,
        appnum,
        reg_num=found_reg_num or registration_number,
        reg_name=registered_name if not found_reg_num and not registration_number else None,
    )
    if not csv_text:
        logger.warning(f"OFA: CSV не получен для appnum={appnum}")
        return None

    result = _parse_csv(csv_text)
    if not result["appnum"]:
        result["appnum"] = appnum

    del csv_text  # освобождаем память

    logger.info(
        f"OFA: данные получены — appnum={appnum}, "
        f"records={len(result['medical_records'])}"
    )
    return result

def fetch_ofa_breed_stats(breed_code: str = BREED_CODE) -> Optional[dict]:
    """
    Получает статистику здоровья породы с OFA.
    Возвращает dict {registry: {total, normal, pct_normal}} или None.

    Используется в ofa_service.get_breed_ofa_stats() с кэшированием.
    """
    session = requests.Session()
    session.headers.update({
        **OFA_HEADERS,
        "Referer": f"{OFA_BROWSE_BY_BREED_CHOOSE_BREED_PATH}{breed_code}",
    })

    # Шаг 1 — инициализация сессии
    try:
        session.get(
            f"{OFA_BB_URL}?a=/chic-programs/browse-by-breed/&breed={breed_code}",
            timeout=15,
        )
    except requests.RequestException as e:
        logger.warning(f"OFA stats: ошибка инициализации: {e}")

    # Шаг 2 — запрос статистики (кнопка Statistics)
    files = {
        "api_action": (None, ""),
        "api_key": (None, ""),
        "bb_filter[brdvar][]": (None, breed_code),
        "bb_action[dft]": (None, ""),
    }

    try:
        resp = session.post(OFA_BB_URL, files=files, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"OFA stats: ошибка запроса: {e}")
        return None

    if not resp.text or len(resp.text) < 100:
        logger.warning("OFA stats: пустой ответ")
        return None

    return _parse_breed_stats(resp.text)


def _parse_breed_stats(html: str) -> Optional[dict]:
    """
    Парсит таблицу статистики OFA по породе.
    Ищет таблицу с колонками Registry / Total / Normal.
    """
    soup = BeautifulSoup(html, "html.parser")
    stats = {}

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        headers = [
            th.get_text(strip=True).lower()
            for th in rows[0].find_all(["th", "td"])
        ]

        # Ищем таблицу со статистикой — должны быть колонки total и normal
        if not any(h in headers for h in ("total", "registry", "test")):
            continue

        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if len(cells) < 3:
                continue

            registry = cells[0].strip()
            if not registry or registry.lower() in ("total", "totals", ""):
                continue

            try:
                total = int(cells[1].replace(",", "")) if cells[1].replace(",", "").isdigit() else 0
                normal = int(cells[2].replace(",", "")) if cells[2].replace(",", "").isdigit() else 0

                if total > 0:
                    stats[registry] = {
                        "total": total,
                        "normal": normal,
                        "pct_normal": round(normal / total * 100, 1),
                    }
            except (ValueError, IndexError):
                continue

    if stats:
        logger.info(f"OFA stats: распарсено {len(stats)} тестов")
    else:
        logger.warning("OFA stats: таблица не найдена в ответе")

    return stats or None
