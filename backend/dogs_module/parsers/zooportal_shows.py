"""
Парсер мероприятий Zooportal (выставки, выступления).
"""

import re
import logging
import time
from datetime import datetime
from typing import Optional, Dict, List, Any
from bs4 import BeautifulSoup

from ..config import ZOOPORTAL_BASE_URL
from .zooportal import BrowserManager

from ..config import (
    ZOOPORTAL_SHOW_LIST_URL,
    ZOOPORTAL_SHOW_RESULTS_URL,
    ZOOPORTAL_SHOW_THEMES,
    ZOOPORTAL_SHOW_FCI_5_GROUP_ID,
    ZOOPORTAL_SHOW_SH_BREED_ID,
)
from ..utils.text import parse_sex

logger = logging.getLogger(__name__)


# Возвращает список мероприятий с Zooportal для указанной даты и породы
def fetch_show_list(
        date_str: str,
        group_id: int = ZOOPORTAL_SHOW_FCI_5_GROUP_ID,
        breed_id: int = ZOOPORTAL_SHOW_SH_BREED_ID,
) -> list[dict]:
    """
    Возвращает list[dict]:
      {
        'zooportal_show_id': '17374482',
        'title': 'Выставка собак всех пород...',
        'event_date': '2026-01-18',  # ISO
        'organizer': 'ТООЛЖ',
        'address': '...',
        'city': 'Тюмень',
        'judges': 'Иванов; Петров',
        'status': 'Результаты',
        'rank': 'САС ЧРКФ',
      }
    """
    url = (
        f"{ZOOPORTAL_SHOW_LIST_URL}?"
        f"AJAX_CALL=N&APPLY=Y&RESET=N&DATE={date_str}"
        f"&f[THEMES]={ZOOPORTAL_SHOW_THEMES}"
        f"&f[GROUPS_OF_BREED]={group_id}"
        f"&f[BREEDS]={breed_id}"
        f"&f[TYPE_EVENT]=0&f[RANKS]=0&f[ORGANIZERS]=0"
        f"&f[COUNTRY]=0&f[REGION]=0&f[CITY]=0"
    )

    with BrowserManager() as browser:
        html = browser.fetch_page(url, wait_selector='.b1t-z-al-l')

    return _parse_show_list_html(html)


# Результаты собак на конкретной выставке.
def fetch_show_results(
        show_id: str,
        group_id: int = ZOOPORTAL_SHOW_FCI_5_GROUP_ID,
        breed_id: int = ZOOPORTAL_SHOW_SH_BREED_ID,
) -> list[dict]:
    """
    Возвращает dict:
      {
        'rank': 'КЧК',
        'results': [
          {
            'zooportal_dog_id': '16893363',
            'dog_name': 'KALORY WINNER ...',
            'registration_number': 'RKF 7255534',
            'owner_name': 'Химич',
            'catalog_number': 346,
            'request_id': '17487420',
            'sex': 1,
            'show_class': 'Юниоров',
            'grade': 'ОТЛ',
            'place': 1,
            'titles_won': 'R.JCAC, ЮСС',
          },
          ...
        ],
      }
    """
    url = (
        f"{ZOOPORTAL_SHOW_RESULTS_URL.format(show_id=show_id)}?"
        f"AJAX_CALL=N&apply=Y&reset=N"
        f"&F[GROUP]={group_id}"
        f"&F[BREED]={breed_id}"
        f"&F[NAME]=&F[CLASS]=&F[SEX]="
        f"&F[BREED_PARAMETER1]=&F[BREED_PARAMETER2]=&F[BREED_PARAMETER3]="
    )

    with BrowserManager() as browser:
        html = browser.fetch_page(url, wait_selector='.view-row.line')

    return _parse_show_results_html(html)


def fetch_show_rank(show_id: str) -> Optional[str]:
    return fetch_show_results(show_id).get('rank')

def _parse_show_list_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    results = []

    # Каждый city-box содержит organizer-блок и вложенные events
    city_boxes = soup.select('.b1t-z-al-l .city-box')
    if not city_boxes:
        # fallback ищем organizer напрямую
        city_boxes = soup.select('.b1t-z-al-l .organizer')

    for city_box in city_boxes:
        city_name = _text(city_box.select_one('.city a:last-of-type'))
        address = _text(city_box.select_one('.address-box .address'))

        organizer_blocks = city_box.select('.organizer')
        if not organizer_blocks:
            # city_box — сам organizer
            organizer_blocks = [city_box]

        for org_block in organizer_blocks:
            organizer = _text(org_block.select_one('.name'))
            status = _text(org_block.select_one('.status'))

            # Рейтинг звёзд (1–5)
            rating_stars = len(org_block.select('.icon-yellow'))

            events = org_block.select('.event')
            if not events:
                # events на том же уровне или в родителе
                parent = org_block.parent
                if parent:
                    events = parent.select('.event')

            for event in events:
                date_str_raw = _text(event.select_one('.dates'))
                name_tag = event.select_one('a.name')
                if not name_tag:
                    continue

                href = name_tag.get('href', '')
                show_id = _extract_show_id(href)
                if not show_id:
                    continue

                title = _text(name_tag)
                judges = _text(event.select_one('.experts'))
                rank = _extract_rank(title)

                results.append({
                    'zooportal_show_id': show_id,
                    'title': title,
                    'event_date': _parse_date(date_str_raw),
                    'organizer': organizer,
                    'address': address.strip() if address else None,
                    'city': city_name,
                    'judges': judges,
                    'status': status,
                    'rank': rank,
                    'rating_stars': rating_stars,
                })

    logger.info(f"Найдено {len(results)} мероприятий")
    logger.info(f"DICT HTML ZOOPORTAL_SHOW: {results}")
    return results


def _parse_show_results_html(html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')

    rows = soup.select('.view-row.line')
    rank = _extract_rank_from_provisions(soup)
    results = []

    current_sex = None
    current_show_class = None

    for row in rows:
        gender_cell = row.select_one('.view-cell.gender')
        if gender_cell:
            gender_text = _text(gender_cell.select_one('.text-ru') or gender_cell)
            current_sex = parse_sex(gender_text)

        class_cell = row.select_one('.view-cell.class')
        if class_cell:
            current_show_class = _text(class_cell.select_one('.text-ru') or class_cell)

        owner_cell = row.select_one('.view-cell.owner')
        if not owner_cell:
            continue

        dog_link = owner_cell.select_one('a[href*="/pedigree/view/"]')
        if not dog_link:
            continue

        zooportal_dog_id = _extract_dog_id(dog_link.get('href', ''))
        dog_name = _text(dog_link)

        logger.info(
            f"_parse_show_results_html: нашёл собаку {dog_name!r} "
            f"zoo_id={zooportal_dog_id!r} class={current_show_class!r}"
        )

        divs = [d for d in owner_cell.find_all('div', recursive=False)
                if not d.get('class')]
        owner_name = _text(divs[0]) if len(divs) > 0 else None
        reg_raw = _text(divs[1]) if len(divs) > 1 else None
        reg_number = reg_raw.strip() if reg_raw else None

        # Оценка и место: "ОТЛ, 1"
        assessment_text = _text(row.select_one('.result-assessment'))
        grade, place = _parse_assessment(assessment_text)

        # Титулы: "CW, CAC, ЧФ, СС"
        titles_el = row.select_one('.result-titles.hidden-xs') or row.select_one('.result-titles')
        titles_won = _text(titles_el)

        catalog_number = None
        num_cell = row.select_one('.view-cell.number')
        if num_cell:
            try:
                catalog_number = int(_text(num_cell))
            except (ValueError, TypeError):
                pass

        results.append({
            'zooportal_dog_id': zooportal_dog_id,
            'dog_name': dog_name,
            'registration_number': reg_number,
            'owner_name': owner_name,
            'catalog_number': catalog_number,
            'request_id': row.get('data-requestid'),
            'sex': current_sex,
            'show_class': current_show_class,
            'grade': grade,
            'place': place,
            'titles_won': titles_won or '',
        })

    logger.info(f"Найдено {len(results)} результатов")

    names = ', '.join(r['dog_name'] for r in results)
    logger.info(f"Найдено {len(results)} результатов: {names}")

    return {'results': results, 'rank': rank}

def _text(el) -> str:
    if el is None:
        return ''
    return el.get_text(separator=' ', strip=True)


def _extract_show_id(href: str) -> Optional[str]:
    m = re.search(r'/show/(\d+)/', href or '')
    return m.group(1) if m else None


def _extract_dog_id(href: str) -> Optional[str]:
    m = re.search(r'/pedigree/view/(\d+)/', href or '')
    return m.group(1) if m else None


def _parse_date(date_str: str) -> Optional[str]:
    if not date_str:
        return None
    for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def _parse_assessment(text: str):
    if not text:
        return None, None
    parts = [p.strip() for p in text.split(',')]
    grade = parts[0] if parts else None
    place = None
    if len(parts) >= 2:
        try:
            place = int(parts[1])
        except ValueError:
            pass
    return grade, place


def _extract_rank_from_provisions(soup: BeautifulSoup) -> Optional[str]:
    container = soup.select_one('.b1t-z-edv-c')
    if not container:
        return None
    for field in container.select('div.mt-10'):
        label = field.find(string=True, recursive=False)
        label = label.strip() if label else ''
        if label == 'Ранг':
            link = field.find('a')
            value = link.get_text(strip=True) if link else field.get_text(separator=' ', strip=True)
            return value or None
    return None

def _extract_rank(title: str) -> Optional[str]:
    if not title:
        return None
    for rank in ['CACIB', 'CAC ЧРКФ', 'САС ЧРКФ', 'CAC РКФ', 'Монопородная', 'Монопредная']:
        if rank.upper() in title.upper():
            return rank
    m = re.search(r'ранга?\s+([A-Za-zА-Яа-яЁё\s]+?)(?:\s*«|\s*\"|$)', title, re.IGNORECASE)
    if m:
        return m.group(1).strip()[:100]
    return None
