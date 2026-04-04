# dogs_module/utils/cookie_refresher.py
"""
Автоматическое обновление куков для Zooportal и BreedArchive.

Алгоритм:
  get_*_cookies()  →  Redis HIT → вернуть
                   →  Redis MISS → залогиниться → сохранить → вернуть
                   →  логин упал → fallback к значениям из .env

  on_*_401()       →  удалить из Redis → залогиниться заново

  ВАЖНО: оба логина используют Playwright в ThreadPoolExecutor.
  Это необходимо потому что:
  - Zoo: _set_cookies вызывается изнутри BrowserManager.__enter__,
    где уже запущен sync_playwright() — вложенный вызов конфликтует через asyncio.
  - BA: логин через HTTP POST /auth_user/perform_login (формат как у axios на сайте).
  ThreadPoolExecutor даёт чистый тред без asyncio-loop, sync_playwright работает.

  Redis-лок гарантирует что при одновременном 401 у N воркеров
  реальный логин произойдёт только один раз.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_KEY_BA_COOKIES  = "auth:ba:cookies"
_KEY_ZOO_COOKIES = "auth:zoo:cookies"
_KEY_BA_LOCK     = "auth:ba:lock"
_KEY_ZOO_LOCK    = "auth:zoo:lock"
_COOKIE_TTL      = 20 * 3600  # 20ч — запас до истечения 24ч-сессии


# ── Redis helpers ─────────────────────────────────────────────────────────────

def _cache():
    """Alias 'parsers' — тот же что используется в cache.py."""
    from django.core.cache import caches
    return caches['parsers']


def _acquire_lock(key: str, ttl: int) -> bool:
    """cache.add() атомарен — стандартный Redis-лок без lua-скриптов."""
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
    """
    Запускает fn() в отдельном треде и возвращает результат.
    Нужно для sync_playwright — он требует чистый тред без asyncio event loop.
    """
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            logger.error(f"_run_in_thread timeout ({timeout}s): {fn.__name__}")
            return None


# ── BreedArchive ──────────────────────────────────────────────────────────────

def get_ba_cookies() -> Dict[str, str]:
    """Redis → автологин → .env fallback."""
    try:
        hit = _cache().get(_KEY_BA_COOKIES)
        if hit:
            return hit
    except Exception as e:
        logger.warning(f"BA cookies: Redis недоступен ({e}), fallback к .env")
        return _ba_env_cookies()

    fresh = _do_ba_login()
    return fresh if fresh else _ba_env_cookies()


def on_ba_401() -> None:
    """Вызывать в 401-ветках breedarchive.py."""
    logger.warning("BA 401 — инвалидируем куки, логинимся заново")
    try:
        _cache().delete(_KEY_BA_COOKIES)
    except Exception:
        pass
    _do_ba_login()


def _ba_env_cookies() -> Dict[str, str]:
    from ..config import BREEDARCHIVE_COOKIES
    cookies = {k: v for k, v in BREEDARCHIVE_COOKIES.items() if v}
    logger.warning(f"BA: fallback к .env ({len(cookies)} куков) — могут быть устаревшими")
    return cookies


def _do_ba_login() -> Optional[Dict[str, str]]:
    """Логин через Playwright в отдельном треде (избегаем конфликта asyncio)."""
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
        return _run_in_thread(_ba_playwright_login, timeout=120)
    finally:
        _release_lock(_KEY_BA_LOCK)


def _ba_playwright_login() -> Optional[Dict[str, str]]:
    """
    Выполняется в отдельном треде.

    Из HTML страницы BA видно что форма логина отправляет данные через
    axios POST /auth_user/perform_login с JSON {credentials: {username, password}}.
    Это можно сделать через requests без Playwright — быстрее и надёжнее.

    Шаги:
      1. GET /auth_user/login — получаем CSRF-куку и заголовки сессии
      2. POST /auth_user/perform_login — передаём credentials как JSON
      3. Из jar сессии забираем session_tba_v3
    """
    from ..config import (
        BREEDARCHIVE_BASE_URL, BREEDARCHIVE_EMAIL,
        BREEDARCHIVE_PASSWORD, BREEDARCHIVE_HEADERS,
    )
    import requests

    login_page_url   = f"{BREEDARCHIVE_BASE_URL}/auth_user/login"
    perform_login_url = f"{BREEDARCHIVE_BASE_URL}/auth_user/perform_login"

    logger.info("BA: HTTP логин через /auth_user/perform_login...")
    try:
        session = requests.Session()
        session.headers.update(BREEDARCHIVE_HEADERS)
        session.headers.update({
            'X-REQUESTED-WITH': 'XMLHttpRequest',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': BREEDARCHIVE_BASE_URL,
            'Referer': login_page_url,
        })

        # Шаг 1: GET страницы логина — получаем сессионные куки (CSRF и т.д.)
        r = session.get(login_page_url, timeout=30)
        if r.status_code != 200:
            logger.error(f"BA логин GET: HTTP {r.status_code}")
            return None

        # Шаг 2: POST credentials — формат как у axios в Vue-компоненте LoginTemplate
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
            logger.error(f"BA логин POST: HTTP {r2.status_code} — {r2.text[:300]}")
            return None

        # Проверяем ответ — Vue-компонент смотрит data.errorMessages
        try:
            resp_data = r2.json()
            if resp_data.get('errorMessages'):
                logger.error(f"BA логин: ошибка в ответе — {resp_data['errorMessages']}")
                return None
        except Exception:
            pass  # ответ не JSON — редирект, это ок

        fresh = dict(session.cookies)
        if not fresh.get('session_tba_v3'):
            logger.error(
                f"BA логин: session_tba_v3 не получена. "
                f"Куки в jar: {list(fresh.keys())}"
            )
            return None

        _cache().set(_KEY_BA_COOKIES, fresh, timeout=_COOKIE_TTL)
        logger.info(f"✅ BA: куки обновлены ({len(fresh)} шт.)")
        return fresh

    except Exception as e:
        logger.error(f"BA HTTP логин ошибка: {e}", exc_info=True)
        return None


# ── Zooportal ─────────────────────────────────────────────────────────────────

def get_zoo_cookies() -> Dict[str, str]:
    """Redis → автологин → .env fallback."""
    try:
        hit = _cache().get(_KEY_ZOO_COOKIES)
        if hit:
            return hit
    except Exception as e:
        logger.warning(f"Zoo cookies: Redis недоступен ({e}), fallback к .env")
        return _zoo_env_cookies()

    fresh = _do_zoo_login()
    return fresh if fresh else _zoo_env_cookies()


def on_zoo_session_expired() -> None:
    """Вызывать если обнаружен редирект на /auth/."""
    logger.warning("Zoo: сессия истекла — инвалидируем и логинимся заново")
    try:
        _cache().delete(_KEY_ZOO_COOKIES)
    except Exception:
        pass
    _do_zoo_login()


def _zoo_env_cookies() -> Dict[str, str]:
    from ..config import ZOOPORTAL_COOKIES
    cookies = {k: v for k, v in ZOOPORTAL_COOKIES.items() if v}
    logger.warning(f"Zoo: fallback к .env ({len(cookies)} куков) — могут быть устаревшими")
    return cookies


def _do_zoo_login() -> Optional[Dict[str, str]]:
    """Логин через Playwright в отдельном треде (избегаем конфликта с BrowserManager)."""
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
        return _run_in_thread(_zoo_playwright_login, timeout=120)
    finally:
        _release_lock(_KEY_ZOO_LOCK)


def _zoo_playwright_login() -> Optional[Dict[str, str]]:
    """Выполняется в отдельном треде. Логин через Bitrix-форму."""
    from ..config import (
        ZOOPORTAL_LOGIN_URL, ZOOPORTAL_LOGIN, ZOOPORTAL_PASSWORD,
        PLAYWRIGHT_HEADLESS, PLAYWRIGHT_BROWSER_ARGS, USER_AGENT,
    )
    from playwright.sync_api import sync_playwright

    logger.info("Zoo: Playwright логин (Bitrix)...")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=PLAYWRIGHT_HEADLESS, args=PLAYWRIGHT_BROWSER_ARGS)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080}, user_agent=USER_AGENT)
            page = context.new_page()
            try:
                page.goto(ZOOPORTAL_LOGIN_URL, wait_until='networkidle', timeout=60_000)
                page.fill('input[name="USER_LOGIN"]', ZOOPORTAL_LOGIN)
                page.fill('input[name="USER_PASSWORD"]', ZOOPORTAL_PASSWORD)
                page.click('input[type="submit"], button[type="submit"]')

                try:
                    page.wait_for_url(
                        lambda url: '/auth/' not in url,
                        timeout=20_000,
                    )
                except Exception:
                    page.wait_for_load_state('networkidle', timeout=20_000)

                fresh = {c['name']: c['value'] for c in context.cookies()}
            finally:
                page.close()
                context.close()
                browser.close()

        if not fresh.get('PHPSESSID'):
            logger.error(
                f"Zoo логин: PHPSESSID не получен. "
                f"URL={page.url}, куки={list(fresh.keys())}"
            )
            return None

        _cache().set(_KEY_ZOO_COOKIES, fresh, timeout=_COOKIE_TTL)
        logger.info(f"✅ Zoo: куки обновлены ({len(fresh)} шт.)")
        return fresh

    except Exception as e:
        logger.error(f"Zoo Playwright логин ошибка: {e}", exc_info=True)
        return None