# dogs_module/parsers/ofa.py
"""
OFA парсер — только HTTP и парсинг HTML.

Никакой работы с БД. Никаких Django-моделей кроме timezone.

Два запроса к https://api.ofa.org/api/as.php:
  1. POST — поиск → appnum
  2. GET  — детальная страница → данные собаки + медзаписи

Проверка пола:
  Если результатов поиска несколько — выбираем тот у которого
  пол совпадает с ожидаемым (expected_sex: 1=кобель, 2=сука).
  OFA возвращает "M" или "F" в колонке Sex таблицы результатов.
"""

import logging
import re
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

logger = logging.getLogger(__name__)

OFA_API_URL = "https://api.ofa.org/api/as.php"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://ofa.org",
    "Referer": "https://ofa.org/advanced-search/",
}

# Все обязательные поля формы из as-1.php
# api_action = "as_action" — JS парсит "as_action[search]" регуляркой
# и пишет в api_action только "as_action" (без [search])
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

# Маппинг пола: наш формат → OFA формат
_SEX_MAP = {1: "M", 2: "F"}


# ── Сессия ────────────────────────────────────────────────────────────────────

def _make_session() -> requests.Session:
    """
    Создаёт HTTP-сессию с начальным GET для получения cookies.
    Без GET сервер отвечает 'unhandled' на POST.
    """
    session = requests.Session()
    session.headers.update(_HEADERS)
    try:
        session.get(f"{OFA_API_URL}?a=/advanced-search/", timeout=15)
        logger.debug("OFA: сессия инициализирована")
    except requests.RequestException as e:
        logger.warning(f"OFA: ошибка инициализации сессии: {e}")
    return session


# ── Шаг 1: поиск → appnum ─────────────────────────────────────────────────────

def _search_appnum(
    session: requests.Session,
    *,
    reg_name: Optional[str] = None,
    reg_num: Optional[str] = None,
    ofa_num: Optional[str] = None,
    expected_sex: Optional[int] = None,
) -> tuple:
    """
    POST as_action[search] — поиск собаки.
    Возвращает (appnum, api_key) или (None, None).
    api_key нужен для последующего скачивания CSV.
    """
    data = dict(_BASE_FORM)
    data["as_action[search]"] = ""
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
        logger.info("OFA search: пустой ответ")
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Извлекаем api_key из ответа — нужен для CSV запроса
    api_key = ""
    key_input = soup.find("input", {"name": "api_key"})
    if key_input:
        api_key = key_input.get("value", "")

    rows = soup.select(".as_results_row[data-appnum]")

    if not rows:
        # Единственный результат — сервер вернул детальную страницу сразу
        if api_key:
            logger.info(f"OFA search: единственный результат, appnum={api_key}")
            return api_key, api_key
        logger.info("OFA search: результатов нет")
        return None, None

    if len(rows) == 1:
        appnum = rows[0].get("data-appnum")
        logger.info(f"OFA search: 1 результат, appnum={appnum}")
        return appnum, api_key

    # Несколько результатов — фильтруем по полу
    logger.info(f"OFA search: {len(rows)} результатов, фильтрую по полу")

    if expected_sex is None:
        appnum = rows[0].get("data-appnum")
        logger.warning(
            f"OFA search: несколько результатов, пол не передан — "
            f"берём первый appnum={appnum}"
        )
        return appnum, api_key

    ofa_sex_str = _SEX_MAP.get(expected_sex)
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 5:
            row_sex = cells[4].get_text(strip=True).upper()
            if row_sex == ofa_sex_str:
                appnum = row.get("data-appnum")
                logger.info(f"OFA search: совпал по полу {ofa_sex_str}, appnum={appnum}")
                return appnum, api_key

    appnum = rows[0].get("data-appnum")
    logger.warning(
        f"OFA search: ни один из {len(rows)} результатов не совпал по полу "
        f"(ожидали {ofa_sex_str}), берём первый appnum={appnum}"
    )
    return appnum, api_key


# ── Шаг 2: детальная страница ─────────────────────────────────────────────────

def _fetch_detail_html(session: requests.Session, appnum: str) -> Optional[str]:
    """
    GET /api/as.php?a=/advanced-search/&appnum=XXXXX

    URL строим вручную — requests кодирует слэши в 'a' как %2F,
    сервер ожидает незакодированные слэши.
    """
    url = f"{OFA_API_URL}?a=/advanced-search/&appnum={appnum}"
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.error(f"OFA detail GET error (appnum={appnum}): {e}")
        return None


# ── Парсинг HTML ──────────────────────────────────────────────────────────────

def _parse_date(raw: str) -> Optional[datetime]:
    """
    Парсит строки вида 'Nov 22 2021', 'Oct  6 2022'.
    Возвращает timezone-aware datetime (Django требует при USE_TZ=True).
    """
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


def _parse_dog_info(soup: BeautifulSoup) -> dict:
    """
    Парсит #as_detail_individual.

    Структура строк:
      0: <span id='as_detail_name'>ИМЯ, CH</span>
      1: WS17427605  (первое слово — рег. номер)
      2: M GRAY & WHITE SIBERIAN HUSKY
      3: Born May  9 2006
      4: (пустая)
      5: Sire: WP96427603<br /> Dam: WS04742001<br />
    """
    info: dict = {}
    block = soup.find(id="as_detail_individual")
    if not block:
        logger.warning("OFA: #as_detail_individual не найден")
        return info

    for i, row in enumerate(block.find_all("tr")):
        text = row.get_text(separator=" ", strip=True)
        if not text:
            continue

        if i == 0:
            name_span = soup.find(id="as_detail_name")
            info["name"] = name_span.get_text(strip=True) if name_span else text

        elif i == 1:
            info["registration_number"] = text.split()[0]

        elif i == 2:
            parts = text.split(None, 1)
            if parts:
                info["sex_raw"] = parts[0].upper()
                if len(parts) > 1:
                    info["breed_color"] = parts[1]

        elif i == 3 and text.lower().startswith("born"):
            info["date_of_birth"] = _parse_date(text[4:].strip())

        elif "Sire:" in text or "Dam:" in text:
            sire = re.search(r'Sire:\s*(\S+)', text)
            dam = re.search(r'Dam:\s*(\S+)', text)
            if sire:
                info["sire_reg"] = sire.group(1)
            if dam:
                info["dam_reg"] = dam.group(1)

    return info


def _parse_medical_records(soup: BeautifulSoup) -> list:
    """
    Парсит #as_detail_tests.

    Колонки: Registry | Test Date | Report Date | Age(m) | Conclusion | OFA Number
    """
    records = []
    table = soup.find(id="as_detail_tests")
    if not table:
        logger.warning("OFA: #as_detail_tests не найден")
        return records

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 6:
            continue
        records.append({
            "registry":      cells[0].get_text(strip=True),
            "test_date":     _parse_date(cells[1].get_text(strip=True)),
            "report_date":   _parse_date(cells[2].get_text(strip=True)),
            "age_in_months": _parse_age(cells[3].get_text(strip=True)),
            "conclusion":    cells[4].get_text(strip=True),
            "ofa_number":    cells[5].get_text(strip=True),
        })

    logger.info(f"OFA: распарсено {len(records)} медицинских записей")
    return records

# ── Шаг 2 (новый): скачать CSV по appnum ─────────────────────────────────────

def _fetch_csv(session, appnum, *, reg_name=None, reg_num=None):
    data = dict(_BASE_FORM)
    data["api_action"] = "api_nav"
    data["api_key"] = "D1"      # ← вот что JS пишет перед сабмитом

    if reg_name:
        data["as_filter[regname]"] = reg_name
    if reg_num:
        data["as_filter[regnum]"] = reg_num

    files = {k: (None, v) for k, v in data.items()}

    try:
        resp = session.post(OFA_API_URL, files=files, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"OFA CSV download error: {e}")
        return None

    logger.info(f"OFA CSV status: {resp.status_code}, length: {len(resp.text)}")
    logger.info(f"OFA CSV response: {resp.text[:200]}")

    text = resp.text.strip()
    if not text or "Registration" not in text:
        logger.warning(f"OFA CSV: невалидный ответ для appnum={appnum}")
        return None

    return text


# ── Парсинг CSV ───────────────────────────────────────────────────────────────

def _parse_csv(csv_text: str) -> dict:
    """
    Парсит CSV текст от OFA.

    Колонки:
      Registration, Name, Breed, Variety, Color, Sex, Birth_Date,
      Sire, Dam, AppNum, CHIC, Test_Date, Age(mos), Registry, Results, OFA_#

    Данные о собаке одинаковы во всех строках — берём из первой.
    Каждая строка = один тест.
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

def fetch_ofa_data_html(
    *,
    registered_name: Optional[str] = None,
    registration_number: Optional[str] = None,
    ofa_number: Optional[str] = None,
    expected_sex: Optional[int] = None,
) -> Optional[dict]:
    """
    Ищет собаку в OFA и возвращает распарсенные данные.

    expected_sex — пол из нашей БД (1=кобель, 2=сука).
    Используется для фильтрации при нескольких результатах поиска.

    Возвращает dict или None если не найдена.
    """
    if not any([registered_name, registration_number, ofa_number]):
        raise ValueError("Нужен хотя бы один параметр поиска")

    session = _make_session()

    appnum = _search_appnum(
        session,
        reg_name=registered_name,
        reg_num=registration_number,
        ofa_num=ofa_number,
        expected_sex=expected_sex,
    )
    if not appnum:
        logger.info(
            f"OFA: не найдена — "
            f"name={registered_name!r}, reg={registration_number!r}"
        )
        return None

    html = _fetch_detail_html(session, appnum)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    result = {
        "appnum":          appnum,
        "dog_info":        _parse_dog_info(soup),
        "medical_records": _parse_medical_records(soup),
    }
    logger.info(
        f"OFA: данные получены — appnum={appnum}, "
        f"records={len(result['medical_records'])}"
    )
    return result

def fetch_ofa_data(
    *,
    registered_name: Optional[str] = None,
    registration_number: Optional[str] = None,
    ofa_number: Optional[str] = None,
    expected_sex: Optional[int] = None,
) -> Optional[dict]:
    """
    Ищет собаку в OFA и возвращает данные через CSV.

    Два запроса:
      1. POST as_action[search]  → appnum + api_key
      2. POST api_nav[D1]        → CSV → парсинг в памяти
    """
    if not any([registered_name, registration_number, ofa_number]):
        raise ValueError("Нужен хотя бы один параметр поиска")

    session = _make_session()

    appnum, api_key = _search_appnum(
        session,
        reg_name=registered_name,
        reg_num=registration_number,
        ofa_num=ofa_number,
        expected_sex=expected_sex,
    )
    if not appnum:
        logger.info(
            f"OFA: не найдена — "
            f"name={registered_name!r}, reg={registration_number!r}"
        )
        return None

    csv_text = _fetch_csv(
        session,
        appnum,
        reg_name=registered_name,
        reg_num=registration_number,
    )
    if not csv_text:
        logger.warning(f"OFA: CSV не получен для appnum={appnum}")
        return None

    result = _parse_csv(csv_text)
    if not result["appnum"]:
        result["appnum"] = appnum

    logger.info(
        f"OFA: данные получены — appnum={appnum}, "
        f"records={len(result['medical_records'])}"
    )
    return result