"""Парсер породного рейтинга bestrussian.dog"""
import re
import logging
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from ..config import (
    BESTRUSSIAN_BASE_URL,
    BESTRUSSIAN_BREEDS_RATING_URL,
    SIBIRIAN_HUSKY_GROUP,
    BESTRUSSIAN_HEADERS,
)
logger = logging.getLogger(__name__)

def _find_husky_block_id(soup: BeautifulSoup) -> Optional[str]:
    """
    Находит value породы 'СИБИРСКИЙ ХАСКИ' из <select class="breedTabs">
    """
    select = soup.select_one("select.breedTabs")
    if not select:
        return None
    for option in select.select("option"):
        text = option.get_text(strip=True).upper()
        if "СИБИРСКИЙ" in text and "ХАСКИ" in text:
            return option.get("value")
    return None


def fetch_husky_breed_rating(year: int) -> List[Dict]:
    """
    Возвращает [{'position': 1, 'name': 'SIBERIEN ARABESQUE SNOW AMADEUS COSMOS', 'points': 37}, ...]
    Пустой список если данных на этот год нет
    """
    url = f"{BESTRUSSIAN_BREEDS_RATING_URL}?g={SIBIRIAN_HUSKY_GROUP}&y={year}"
    resp = requests.get(url, headers=BESTRUSSIAN_HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    block_id = _find_husky_block_id(soup)
    if not block_id:
        logger.warning(f"bestrussian: порода 'СИБИРСКИЙ ХАСКИ' не найдена в select (year={year})")
        return []

    block = soup.select_one(f"#breedsBlock_{block_id}")
    if not block:
        logger.info(f"bestrussian: breedsBlock_{block_id} пуст для year={year}")
        return []

    results = []
    for item in block.select(".item"):
        name_el = item.select_one(".name-breed-raiting")
        points_el = item.select_one(".price-breed-raiting")
        pos_el = item.select_one(".number-breed-raiting")
        if not name_el:
            continue
        points_text = points_el.get_text(strip=True) if points_el else ""
        results.append({
            "position": int(pos_el.get_text(strip=True)) if pos_el and pos_el.get_text(strip=True).isdigit() else None,
            "name": name_el.get_text(strip=True),
            "points": int(points_text) if points_text.isdigit() else None,
        })

    logger.info(f"bestrussian: year={year} — {len(results)} собак в рейтинге хаски")
    return results