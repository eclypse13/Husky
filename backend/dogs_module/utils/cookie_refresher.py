# dogs_module/utils/cookie_refresher.py
"""
Автоматическое обновление куков для Zooportal и BreedArchive.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_KEY_BA_COOKIES = "auth:ba:cookies"
_KEY_ZOO_COOKIES = "auth:zoo:cookies"
_KEY_BA_LOCK = "auth:ba:lock"
_KEY_ZOO_LOCK = "auth:zoo:lock"
_COOKIE_TTL = 20 * 3600  # 20ч


# Redis helpers

def _cache():
    from django.core.cache import caches
    return caches['parsers']


def _acquire_lock(key: str, ttl: int) -> bool:
    try:
        return bool(_cache().add(key, "1", timeout=ttl))
    except Exception as e:
        logger.error(f"lock acquire [{key}]: {e}")
        return False


def _release_lock(key: str) -> None:
    try:
        _cache().delete(key)
    except Exception:
        pass


def _wait_for_lock_release(key: str, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if not _cache().get(key):
                return
        except Exception:
            return
        time.sleep(2)
    logger.warning(f"timeout ожидания лока [{key}]")


def _run_in_thread(fn, timeout: int):
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            logger.error(f"_run_in_thread timeout ({timeout}s): {fn.__name__}")
            return None


# BreedArchive

def get_ba_cookies() -> Dict[str, str]:
    """Redis → автологин → .env fallback."""
    try:
        hit = _cache().get(_KEY_BA_COOKIES)
        if hit:
            return hit
    except Exception as e:
        logger.warning(f"BA cookies: Redis недоступен ({e})")
        return _ba_env_cookies()

    fresh = do_ba_login()
    return fresh if fresh else _ba_env_cookies()


def on_ba_401() -> None:
    logger.warning("BA 401 — инвалидируем куки, логинимся заново")
    try:
        _cache().delete(_KEY_BA_COOKIES)
    except Exception:
        pass
    do_ba_login()


def _ba_env_cookies() -> Dict[str, str]:
    from ..config import BREEDARCHIVE_COOKIES
    cookies = {k: v for k, v in BREEDARCHIVE_COOKIES.items() if v}
    logger.warning(f"BA: fallback к .env ({len(cookies)} куков)")
    return cookies


def do_ba_login() -> Optional[Dict[str, str]]:
    from ..config import BREEDARCHIVE_EMAIL, BREEDARCHIVE_PASSWORD

    if not BREEDARCHIVE_EMAIL or not BREEDARCHIVE_PASSWORD:
        logger.error("BA: задайте BREEDARCHIVE_EMAIL и BREEDARCHIVE_PASSWORD в .env")
        return None

    if not _acquire_lock(_KEY_BA_LOCK, ttl=120):
        logger.info("BA: другой воркер логинится, ждём...")
        _wait_for_lock_release(_KEY_BA_LOCK)
        try:
            return _cache().get(_KEY_BA_COOKIES)
        except Exception:
            return None

    try:
        return _run_in_thread(_ba_http_login, timeout=60)
    finally:
        _release_lock(_KEY_BA_LOCK)


def _ba_http_login() -> Optional[Dict[str, str]]:
    """HTTP POST логин BA через /auth_user/perform_login."""
    from ..config import (
        BREEDARCHIVE_BASE_URL, BREEDARCHIVE_EMAIL,
        BREEDARCHIVE_PASSWORD, BREEDARCHIVE_HEADERS,
        BREEDARCHIVE_LOGIN_URL,
    )
    import requests

    perform_login_url = f"{BREEDARCHIVE_BASE_URL}/auth_user/perform_login"

    logger.info("BA: HTTP логин...")
    try:
        session = requests.Session()
        session.headers.update(BREEDARCHIVE_HEADERS)
        session.headers.update({
            'X-REQUESTED-WITH': 'XMLHttpRequest',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': BREEDARCHIVE_BASE_URL,
            'Referer': BREEDARCHIVE_LOGIN_URL,
        })

        r = session.get(BREEDARCHIVE_LOGIN_URL, timeout=30)
        if r.status_code != 200:
            logger.error(f"BA логин GET: HTTP {r.status_code}")
            return None

        payload = {
            "credentials": {
                "username": BREEDARCHIVE_EMAIL,
                "password": BREEDARCHIVE_PASSWORD,
                "termsofuseAccepted": False,
                "errors": {},
            }
        }
        r2 = session.post(perform_login_url, json=payload, timeout=30, allow_redirects=True)

        if r2.status_code not in (200, 302):
            logger.error(f"BA логин POST: HTTP {r2.status_code}")
            return None

        try:
            resp = r2.json()
            if resp.get('errorMessages'):
                logger.error(f"BA логин: ошибка — {resp['errorMessages']}")
                return None
        except Exception:
            pass

        fresh = dict(session.cookies)
        if not fresh.get('session_tba_v3'):
            logger.error(f"BA логин: session_tba_v3 не получена. Куки: {list(fresh.keys())}")
            return None

        _cache().set(_KEY_BA_COOKIES, fresh, timeout=_COOKIE_TTL)
        logger.info(f"✅ BA: куки обновлены ({len(fresh)} шт.)")
        return fresh

    except Exception as e:
        logger.error(f"BA HTTP логин ошибка: {e}", exc_info=True)
        return None


# Zooportal

def get_zoo_cookies() -> Dict[str, str]:
    """Redis → автологин → .env fallback."""
    try:
        hit = _cache().get(_KEY_ZOO_COOKIES)
        if hit:
            return hit
    except Exception as e:
        logger.warning(f"Zoo cookies: Redis недоступен ({e})")
        return _zoo_env_cookies()

    fresh = do_zoo_login()
    return fresh if fresh else _zoo_env_cookies()


def on_zoo_session_expired() -> None:
    logger.warning("Zoo: сессия истекла — инвалидируем и логинимся заново")
    try:
        _cache().delete(_KEY_ZOO_COOKIES)
    except Exception:
        pass
    do_zoo_login()


def _zoo_env_cookies() -> Dict[str, str]:
    from ..config import ZOOPORTAL_COOKIES
    cookies = {k: v for k, v in ZOOPORTAL_COOKIES.items() if v}
    logger.warning(f"Zoo: fallback к .env ({len(cookies)} куков)")
    return cookies


def do_zoo_login() -> Optional[Dict[str, str]]:
    """
    Сначала пробует HTTP логин (быстро),
    если не получил PHPSESSID — fallback на Playwright.
    """
    from ..config import ZOOPORTAL_LOGIN, ZOOPORTAL_PASSWORD

    if not ZOOPORTAL_LOGIN or not ZOOPORTAL_PASSWORD:
        logger.error("Zoo: задайте ZOOPORTAL_LOGIN и ZOOPORTAL_PASSWORD в .env")
        return None

    if not _acquire_lock(_KEY_ZOO_LOCK, ttl=120):
        logger.info("Zoo: другой воркер логинится, ждём...")
        _wait_for_lock_release(_KEY_ZOO_LOCK, timeout=90)
        try:
            return _cache().get(_KEY_ZOO_COOKIES)
        except Exception:
            return None

    try:
        # Сначала HTTP — быстро, без Playwright
        result = _run_in_thread(_zoo_http_login, timeout=60)
        if result and result.get('PHPSESSID'):
            return result

        logger.info("Zoo: HTTP не дал PHPSESSID, пробуем Playwright...")
        result = _run_in_thread(_zoo_playwright_login, timeout=120)
        return result

    finally:
        _release_lock(_KEY_ZOO_LOCK)


def _zoo_http_login() -> Optional[Dict[str, str]]:
    """
    HTTP POST логин Zooportal.
    Использует J-куки из .env для прохождения anti-bot защиты.
    """
    from ..config import (
        ZOOPORTAL_BASE_URL, ZOOPORTAL_LOGIN,
        ZOOPORTAL_PASSWORD, USER_AGENT,
        ZOOPORTAL_COOKIES, ZOOPORTAL_AUTH_PAGE_URL,
        ZOOPORTAL_AUTH_POST_URL,
    )
    import requests

    logger.info("Zoo: HTTP логин...")
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Origin': ZOOPORTAL_BASE_URL,
            'Referer': ZOOPORTAL_AUTH_PAGE_URL,
        })

        # GET — получаем начальные куки сервера
        r = session.get(ZOOPORTAL_AUTH_PAGE_URL, timeout=30)
        if r.status_code != 200:
            logger.error(f"Zoo HTTP GET: {r.status_code}")
            return None

        # Добавляем J-куки из .env — нужны для anti-bot проверки
        for key in ['__jhash_', '__js_p_', '__jua_', '__lhash_', '__hash_',
                    'BITRIX_SM_GUEST_ID', 'BITRIX_SM_NCC']:
            val = ZOOPORTAL_COOKIES.get(key, '')
            if val:
                session.cookies.set(key, val, domain='zooportal.pro')

        # POST формы
        payload = {
            'AUTH_FORM': 'Y',
            'TYPE': 'AUTH',
            'backurl': '/auth/?auth=yes',
            'USER_LOGIN': ZOOPORTAL_LOGIN,
            'USER_PASSWORD': ZOOPORTAL_PASSWORD,
            'USER_REMEMBER': 'Y',
            'Login': 'Войти',
        }
        r2 = session.post(ZOOPORTAL_AUTH_POST_URL, data=payload, timeout=30, allow_redirects=True)
        fresh = dict(session.cookies)

        if not fresh.get('PHPSESSID'):
            logger.warning(f"Zoo HTTP: PHPSESSID не получен. Куки: {list(fresh.keys())}")
            return None

        if fresh.get('BITRIX_SM_UIDH'):
            logger.info(f"✅ Zoo HTTP: полная авторизация ({len(fresh)} куков)")
        else:
            logger.info(f"✅ Zoo HTTP: сессия без UIDH ({len(fresh)} куков) — достаточно для парсинга")

        _cache().set(_KEY_ZOO_COOKIES, fresh, timeout=_COOKIE_TTL)
        return fresh

    except Exception as e:
        logger.error(f"Zoo HTTP логин ошибка: {e}", exc_info=True)
        return None


def _zoo_playwright_login() -> Optional[Dict[str, str]]:
    """
    Playwright логин Zooportal — fallback если HTTP не сработал.
    PHPSESSID достаточно для парсинга — BITRIX_SM_UIDH не обязателен.
    """
    from ..config import (
        ZOOPORTAL_LOGIN_URL, ZOOPORTAL_LOGIN, ZOOPORTAL_PASSWORD,
        PLAYWRIGHT_HEADLESS, PLAYWRIGHT_BROWSER_ARGS, USER_AGENT,
    )
    from playwright.sync_api import sync_playwright

    logger.info("Zoo: Playwright логин...")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=PLAYWRIGHT_HEADLESS,
                args=PLAYWRIGHT_BROWSER_ARGS,
            )
            context = browser.new_context(
                viewport={'width': 1440, 'height': 900},
                user_agent=USER_AGENT,
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                extra_http_headers={'Accept-Language': 'ru-RU,ru;q=0.9'},
            )
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )

            page = context.new_page()
            fresh = {}

            try:
                page.goto(ZOOPORTAL_LOGIN_URL, wait_until='load', timeout=60_000)
                page.wait_for_selector('form[name="form_auth"]', timeout=15_000)

                time.sleep(0.5)
                page.fill('input[name="USER_LOGIN"]', ZOOPORTAL_LOGIN)
                time.sleep(0.3)
                page.fill('input[name="USER_PASSWORD"]', ZOOPORTAL_PASSWORD)
                time.sleep(0.3)

                try:
                    with page.expect_navigation(wait_until='load', timeout=30_000):
                        page.click('input[name="Login"]')
                except Exception:
                    page.wait_for_timeout(3000)

                page.wait_for_timeout(1000)
                fresh = {c['name']: c['value'] for c in context.cookies()}

            finally:
                page.close()
                context.close()
                browser.close()

        if not fresh.get('PHPSESSID'):
            logger.error(f"Zoo Playwright: PHPSESSID не получен. Куки: {list(fresh.keys())}")
            return None

        if fresh.get('BITRIX_SM_UIDH'):
            logger.info(f"✅ Zoo Playwright: полная авторизация ({len(fresh)} куков)")
        else:
            logger.info(f"✅ Zoo Playwright: сессия без UIDH ({len(fresh)} куков)")

        _cache().set(_KEY_ZOO_COOKIES, fresh, timeout=_COOKIE_TTL)
        return fresh

    except Exception as e:
        logger.error(f"Zoo Playwright логин ошибка: {e}", exc_info=True)
        return None
