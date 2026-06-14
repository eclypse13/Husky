# dogs_module/parsers/zooportal.py
"""
Парсер Zooportal — получение данных собак с zooportal.pro
"""

import re
import logging
import time
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from django.core.cache import caches

from ..config import (
    ZOOPORTAL_BASE_URL,
    ZOOPORTAL_DOG_PATH,
    ZOOPORTAL_SEARCH_URL,
    ZOOPORTAL_COOKIES,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_TIMEOUT,
    PLAYWRIGHT_BROWSER_ARGS,
    USER_AGENT,
)
from ..utils.text import normalize_dog_name

logger = logging.getLogger(__name__)

# Кеш
_TTL_SEARCH = 1 * 24 * 3600  # 24 часа
_TTL_DOG = 1 * 24 * 3600  # 24 часа


def _cache():
    """
    Возвращает Redis-кеш 'parsers' (DB 2).
    IGNORE_EXCEPTIONS=True → при недоступном Redis возвращает None,
    парсинг продолжается без кеша.
    """
    return caches['parsers']


def _key_search(page_num: int) -> str:
    return f"zoo:search:{page_num}"


def _key_dog(dog_id: str, generations: int) -> str:
    return f"zoo:dog:{dog_id}:{generations}"


# Менеджер браузера
class BrowserManager:
    """
    Контекстный менеджер для Playwright.
    """

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=PLAYWRIGHT_HEADLESS,
            args=PLAYWRIGHT_BROWSER_ARGS,
        )
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=USER_AGENT,
        )
        self._set_cookies()
        logger.info("🔓 Playwright открыт")
        return self

    def __exit__(self, *args):
        for obj, label, method in [
            (self.context, 'Context', 'close'),
            (self.browser, 'Browser', 'close'),
            (self.playwright, 'Playwright', 'stop'),
        ]:
            if obj:
                try:
                    getattr(obj, method)()
                except Exception as e:
                    logger.debug(f"{label} {method} error: {e}")
        self.context = self.browser = self.playwright = None
        logger.info("🔒 Playwright закрыт")

    def _recreate_context(self):
        """
        Пересоздаёт browser context после краша страницы.

        После 'Page crashed' / 'Target crashed' текущий context сломан —
        новые page.goto() в нём будут падать. Закрываем и создаём новый.
        Browser и playwright остаются живыми — только context пересоздаём.
        """
        if self.context:
            try:
                self.context.close()
            except Exception:
                pass
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=USER_AGENT,
        )
        self._set_cookies()

    def _set_cookies(self):
        from ..utils.cookie_refresher import get_zoo_cookies
        cookies = [
            {'name': name, 'value': value, 'domain': '.zooportal.pro', 'path': '/'}
            for name, value in get_zoo_cookies().items()
            if value
        ]
        if cookies:
            self.context.add_cookies(cookies)

    def fetch_page(self, url: str, retries: int = 5, wait_selector: Optional[str] = None) -> str:
        """
        Загружает HTML страницы через Playwright с retry и восстановлением после краша.
        """
        _CRASH_ERRORS = ('crashed', 'ERR_SSL', 'net::', 'Target closed')

        for attempt in range(retries):
            page = None
            try:
                page = self.context.new_page()
                logger.info(f"  [{attempt + 1}/{retries}] Загрузка: {url}")
                page.goto(url, wait_until='networkidle', timeout=PLAYWRIGHT_TIMEOUT)

                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=15000)
                        page.wait_for_function(
                            f"() => {{ const el = document.querySelector('{wait_selector}'); "
                            f"return el && el.innerText && el.innerText.trim().length > 0; }}",
                            timeout=10000,
                        )
                    except Exception as e:
                        # Таймаут селектора — не критично, страница загружена
                        logger.warning(f"  Селектор '{wait_selector}' не дождался: {e}")

                html = page.content()
                if not html or len(html) < 100:
                    raise RuntimeError(f"Пустой HTML ({len(html) if html else 0} байт)")
                return html

            except Exception as e:
                err_str = str(e)
                is_crash = any(c in err_str for c in _CRASH_ERRORS)

                if is_crash:
                    logger.error(
                        f"  💥 Краш браузера (попытка {attempt + 1}/{retries}): {err_str[:120]}"
                    )
                    # После краша context сломан — пересоздаём
                    try:
                        self._recreate_context()
                        logger.info("  ♻️  Контекст браузера пересоздан")
                    except Exception as re:
                        logger.error(f"  ❌ Не удалось пересоздать контекст: {re}")
                else:
                    logger.warning(
                        f"  ⚠️  Ошибка загрузки (попытка {attempt + 1}/{retries}): {err_str[:120]}"
                    )

                if attempt < retries - 1:
                    sleep_sec = 3 * (attempt + 1)  # 3с, 6с, 9с, 12с
                    logger.info(f"  ⏳ Пауза {sleep_sec}с перед следующей попыткой...")
                    time.sleep(sleep_sec)

            finally:
                # Закрываем page в любом случае — предотвращаем утечку
                if page:
                    try:
                        page.close()
                    except Exception:
                        pass  # После краша close() тоже может упасть
                    page = None

        raise RuntimeError(f"Не удалось загрузить {url} после {retries} попыток")

    def download_photo_bytes(self, photo_url: str) -> Optional[bytes]:
        """
        Скачивает фото Zoo через Playwright контекст (уже авторизован).
        Вызывается сразу после fetch_page — контекст с куками открыт.
        Возвращает bytes или None при ошибке.
        """
        if not photo_url:
            return None
        try:
            response = self.context.request.get(
                photo_url,
                headers={
                    "Referer": f"{ZOOPORTAL_BASE_URL}/pedigree/",
                    "Accept": "image/*,*/*;q=0.8",
                },
                timeout=30000,
            )
            if response.status != 200:
                logger.warning(f"Zoo photo: HTTP {response.status} для {photo_url}")
                return None
            if "text/html" in response.headers.get("content-type", ""):
                logger.warning(f"Zoo photo: вернул HTML для {photo_url}")
                return None
            body = response.body()
            logger.info(f"Zoo photo: скачано {len(body)}b для {photo_url}")
            return body
        except Exception as e:
            logger.warning(f"Zoo photo download error: {e}")
            return None


# ПАРСЕР ZOOPORTAL


class ZooportalParser:
    """Парсер Zooportal"""

    def parse_search_page_with_browser(
            self, browser: BrowserManager, page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Парсит страницу поиска Zooportal.

        Используется при retry задач: если задача упала после парсинга
        страницы, но до сохранения — повторный запуск не идёт в Playwright.
        """
        c = _cache()
        key = _key_search(page_num)

        cached = c.get(key)
        if cached is not None:
            logger.info(f"🎯 Zoo search HIT: page={page_num} ({len(cached)} собак)")
            return cached

        url = (
            f"{ZOOPORTAL_SEARCH_URL}"
            f"?bxajaxid=&AJAX_CALL=N&APPLY=Y&RESET=N"
            f"&RAND=0.5117462978400045"
            f"&FILTER_NAME=arrFilter"
            f"&KENNEL_ID=&SHORT=&OWNER="
            f"&F%5BNAME%5D=&F%5BNICKNAME%5D="
            f"&F%5BDOCUMENT%5D=0&F%5BDOCUMENT_NUMBER%5D="
            f"&F%5BSTAMP%5D="
            f"&F%5BTHEME%5D=1209"
            f"&F%5BSEX%5D=0"
            f"&F%5BBREED%5D=16747920"
            f"&F%5BBREED_PARAMETER1%5D=0"
            f"&F%5BBREED_PARAMETER2%5D=0"
            f"&F%5BBREED_PARAMETER3%5D=0"
            f"&F%5BCOUNTRY%5D=0&F%5BREGION%5D=0"
            f"&F%5BRAION%5D=0&F%5BCITY%5D=0&F%5BPUNKT%5D=0"
            f"&PAGEN_1={page_num}"
        )
        html = browser.fetch_page(url, wait_selector='span.item-wrapper')
        dogs = self._parse_search_html(html)

        if dogs:
            c.set(key, dogs, timeout=_TTL_SEARCH)
            logger.debug(f"💾 Кеш SET zoo:search:{page_num} ({len(dogs)} собак, TTL=30мин)")

        return dogs

    def parse_dog_page_with_browser(
            self, browser: BrowserManager, dog_id: str, generations: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Парсит страницу конкретной собаки.
        """
        c = _cache()
        key = _key_dog(dog_id, generations)

        cached = c.get(key)
        if cached is not None:
            logger.info(f"🎯 Zoo dog HIT: id={dog_id} "
                        f"({cached.get('registered_name', '?')})")
            return cached

        url = f"{ZOOPORTAL_BASE_URL}{ZOOPORTAL_DOG_PATH}/{dog_id}/?COUNT_GENERATIONS={generations}"
        # html = browser.fetch_page(url)
        html = browser.fetch_page(url, wait_selector='span.item-wrapper')
        data = self._parse_dog_html(html, dog_id)
        logger.info(f"💾 {data.get('registered_name')}")

        # Скачиваем фото сразу — пока Playwright контекст авторизован.
        # Zoo блокирует прямые запросы без сессии, через контекст работает.
        if data and data.get('photo_url'):
            photo_bytes = browser.download_photo_bytes(data['photo_url'])
            if photo_bytes:
                data['photo_bytes'] = photo_bytes
                logger.info(f"📷 Фото скачано при парсинге ({len(photo_bytes)}b)")

        if data and data.get('registered_name'):
            # Не кешируем photo_bytes — большие данные, не нужны при повторе
            cache_data = {k: v for k, v in data.items() if k != 'photo_bytes'}
            c.set(key, cache_data, timeout=_TTL_DOG)
            logger.debug(f"💾 Кеш SET zoo:dog:{dog_id}:{generations} "
                         f"({data['registered_name']}, TTL=6ч)")

        return data

    # ИНВАЛИДАЦИЯ

    def invalidate_dog_cache(self, dog_id: str, generations: int = 3) -> None:
        """Сбрасывает кеш страницы собаки. Вызывать если данные обновлены."""
        _cache().delete(_key_dog(dog_id, generations))
        logger.info(f"🗑️ Кеш удалён: zoo:dog:{dog_id}:{generations}")

    def invalidate_search_cache(self, page_num: int) -> None:
        """Сбрасывает кеш страницы поиска."""
        _cache().delete(_key_search(page_num))
        logger.info(f"🗑️ Кеш удалён: zoo:search:{page_num}")

    # ПАРСИНГ HTML

    def _parse_search_html(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        dogs = []

        wrappers = soup.find_all('span', class_='item-wrapper')
        for wrapper in wrappers:
            try:
                item = wrapper.find('div', class_='item')
                if not item or 'PRO-аккаунт' in str(item):
                    continue

                name_link = item.find('a', class_='name')
                if not name_link:
                    continue

                name = name_link.get_text(strip=True)
                href = name_link.get('href', '')

                match = re.search(r'/view/(\d+)/', href)
                if not match:
                    continue

                dog_id = match.group(1)
                item_classes = item.get('class', [])
                sex = 2 if 'red' in item_classes else 1 if 'blue' in item_classes else 0

                dogs.append({
                    'zooportal_id': dog_id,
                    'name': normalize_dog_name(name),
                    'sex': sex,
                    'url': f"{ZOOPORTAL_BASE_URL}{href}",
                })
            except Exception as e:
                logger.error(f"Ошибка парсинга элемента: {e}")

        logger.info(f"📊 Распарсено {len(dogs)} собак")
        return dogs

    def _parse_dog_html(self, html: str, dog_id: str) -> Optional[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')

        try:
            breeder_info = self._extract_breeder_info(soup)
            owner_info = self._extract_owner_info(soup)

            data = {
                'zooportal_id': dog_id,
                'registered_name': self._extract_name(soup),
                'call_name': self._extract_call_name(soup),
                'sex': self._extract_sex(soup),
                'color': self._extract_color(soup),
                'year_of_birth': self._extract_year(soup),
                'date_of_birth': self._extract_date_of_birth(soup),
                'land_of_birth': self._extract_country(soup),
                'registration_number': self._extract_reg_number(soup),
                'brand_chip': self._extract_brand_chip(soup),
                'photo_url': self._extract_photo(soup),
                'titles_text': self._extract_titles(soup),
                'titles': self._extract_titles_structured(soup),
                'breeder_name': breeder_info.get('name'),
                'breeder_url': breeder_info.get('url'),
                'breeder_kennel': breeder_info.get('kennel'),
                'breeder_kennel_url': breeder_info.get('kennel_url'),
                'owner_name': owner_info.get('name'),
                'owner_url': owner_info.get('url'),
                'owner_kennel': owner_info.get('kennel'),
                'owner_kennel_url': owner_info.get('kennel_url'),
                'pedigree': self._parse_pedigree(soup, dog_id),
            }

            logger.info(f"✅ Распарсена собака {dog_id}: {data.get('registered_name')}")
            return data
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {dog_id}: {e}")
            return None

    # ИЗВЛЕЧЕНИЕ ПОЛЕЙ

    def _extract_name(self, soup) -> Optional[str]:
        h1 = soup.find('h1')
        return normalize_dog_name(h1.get_text(strip=True)) if h1 else None

    def _extract_call_name(self, soup) -> Optional[str]:
        tag = soup.find('h2', class_='name_rus')
        return tag.get_text(strip=True) if tag else None

    def _extract_sex(self, soup) -> int:
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True).lower()
                if 'пол' in label:
                    return 2 if 'сука' in value else 1 if 'кобель' in value else 0
        return 0

    def _extract_color(self, soup) -> Optional[str]:
        for div in soup.find_all('div', class_='row2col'):
            ct = div.find('div', class_='col-text')
            cv = div.find('div', class_='col-value')
            if ct and 'окрас' in ct.get_text(strip=True).lower():
                return cv.get_text(strip=True) if cv else None
        return None

    def _extract_year(self, soup) -> Optional[int]:
        dob = self._extract_date_of_birth(soup)
        if dob:
            m = re.search(r'\d{4}', dob)
            if m:
                return int(m.group(0))
        return None

    def _extract_date_of_birth(self, soup) -> Optional[str]:
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                if 'дата рождения' in label and value:
                    return value
        return None

    def _extract_country(self, soup) -> Optional[str]:
        for div in soup.find_all('div', class_='row2col'):
            ct = div.find('div', class_='col-text')
            cv = div.find('div', class_='col-value')
            if ct and 'страна' in ct.get_text(strip=True).lower():
                return cv.get_text(strip=True) if cv else None
        return None

    def _extract_reg_number(self, soup) -> Optional[str]:
        for el in soup.find_all(string=lambda t: t and '№ родословной' in t):
            parent = el.parent
            if parent.name == 'td':
                next_td = parent.find_next_sibling('td')
                if next_td:
                    return next_td.get_text(strip=True)
        return None

    def _extract_brand_chip(self, soup) -> Optional[str]:
        parts = []
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                if ('клеймо' in label or 'чип' in label) and value:
                    parts.append(value)
        return ', '.join(parts) if parts else None

    def _extract_photo(self, soup) -> Optional[str]:
        fancybox = soup.find('a', class_='fancybox', rel='poto')
        if fancybox and fancybox.get('href'):
            href = fancybox['href']
            return f"{ZOOPORTAL_BASE_URL}{href}" if not href.startswith('http') else href
        img = soup.find('img', class_='photo')
        if img and img.get('src'):
            src = img['src']
            if 'resize_cache' in src:
                src = src.replace('resize_cache/', '').replace('/300_170_2/', '/')
            return f"{ZOOPORTAL_BASE_URL}{src}" if not src.startswith('http') else src
        return None

    def _extract_titles(self, soup) -> Optional[str]:
        tag = soup.find('div', class_='titles')
        return tag.get_text(strip=True) if tag else None

    def _extract_titles_structured(self, soup) -> List[Dict]:
        return []

    # BREEDER / OWNER

    def _extract_breeder_info(self, soup) -> Dict[str, Optional[str]]:
        info: Dict[str, Optional[str]] = {
            'name': None, 'url': None, 'kennel': None, 'kennel_url': None
        }
        for div in soup.find_all('div', class_='row2col'):
            ct = div.find('div', class_='col-text')
            cv = div.find('div', class_='col-value')
            if not ct or not cv:
                continue
            if ct.get_text(strip=True) != 'Заводчик:':
                continue
            link = cv.find('a')
            if link:
                info['name'] = link.get_text(strip=True)
                href = link.get('href', '')
                info['url'] = f"{ZOOPORTAL_BASE_URL}{href}" if href and not href.startswith('http') else href
            else:
                info['name'] = cv.get_text(strip=True)
            next_div = div.find_next_sibling('div', class_='row2col')
            if next_div:
                nct = next_div.find('div', class_='col-text')
                ncv = next_div.find('div', class_='col-value')
                if nct and nct.get_text(strip=True) == 'Питомник:' and ncv:
                    klink = ncv.find('a')
                    if klink:
                        info['kennel'] = klink.get_text(strip=True)
                        khref = klink.get('href', '')
                        info['kennel_url'] = f"{ZOOPORTAL_BASE_URL}{khref}" if khref and not khref.startswith(
                            'http') else khref
            break
        return info

    def _extract_owner_info(self, soup) -> Dict[str, Optional[str]]:
        info: Dict[str, Optional[str]] = {
            'name': None, 'url': None, 'kennel': None, 'kennel_url': None
        }
        for div in soup.find_all('div', class_='row2col'):
            ct = div.find('div', class_='col-text')
            cv = div.find('div', class_='col-value')
            if not ct or not cv:
                continue
            if ct.get_text(strip=True) != 'Владелец:':
                continue
            link = cv.find('a')
            if link:
                info['name'] = link.get_text(strip=True)
                href = link.get('href', '')
                info['url'] = f"{ZOOPORTAL_BASE_URL}{href}" if href and not href.startswith('http') else href
            else:
                info['name'] = cv.get_text(strip=True)
            next_div = div.find_next_sibling('div', class_='row2col')
            if next_div:
                nct = next_div.find('div', class_='col-text')
                ncv = next_div.find('div', class_='col-value')
                if nct and nct.get_text(strip=True) == 'Питомник:' and ncv:
                    klink = ncv.find('a')
                    if klink:
                        info['kennel'] = klink.get_text(strip=True)
                        khref = klink.get('href', '')
                        info['kennel_url'] = f"{ZOOPORTAL_BASE_URL}{khref}" if khref and not khref.startswith(
                            'http') else khref
            break
        return info

    # РОДОСЛОВНАЯ

    def _parse_pedigree(self, soup, dog_id: str) -> Dict[str, Any]:
        """
        Парсит таблицу родословной.

        ВОЗВРАЩАЕТ:
          ancestors:      dict {node_key: ancestor_data}
          relationships:  list [{child_key, parent_key, relation}]
          base_dogs:      dict {base_key: {zooportal_id}}
          parents:        {sire: data, dam: data}

        node_key = "{child_id}:{CODE}"   (напр. "12345:FATHER_MOTHER")
        base_key = "{child_id}:"         (напр. "12345:")

        ancestor_data['zooportal_id'] — это ID, который будет использоваться
        при рекурсивном парсинге. Если он есть — можно вызвать
        parse_dog_page_with_browser(browser, ancestor_data['zooportal_id'], gen)
        и получить полную информацию о предке (включая его родословную).
        """
        pedigree = {
            'parents': {'dam': None, 'sire': None},
            'ancestors': {},
            'relationships': [],
            'base_dogs': {},
        }

        pedigree_table = soup.find('table', class_='pedigree-table')
        if not pedigree_table:
            return pedigree

        cells = pedigree_table.find_all('td', attrs={'code': True, 'child_id': True})

        for cell in cells:
            try:
                code = (cell.get('code') or '').strip()
                child_id = (cell.get('child_id') or '').strip()
                if not code or not child_id:
                    continue

                base_key = f"{child_id}:"
                if base_key not in pedigree['base_dogs']:
                    pedigree['base_dogs'][base_key] = {'zooportal_id': child_id}

                if 'animal_parent_not_set' in str(cell):
                    continue

                name = self._extract_cell_name(cell)
                if not name:
                    continue

                last_segment = code.split('_')[-1]
                sex = 1 if last_segment == 'FATHER' else 2 if last_segment == 'MOTHER' else 0

                zooportal_id = None
                link = cell.find('a', href=True)
                if link:
                    href = link.get('href', '')
                    m = re.search(r'/pedigree/view/(\d+)/', href)
                    if m:
                        zooportal_id = m.group(1)

                raw_text = self._extract_cell_raw_text(cell)

                ancestor_data = {
                    'name': normalize_dog_name(name),
                    'sex': sex,
                    'zooportal_id': zooportal_id,
                    'guid': cell.get('guid'),
                    'raw_text': raw_text,
                    'code': code,
                    'child_id': child_id,
                }

                node_key = f"{child_id}:{code}"
                pedigree['ancestors'][node_key] = ancestor_data

                if child_id == str(dog_id) and code == 'FATHER':
                    pedigree['parents']['sire'] = ancestor_data
                elif child_id == str(dog_id) and code == 'MOTHER':
                    pedigree['parents']['dam'] = ancestor_data

                segments = code.split('_')
                parent_key = node_key
                child_code = '_'.join(segments[:-1])
                child_key = f"{child_id}:{child_code}"

                relation = (
                    'sire' if segments[-1] == 'FATHER'
                    else 'dam' if segments[-1] == 'MOTHER'
                    else None
                )
                if relation is None:
                    continue

                pedigree['relationships'].append({
                    'child_key': child_key,
                    'parent_key': parent_key,
                    'relation': relation,
                })

            except Exception as e:
                logger.error(f"Ошибка парсинга ячейки родословной: {e}")

        logger.info(
            f"  Pedigree parsed: {len(pedigree['ancestors'])} ancestors, "
            f"{len(pedigree['relationships'])} relationships, "
            f"{len(pedigree['base_dogs'])} base_dogs"
        )
        return pedigree

    def _extract_cell_name(self, cell) -> str:
        parent_input = cell.find('input', {'name': 'PARENT'})
        if parent_input and parent_input.get('value'):
            return parent_input['value'].strip()
        link = cell.find('a')
        if link:
            return link.get_text(strip=True)
        info = cell.find('div', class_='animal-info')
        if info:
            return info.get_text(' ', strip=True).strip()
        return ''

    def _extract_cell_raw_text(self, cell) -> str:
        infos = cell.find_all('div', class_='animal-info')
        if not infos:
            return ''
        return ' '.join([d.get_text(' ', strip=True) for d in infos]).strip()


# Глобальный экземпляр
zooportal_parser = ZooportalParser()
