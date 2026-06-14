# dogs_module/parsers/ofa.py
"""
OFA парсер.
"""

import logging
import re
from typing import Optional, List, Dict

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ..utils.parser_utils import parse_date
from ..config import (
    OFA_API_URL,
    OFA_BB_URL,
    OFA_HEADERS,
    BREED_CODE,
    OFA_BROWSE_BY_BREED_CHOOSE_BREED_PATH,
)

logger = logging.getLogger(__name__)

_BASE_FORM = {
    "api_action": "as_action",
    "api_key": "",
    "api_preset": "dog",
    "api_sort": "",
    "api_sort_prior": "name",
    "api_sort_dir": "A",
    "api_page": "",
    "api_layout": "S",
    "as_filter[quicksearch]": "",
    "as_filter[favorites]": "",
    "as_filter[fullpart]": "F",
    "as_filter[special][chic]": "N",
    "as_filter[special][dnabank]": "N",
    "as_filter[special][photo]": "N",
    "as_action[search]": "",
}

_SEX_MAP = {1: "M", 2: "F"}


# Сессия

def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(OFA_HEADERS)

    # Ретраи на сетевых сбоях и 5xx: 3 попытки с экспоненциальным бэкоффом
    retry = Retry(
        total=3,
        backoff_factor=2,           # паузы: 2s, 4s, 8s
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        session.get(f"{OFA_API_URL}?a=/advanced-search/", timeout=30)  # ← было 15, мало
        logger.debug("OFA: сессия инициализирована")
    except requests.RequestException as e:
        logger.warning(f"OFA: ошибка инициализации сессии: {e}")
    return session

# Шаг 1: поиск → (appnum, reg_num)

def _search_animals(
        session, *, reg_name=None, reg_num=None, ofa_num=None, expected_sex=None,
) -> dict:
    """
    POST-поиск. Возвращает {appnum: regnum|None} ВСЕХ найденных животных.
    """
    data = dict(_BASE_FORM)
    if reg_name: data["as_filter[regname]"] = reg_name
    if reg_num:  data["as_filter[regnum]"] = reg_num
    if ofa_num:  data["as_filter[ofanum]"] = ofa_num
    if expected_sex in _SEX_MAP:  # сужаем выборку у OFA — меньше мусора, легче CSV
        data["as_filter[sex]"] = _SEX_MAP[expected_sex]

    files = {k: (None, v) for k, v in data.items()}
    try:
        resp = session.post(OFA_API_URL, files=files, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"OFA search POST error: {e}")
        return {}

    if not resp.text or not resp.text.strip():
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select(".as_results_row[data-appnum]")

    if not rows:  # единственный результат отдаётся как api_key
        key_input = soup.find("input", {"name": "api_key"})
        if key_input and key_input.get("value"):
            return {key_input["value"]: reg_num}
        logger.info("OFA search: результатов нет")
        return {}

    found = {}
    for row in rows:
        appnum = row.get("data-appnum")
        if not appnum:
            continue
        cells = row.find_all("td")
        regnum = cells[2].get_text(strip=True) if len(cells) >= 3 else None
        found[appnum] = regnum or None
    logger.info(f"OFA search: найдено животных={len(found)}")
    return found


# Шаг 2: скачать CSV

def _fetch_csv(session, *, reg_name=None, reg_num=None, ofa_num=None, expected_sex=None):
    """POST api_nav D1 — скачать CSV самым точным доступным фильтром."""
    data = dict(_BASE_FORM)
    data["api_action"] = "api_nav"
    data["api_key"] = "D1"
    if reg_num:
        data["as_filter[regnum]"] = reg_num
    elif ofa_num:
        data["as_filter[ofanum]"] = ofa_num
    elif reg_name:
        data["as_filter[regname]"] = reg_name
    if expected_sex in _SEX_MAP:
        data["as_filter[sex]"] = _SEX_MAP[expected_sex]

    files = {k: (None, v) for k, v in data.items()}
    try:
        resp = session.post(OFA_API_URL, files=files, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"OFA CSV download error: {e}")
        return None

    text = resp.text.strip()
    if not text or "Registration" not in text:
        logger.warning("OFA CSV: невалидный ответ")
        return None
    return text


# Парсинг CSV
def _parse_age(raw: str) -> Optional[int]:
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return None


def _parse_csv_grouped(csv_text: str) -> list:
    """
    Парсит CSV и группирует строки по AppNum → по одному кандидату на животное.
    """
    import csv as csv_module, io

    groups: dict = {}
    reader = csv_module.DictReader(io.StringIO(csv_text))
    for row in reader:
        n = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        appnum = n.get("AppNum", "")
        if not appnum:
            continue

        g = groups.get(appnum)
        if g is None:
            g = groups[appnum] = {
                "appnum": appnum,
                "registration_number": n.get("Registration", ""),
                "dog_info": {
                    "name": n.get("Name", ""),
                    "registered_name": n.get("Name", ""),  # для сверки имени в сервисе
                    "registration_number": n.get("Registration", ""),
                    "sex_raw": n.get("Sex", "").upper(),
                    "date_of_birth": parse_date(n.get("Birth_Date", "")),
                    "sire_reg": n.get("Sire", ""),
                    "dam_reg": n.get("Dam", ""),
                },
                "medical_records": [],
            }

        registry = n.get("Registry", "").strip()
        ofa_num = n.get("OFA_#", "").strip()
        if registry and ofa_num:
            g["medical_records"].append({
                "registry": registry,
                "test_date": parse_date(n.get("Test_Date", "")),
                "report_date": None,
                "age_in_months": _parse_age(n.get("Age(mos)", "")),
                "conclusion": n.get("Results", "").strip(),
                "ofa_number": ofa_num,
            })

    total = sum(len(g["medical_records"]) for g in groups.values())
    logger.info(f"OFA CSV: животных={len(groups)}, записей суммарно={total}")
    return list(groups.values())


# Публичный API

def fetch_ofa_breed_stats(breed_code: str = BREED_CODE) -> Optional[dict]:
    """
    Получает статистику здоровья породы с OFA.
    Возвращает dict {registry: {total, normal, pct_normal}} или None.
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

        # ищем таблицу со статистикой — должны быть колонки total и normal
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


def fetch_ofa_data(*, registered_name=None, registration_number=None, ofa_number=None,
                   expected_sex=None, expected_year=None) -> dict:
    """Ищет собаку в OFA. Возвращает {"candidates": [...]} — по кандидату на животное."""
    if not any([registered_name, registration_number, ofa_number]):
        raise ValueError("Нужен хотя бы один параметр поиска")

    session = _make_session()

    found = _search_animals(
        session, reg_name=registered_name, reg_num=registration_number,
        ofa_num=ofa_number, expected_sex=expected_sex,
    )
    if not found:
        logger.info(f"OFA: не найдена — name={registered_name!r}, reg={registration_number!r}")
        return {"candidates": []}

    csv_text = _fetch_csv(
        session, reg_name=registered_name, reg_num=registration_number,
        ofa_num=ofa_number, expected_sex=expected_sex,
    )
    if not csv_text:
        return {"candidates": []}

    grouped = _parse_csv_grouped(csv_text)

    # CSV полнее поиска (поиск отдаёт максимум ~20, CSV — всех по фильтру).
    # Поэтому кандидаты = ВСЕ группы CSV. found используем лишь чтобы
    # добрать regnum и пометить, кто реально был в выдаче поиска.
    for c in grouped:
        if not c.get("registration_number") and found.get(c["appnum"]):
            c["registration_number"] = found[c["appnum"]]
        c["in_search_results"] = c["appnum"] in found

    logger.info(f"OFA: кандидатов={len(grouped)} (в выдаче поиска={len(found)})")
    return {"candidates": grouped}

