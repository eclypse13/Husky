# dogs_module/parsers/breedarchive.py
"""
Парсер BreedArchive
"""

import re
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Set

from django.core.cache import caches
from playwright.sync_api import sync_playwright
import httpx

from ..config import (
    BREEDARCHIVE_COOKIES,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_BROWSER_ARGS,
    BREEDARCHIVE_HEADERS,
    BREEDARCHIVE_BASE_URL,
    BREEDARCHIVE_SEARCH_RECENT_DOGS,
    BREEDARCHIVE_SEARCH_BROWSE,
    BREEDARCHIVE_SEARCH_BY_NAME_URL,
    BREEDARCHIVE_SEARCH_DOG_GET_ANCESTORS,
    BREEDARCHIVE_SEARCH_DOG_BASE_NO_ANCESTORS,
)
from ..utils.text import (
    normalize_name_title_case,
    remove_titles_from_name,
    transliterate_ru_to_en,
    transliterate_en_to_ru,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# КЕШ
# ══════════════════════════════════════════════════════════════════════════════

_NOT_FOUND       = "__NOT_FOUND__"  # маркер «спрашивали — не нашли»
_TTL_NAME_SEARCH = 2 * 24 * 3600       # 24ч  — UUID по имени
_TTL_DOG_DATA    = 7 * 24 * 3600   # 7д   — полные данные собаки
_TTL_BASIC_DATA  = 2 * 24 * 3600    # 24ч  — базовые данные


def _cache():
    """
    Redis-кеш 'parsers' (DB 2).
    Функция, не константа — гарантирует что Django settings уже загружены.
    IGNORE_EXCEPTIONS=True → при сбое Redis работаем без кеша.
    """
    return caches['parsers']


def _key_name(name_upper: str) -> str:
    return f"ba:name:{name_upper}"


def _key_dog(uuid: str) -> str:
    return f"ba:dog:{uuid}"


def _key_basic(uuid: str) -> str:
    return f"ba:basic:{uuid}"


# ══════════════════════════════════════════════════════════════════════════════
# HTTP КЛИЕНТ — КУКИ + ЗАГОЛОВКИ
# ══════════════════════════════════════════════════════════════════════════════

def _create_session() -> requests.Session:
    """
    Создаёт HTTP-сессию с куками и заголовками для BreedArchive.

    КУКИ берутся из config.py → BREEDARCHIVE_COOKIES → .env
    Главная кука: session_tba_v3 — авторизация в BA.
    Без неё API возвращает 401.
    """
    from ..utils.cookie_refresher import get_ba_cookies
    session = requests.Session()
    cookies = get_ba_cookies()
    session.cookies.update(cookies)
    session.headers.update(BREEDARCHIVE_HEADERS)
    logger.debug(f"BA session: {len(cookies)} куков передано")
    return session


def _create_ba_client() -> httpx.Client:
    from ..utils.cookie_refresher import get_ba_cookies
    cookies = get_ba_cookies()
    return httpx.Client(
        headers=BREEDARCHIVE_HEADERS,
        cookies=cookies,
        timeout=30.0,
        follow_redirects=True,
    )


def _build_photo_url(photo_path: Optional[str]) -> Optional[str]:
    """Строит полный URL фото из относительного пути BreedArchive."""
    if not photo_path:
        return None
    return f"https://siberianhusky.breedarchive.com/resource/{photo_path}"


# ══════════════════════════════════════════════════════════════════════════════
# ПОИСК ПО ИМЕНИ — ВАРИАНТЫ
# ══════════════════════════════════════════════════════════════════════════════

def _build_search_variants(name: str) -> List[str]:
    """
    Строит список вариантов имени для поиска в BA.

    Порядок: имя без титулов → RU→EN транслит → EN→RU транслит.
    Дубликаты удаляются с сохранением порядка.
    """
    base = normalize_name_title_case(name.strip())
    without_titles = remove_titles_from_name(base)

    variants = []

    # 1. Имя без титулов (основной вариант)
    if without_titles:
        variants.append(without_titles)

    # 2. Транслитерация RU → EN (если есть кириллица)
    if any('\u0400' <= c <= '\u04ff' for c in base):
        en = normalize_name_title_case(transliterate_ru_to_en(without_titles or base))
        if en:
            variants.append(en)

    # 3. Транслитерация EN → RU (если есть латиница)
    if any('a' <= c.lower() <= 'z' for c in base):
        ru = normalize_name_title_case(transliterate_en_to_ru(without_titles or base))
        if ru:
            variants.append(ru)

    # Дедупликация с сохранением порядка
    seen, result = set(), []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# ПОИСК ПО ИМЕНИ → UUID
# ══════════════════════════════════════════════════════════════════════════════

def search_breedarchive_by_name(dog_name: str) -> Optional[str]:
    """
    Ищет собаку в BreedArchive по имени, возвращает UUID или None.

    АЛГОРИТМ:
      1. Проверяем кеш ba:name:{NAME}
      2. Строим варианты имени (без титулов, RU→EN, EN→RU)
      3. Для каждого варианта делаем GET /ng_animal/data?registered_name=...
      4. Берём records[0].uuid при первом успешном результате
      5. Кешируем UUID или _NOT_FOUND

    КЕШ: ba:name:{NAME_UPPER}, TTL=24ч
    """
    if not dog_name or not isinstance(dog_name, str):
        return None

    cache_key_name = dog_name.strip().upper()
    c = _cache()
    key = _key_name(cache_key_name)

    cached = c.get(key)
    if cached is not None:
        if cached == _NOT_FOUND:
            logger.debug(f"🎯 BA name MISS (кешировано): {cache_key_name}")
            return None
        logger.info(f"🎯 BA name HIT: {cache_key_name} → {cached}")
        return cached

    variants = _build_search_variants(dog_name)
    if not variants:
        return None

    logger.info(f"🔍 BA поиск: '{dog_name}' → варианты: {variants}")

    client = _create_ba_client()

    try:
        for variant in variants:
            try:
                params = {
                    'registered_name': variant.strip(),
                    'start': 0,
                    'order_column': 'registeredName',
                    'order_asc': 'true',
                }

                response = client.get(BREEDARCHIVE_SEARCH_BY_NAME_URL, params=params)

                if response.status_code == 401:
                    from ..utils.cookie_refresher import on_ba_401
                    on_ba_401()
                    logger.error(f"❌ BA: 401 для '{variant}' — куки обновлены, повторите запрос")
                    break

                if response.status_code != 200:
                    logger.warning(
                        f"  BA: статус {response.status_code} для '{variant}' "
                        f"(тело: {response.text[:150]})"
                    )
                    continue

                data = response.json()
                records = data.get('records', [])

                if not records:
                    logger.debug(f"  BA: '{variant}' → пусто")
                    continue

                logger.debug(f"  BA: '{variant}' → {len(records)} результатов")

                for record in records:
                    api_name = (record.get('registeredName') or '').strip()
                    uuid = record.get('uuid')
                    if uuid and api_name.upper() == variant.upper():
                        logger.info(f"✅ BA: UUID={uuid} точное '{api_name}'")
                        c.set(key, uuid, timeout=_TTL_NAME_SEARCH)
                        return uuid

                # Нет точного — первый результат
                first_uuid = records[0].get('uuid')
                first_name = records[0].get('registeredName', '?')
                if first_uuid:
                    logger.info(
                        f"✅ BA: UUID={first_uuid} первый '{first_name}' "
                        f"(запрос: '{variant}')"
                    )
                    c.set(key, first_uuid, timeout=_TTL_NAME_SEARCH)
                    return first_uuid

            except httpx.RequestError as e:
                logger.warning(f"  BA: сетевая ошибка для '{variant}': {e}")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"  BA: ошибка для '{variant}': {e}")
    finally:
        client.close()

    logger.info(f"❌ BA: '{dog_name}' не найдена")
    c.set(key, _NOT_FOUND, timeout=_TTL_NAME_SEARCH)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ПОЛУЧЕНИЕ ПОЛНЫХ ДАННЫХ ПО UUID (с предками, 5 поколений)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_breedarchive_dog(uuid: str, generations: int = 5) -> Optional[Dict]:
    """
    Получает полные данные собаки из BA: предки, владельцы, заводчики, титулы.
    Endpoint: GET /animal/get_ancestors/{uuid}?generations=5

    ВСЕГДА запрашиваем generations=5 (максимум) — кешируем полный результат.

    КЕШ: ba:dog:{uuid}, TTL=7д
    """
    c = _cache()
    key = _key_dog(uuid)

    cached = c.get(key)
    if cached is not None:
        logger.info(f"🎯 BA dog HIT: {uuid} ({cached.get('registered_name', '?')})")
        return cached

    logger.info(f"📄 BA: загрузка uuid={uuid}")
    session = _create_session()

    try:
        response = session.get(
            # f"{BREEDARCHIVE_BASE_URL}/animal/get_ancestors/{uuid}",
            f"{BREEDARCHIVE_SEARCH_DOG_GET_ANCESTORS}/{uuid}",
            params={'generations': generations},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if not data or 'uuid' not in data:
            logger.error(f"❌ BA: пустой/некорректный ответ для uuid={uuid}")
            return None

        # logger.info(f"✅ BA: получены данные '{data}'")
        logger.info(f"✅ BA: получены данные Имя'{data.get('registeredName') or data.get('registered_name', '?')}'")
        c.set(key, data, timeout=_TTL_DOG_DATA)
        return data

    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else '?'
        if code == 404:
            logger.warning(f"⚠️ BA: uuid={uuid} не найден (404)")
        elif code == 401:
            from ..utils.cookie_refresher import on_ba_401
            on_ba_401()
            logger.error(f"❌ BA: 401 — куки обновлены, uuid={uuid}")
        else:
            logger.error(f"❌ BA: HTTP {code} для uuid={uuid}")
        return None
    except Exception as e:
        logger.error(f"❌ BA: ошибка для uuid={uuid}: {e}")
        return None


def _collect_leaf_uuids(node: Dict, leaves: Set[str]) -> None:
    """
    Рекурсивно обходит дерево предков и собирает UUID «граничных» узлов.

    «Граничный» узел — тот, у которого:
      - есть uuid (значит можем запросить его предков отдельно)
      - sire и/или dam = None, но sireId / damId > 0
        (родитель существует в BA, просто не вошёл в текущий ответ из-за лимита 5 поколений)

    Именно для таких узлов нужно делать дополнительный запрос get_ancestors/{uuid}.
    """
    if not isinstance(node, dict):
        return

    uuid = node.get('uuid')
    sire_cut = node.get('sire') is None and (node.get('sireId') or 0) > 0
    dam_cut = node.get('dam') is None and (node.get('damId') or 0) > 0

    if uuid and (sire_cut or dam_cut):
        # Этот узел — граница: его родители известны BA, но не пришли в ответе.
        # Добавляем uuid узла в очередь на отдельный запрос.
        leaves.add(uuid)
        # Не идём глубже — сам узел будет запрошен отдельно.
        return

    # Если родители пришли — рекурсивно проверяем их тоже.
    if node.get('sire'):
        _collect_leaf_uuids(node['sire'], leaves)
    if node.get('dam'):
        _collect_leaf_uuids(node['dam'], leaves)

# ══════════════════════════════════════════════════════════════════════════════
# ПОЛУЧЕНИЕ БАЗОВЫХ ДАННЫХ ПО UUID (без предков — быстро)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_breedarchive_basic(uuid: str) -> Optional[Dict]:
    """
    Получает базовые данные собаки без дерева предков.
    Endpoint: GET /animal/get_animal/{uuid}?include_ancestors=false&generations=1

    КЕШ: ba:basic:{uuid}, TTL=24ч
    """
    c = _cache()
    key = _key_basic(uuid)

    cached = c.get(key)
    if cached is not None:
        logger.info(f"🎯 BA basic HIT: {uuid}")
        return cached

    logger.info(f"📋 BA basic: uuid={uuid}")
    session = _create_session()

    try:
        response = session.get(
            # f"{BREEDARCHIVE_BASE_URL}/animal/get_animal/{uuid}",
            f"{BREEDARCHIVE_SEARCH_DOG_BASE_NO_ANCESTORS}/{uuid}",
            params={'include_ancestors': False, 'generations': 1},
            timeout=30,
        )
        response.raise_for_status()
        raw = response.json()

        # Ответ может быть обёрнут в {'animal': {...}} или напрямую
        animal_data = raw.get('animal', raw)
        if not animal_data:
            logger.warning(f"⚠️ BA basic: нет данных для {uuid}")
            return None

        photo_path = animal_data.get('primary_photo_path') or animal_data.get('primaryPhotoPath')

        result = {
            'uuid': uuid,
            'registered_name':    animal_data.get('registered_name')    or animal_data.get('registeredName'),
            'link_name':          animal_data.get('link_name')          or animal_data.get('linkName'),
            'call_name':          animal_data.get('call_name')          or animal_data.get('callName'),
            'sex':                animal_data.get('sex'),
            'color':              animal_data.get('color'),
            'color_marking':      animal_data.get('color_marking')      or animal_data.get('colorMarking'),
            'variety':            animal_data.get('variety'),
            'year_of_birth':      animal_data.get('year_of_birth')      or animal_data.get('yearOfBirth'),
            'month_of_birth':     animal_data.get('month_of_birth')     or animal_data.get('monthOfBirth'),
            'day_of_birth':       animal_data.get('day_of_birth')       or animal_data.get('dayOfBirth'),
            'date_of_birth':      animal_data.get('date_of_birth'),
            'land_of_birth':      animal_data.get('land_of_birth')      or animal_data.get('landOfBirth'),
            'land_of_birth_code': animal_data.get('land_of_birth_code') or animal_data.get('landOfBirthCode'),
            'land_of_standing':   animal_data.get('land_of_standing')   or animal_data.get('landOfStanding'),
            'prefix_titles':      animal_data.get('prefix_titles')      or animal_data.get('prefixTitles'),
            'suffix_titles':      animal_data.get('suffix_titles')      or animal_data.get('suffixTitles'),
            'registration_number': animal_data.get('registration_number') or animal_data.get('registrationNumber'),
            'registration_status': animal_data.get('registration_status') or animal_data.get('registrationStatus'),
            'coi':                animal_data.get('coi'),
            'incomplete_pedigree': animal_data.get('incomplete_pedigree'),
            'primary_photo_path': photo_path,
            'photo_url':          _build_photo_url(photo_path),
            'neutered':           animal_data.get('neutered', False),
            'source':             'breedarchive.com',
        }

        result = {k: v for k, v in result.items() if v is not None}
        c.set(key, result, timeout=_TTL_BASIC_DATA)
        return result

    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else '?'
        logger.warning(f"⚠️ BA basic: HTTP {code} для {uuid}")
        return None
    except Exception as e:
        logger.error(f"❌ BA basic: ошибка для {uuid}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# ПОЛУЧЕНИЕ ПОСЛЕДНИХ ОБНОВЛЕНИЙ (operation=all)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_recent_dogs(
    pages_count: int = 1,
    start_page: int = 0,
    is_full_sync: bool = False,
) -> List[Dict]:
    """
    Получает список последних обновлённых/новых собак из BreedArchive.

    ENDPOINT: GET /ng_animal/get_entries?operation=all&start={N}
      - По 25 собак за раз (start=0, 25, 50, ..., 225)
      - Максимум 250 записей (start > 225 → нет новых данных)
      - data['has_more'] сигнализирует о продолжении

    ПАРАМЕТРЫ:
      pages_count  — количество страниц (1 стр = 25 собак)
      start_page   — с какой страницы начать (0–9)
      is_full_sync — True = грузим всё до has_more=False (максимум 250)

    ВОЗВРАЩАЕТ: List[Dict] — raw данные из API.
    """
    session = _create_session()
    start = start_page * 25
    all_animals: List[Dict] = []
    rows_fetched = 0

    logger.info(
        f"📡 BA recent: pages={pages_count}, start_page={start_page}, "
        f"full_sync={is_full_sync}"
    )

    while True:
        try:
            response = session.get(
                BREEDARCHIVE_SEARCH_RECENT_DOGS,
                params={'operation': 'all', 'start': start},
                timeout=30,
            )
            if response.status_code == 401:
                from ..utils.cookie_refresher import on_ba_401
                on_ba_401()
                logger.error("❌ BA recent: 401 — куки обновлены")
                break
            response.raise_for_status()
            data = response.json()
        except requests.HTTPError as e:
            logger.error(f"❌ BA recent: HTTP ошибка start={start}: {e}")
            break
        except Exception as e:
            logger.error(f"❌ BA recent: ошибка start={start}: {e}")
            break

        animals = data.get('animals', [])
        if not animals:
            logger.info("  BA recent: пустой ответ — завершаем")
            break

        all_animals.extend(animals)
        rows_fetched += len(animals)
        start += 25

        logger.info(
            f"  BA recent: получено {len(animals)}, всего={len(all_animals)}, "
            f"has_more={data.get('has_more')}"
        )

        has_more = data.get('has_more', False)
        if not has_more:
            break
        if not is_full_sync and rows_fetched >= pages_count * 25:
            break
        if start > 225:
            break

        time.sleep(0.5)

    logger.info(f"✅ BA recent: загружено {len(all_animals)} собак")
    return all_animals


# ══════════════════════════════════════════════════════════════════════════════
# ПАРСИНГ BROWSE-СТРАНИЦЫ ЧЕРЕЗ PLAYWRIGHT
# ══════════════════════════════════════════════════════════════════════════════

def parse_browse_page(recent_days: int = 1) -> Dict[str, Any]:
    """
    Парсит страницу /animal/browse через синхронный Playwright.

    ЗАЧЕМ PLAYWRIGHT:
      Browse — это SPA (KnockoutJS), данные грузятся динамически через JS.
      Обычный requests.get() вернёт пустой HTML без данных.

    АЛГОРИТМ:
      1. Открываем браузер, переходим на /animal/browse
      2. Ждём загрузки списка, для каждого элемента извлекаем данные
      3. Если modified_at < cutoff_date → стоп (данные упорядочены по дате)
      4. Для каждой собаки → fetch_breedarchive_dog(uuid) для полных данных
      5. Кликаем «Show more» если есть, повторяем

    ПАРАМЕТРЫ:
      recent_days — сколько последних дней обрабатывать (1–30)
    """
    dogs_data: List[Dict] = []
    failed: List[Dict] = []
    total_processed = 0
    page_count = 0
    cutoff_date = datetime.now() - timedelta(days=recent_days)

    logger.info(
        f"🌐 BA browse: recent_days={recent_days}, "
        f"cutoff={cutoff_date.strftime('%Y-%m-%d %H:%M')}"
    )

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=PLAYWRIGHT_HEADLESS,
                args=PLAYWRIGHT_BROWSER_ARGS,
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=(
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.1 Safari/605.1.15'
                ),
            )
            from ..utils.cookie_refresher import get_ba_cookies
            ba_cookies = get_ba_cookies()
            if ba_cookies:
                context.add_cookies([
                    {
                        'name': name, 'value': value,
                        'domain': 'siberianhusky.breedarchive.com',
                        'path': '/',
                    }
                    for name, value in ba_cookies.items() if value
                ])
            page = context.new_page()

            try:
                logger.info(f"  Переход: {BREEDARCHIVE_SEARCH_BROWSE}")
                page.goto(BREEDARCHIVE_SEARCH_BROWSE, wait_until='networkidle', timeout=60000)

                try:
                    page.wait_for_function(
                        """() => {
                            const el = document.querySelector('[data-bind]');
                            return el !== null && document.querySelector('.itemBox') !== null;
                        }""",
                        timeout=30000,
                    )
                except Exception:
                    # Если не дождались — логируем data-bind для диагностики
                    import re
                    html = page.content()
                    data_binds = re.findall(r'data-bind="[^"]{0,100}"', html)
                    logger.warning(f"  KO не инициализировался. data-bind: {data_binds[:10]}")

                page.wait_for_timeout(2000)
                elements = page.query_selector_all('.itemBox')
                if not elements:
                    # Пробуем другой селектор
                    elements = page.query_selector_all('[class*="itemBox"]')

                has_more_pages = True

                while has_more_pages:
                    page_count += 1
                    logger.info(f"  Browse стр.{page_count}")

                    page.wait_for_selector(
                        '.itemBox.fullProfile.resultProfile.profileDetails',
                        timeout=10000,
                    )

                    elements = page.query_selector_all(
                        '.itemBox.fullProfile.resultProfile.profileDetails'
                    )
                    logger.info(f"  Найдено элементов: {len(elements)}")

                    should_stop = False

                    for i, element in enumerate(elements):
                        try:
                            dog_info = _extract_browse_element(element)
                            if not dog_info:
                                continue

                            modified_str = dog_info.get('modified_at', '')
                            if modified_str:
                                try:
                                    modified_dt = datetime.strptime(
                                        modified_str, "%d/%m/%Y, %H:%M"
                                    )
                                    if modified_dt < cutoff_date:
                                        logger.info(
                                            f"  Стоп: {dog_info.get('registered_name')} "
                                            f"— {modified_dt} < cutoff"
                                        )
                                        should_stop = True
                                        break
                                except ValueError:
                                    pass

                            uuid = dog_info.get('uuid')
                            if not uuid:
                                failed.append({
                                    'name': dog_info.get('registered_name'),
                                    'error': 'UUID не найден',
                                })
                                continue

                            full_data = fetch_breedarchive_dog(uuid)
                            if full_data:
                                full_data['modified_at'] = dog_info.get('modified_at')
                                full_data['is_new'] = dog_info.get('is_new', False)
                                dogs_data.append(full_data)
                                status = "🆕 новая" if dog_info.get('is_new') else "🔄 обновлена"
                                logger.info(f"  ✅ {status}: {dog_info.get('registered_name', '?')}")
                            else:
                                failed.append({
                                    'name': dog_info.get('registered_name'),
                                    'uuid': uuid,
                                    'error': 'API не вернул данные',
                                })

                            total_processed += 1
                            time.sleep(0.5)

                        except Exception as e:
                            logger.error(f"  Ошибка элемента {i}: {e}")

                    if should_stop:
                        break

                    show_more = page.query_selector(
                        '[data-bind="visible: showLoadMore() && !loading(), '
                        'click: loadMore"].standardButton.alternative.showMore'
                    )
                    if show_more and show_more.is_visible():
                        logger.info("  Browse: клик 'Show more'")
                        show_more.click()
                        page.wait_for_timeout(2000)
                        try:
                            page.wait_for_selector(
                                '[data-bind="visible: loading()"]',
                                state='hidden',
                                timeout=10000,
                            )
                        except Exception:
                            pass
                    else:
                        logger.info("  Browse: больше данных нет")
                        has_more_pages = False

            finally:
                browser.close()

        logger.info(
            f"✅ BA browse: обработано={total_processed}, "
            f"успешно={len(dogs_data)}, ошибок={len(failed)}"
        )
        return {
            'status': 'success',
            'dogs': dogs_data,
            'total_processed': total_processed,
            'total_saved': len(dogs_data),
            'failed': failed,
            'pages_processed': page_count,
        }

    except Exception as e:
        logger.error(f"❌ BA browse критическая ошибка: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'dogs': dogs_data,
            'total_processed': total_processed,
            'failed': failed,
            'pages_processed': page_count,
        }


def _extract_browse_element(element) -> Optional[Dict[str, Any]]:
    """Извлекает данные о собаке из одного DOM-элемента browse-страницы."""
    try:
        link = element.query_selector('a.profilePhoto')
        if not link:
            return None

        href = link.get_attribute('href') or ''
        uuid_match = re.search(
            r'-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$',
            href
        )
        if not uuid_match:
            return None
        uuid = uuid_match.group(1)
        link_name = href.split('/')[-1].replace(f'-{uuid}', '')

        name_el = element.query_selector(
            '.registeredNameLink span[data-bind="text: registered_name"]'
        )
        registered_name = name_el.text_content().strip() if name_el else None

        prefix_el = element.query_selector('.prefixTitles')
        prefix_titles = prefix_el.text_content().strip() if prefix_el else None

        suffix_el = element.query_selector('.suffixTitles')
        suffix_titles = suffix_el.text_content().strip() if suffix_el else None

        male_icon = element.query_selector('.icon-male')
        female_icon = element.query_selector('.icon-female')
        sex = None
        if male_icon and male_icon.is_visible():
            sex = 1
        elif female_icon and female_icon.is_visible():
            sex = 2

        sire_name = dam_name = None
        parents_el = element.query_selector('.italic')
        if parents_el:
            spans = parents_el.query_selector_all('span')
            if len(spans) >= 3:
                sire_name = spans[0].text_content().strip()
                dam_name = spans[2].text_content().strip()

        color_el = element.query_selector('[data-bind="text: color"]')
        color = color_el.text_content().strip() if color_el else None

        land_of_birth = year_of_birth = None
        birth_el = element.query_selector(
            'div:has(span[data-bind="text: land_of_birth"])'
        )
        if birth_el:
            land_span = birth_el.query_selector('span[data-bind="text: land_of_birth"]')
            year_span = birth_el.query_selector(
                'span[data-bind="text: (year_of_birth != \'\' ? \' \' : \'\') + year_of_birth"]'
            )
            if land_span:
                land_of_birth = land_span.text_content().strip()
            if year_span:
                year_m = re.search(r'(\d{4})', year_span.text_content())
                if year_m:
                    year_of_birth = int(year_m.group(1))

        date_el = element.query_selector('.dateModified')
        modified_at = date_el.text_content().strip() if date_el else None

        ribbon = element.query_selector('.ribbon')
        is_new = ribbon is not None and ribbon.is_visible()

        return {
            'uuid': uuid,
            'link_name': link_name,
            'registered_name': registered_name,
            'prefix_titles': prefix_titles,
            'suffix_titles': suffix_titles,
            'sex': sex,
            'sire_name': sire_name,
            'dam_name': dam_name,
            'color': color,
            'land_of_birth': land_of_birth,
            'year_of_birth': year_of_birth,
            'modified_at': modified_at,
            'is_new': is_new,
        }

    except Exception as e:
        logger.error(f"❌ _extract_browse_element: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# ИНВАЛИДАЦИЯ КЕША
# ══════════════════════════════════════════════════════════════════════════════

def invalidate_name_cache(dog_name: str) -> None:
    """Сбрасывает кеш поиска по имени."""
    key = _key_name(dog_name.strip().upper())
    _cache().delete(key)
    logger.info(f"🗑️ Кеш удалён: {key}")


def invalidate_dog_cache(uuid: str) -> None:
    """Сбрасывает кеш полных данных собаки + флаг fully_parsed."""
    c = _cache()
    key = _key_dog(uuid)
    c.delete(key)
    # Сбрасываем Redis-флаг чтобы при следующем прогоне собака обновилась
    c.delete(f"ba:fully_parsed:{uuid}")
    logger.info(f"🗑️ Кеш удалён: {key} + fully_parsed флаг")


def invalidate_basic_cache(uuid: str) -> None:
    """Сбрасывает кеш базовых данных собаки."""
    key = _key_basic(uuid)
    _cache().delete(key)
    logger.info(f"🗑️ Кеш удалён: {key}")


def invalidate_all_caches(uuid: str, name: Optional[str] = None) -> None:
    """Сбрасывает ВСЕ кеши для собаки (полный переимпорт)."""
    invalidate_dog_cache(uuid)
    invalidate_basic_cache(uuid)
    if name:
        invalidate_name_cache(name)
    logger.info(f"🗑️ Все кеши сброшены для uuid={uuid}")