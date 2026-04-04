# dogs_module/config.py
"""
Конфигурация для парсеров Zooportal и BreedArchive.
Куки загружаются из переменных окружения (settings → .env).
"""

from django.conf import settings
from decouple import config

# =============================================================================
# ZOOPORTAL
# =============================================================================

ZOOPORTAL_BASE_URL  = "https://zooportal.pro"
ZOOPORTAL_DOG_PATH  = "/pedigree/view"
ZOOPORTAL_SEARCH_URL = f"{ZOOPORTAL_BASE_URL}/pedigree/"

# Логин для автообновления куков (+)
# Если ZOOPORTAL_PASSWORD задан → куки автоматически обновляются через Playwright
# Если не задан → используются ручные куки из переменных ниже (требуют замены каждые 24ч)
ZOOPORTAL_LOGIN    = config('ZOOPORTAL_LOGIN', default='')
ZOOPORTAL_PASSWORD = config('ZOOPORTAL_PASSWORD', default='')
ZOOPORTAL_LOGIN_URL = f"{ZOOPORTAL_BASE_URL}/auth/"  # Bitrix стандартный URL логина

# COOKIES (fallback если автологин не настроен)
ZOOPORTAL_COOKIES = {
    # ОСНОВНЫЕ (критичные для авторизации)
    'PHPSESSID': config('ZOOPORTAL_PHPSESSID', default=''),
    'BITRIX_SM_LOGIN': config('ZOOPORTAL_LOGIN', default=''),
    'BITRIX_SM_UIDH': config('ZOOPORTAL_BITRIX_SM_UIDH', default=''),
    'BITRIX_SM_UIDL': config('ZOOPORTAL_BITRIX_SM_UIDL', default=''),
    'BITRIX_SM_SALE_UID': config('ZOOPORTAL_SALE_UID', default=''),
    'BITRIX_SM_GUEST_ID': config('ZOOPORTAL_BITRIX_SM_GUEST_ID', default=''),

    # ДОПОЛНИТЕЛЬНЫЕ BITRIX
    'BITRIX_SM_NCC': config('ZOOPORTAL_BITRIX_SM_NCC', default=''),
    'BITRIX_SM_LAST_VISIT': config('ZOOPORTAL_BITRIX_SM_LAST_VISIT', default=''),
    'BITRIX_SM_SOUND_LOGIN_PLAYED': config('ZOOPORTAL_BITRIX_SM_SOUND_LOGIN_PLAYED', default=''),
    'BITRIX_SM_BANNERS': config('ZOOPORTAL_BITRIX_SM_BANNERS', default=''),
    'BITRIX_CONVERSION_CONTEXT_s1': config('ZOOPORTAL_CONVERSION_CONTEXT_s1', default=''),

    # J-КУКИ (антибот защита - КРИТИЧНО!)
    '__jhash_': config('ZOOPORTAL_JHASH', default=''),
    '__js_p_': config('ZOOPORTAL_JS_P', default=''),
    '__jua_': config('ZOOPORTAL_JUA', default=''),
    '__lhash_': config('ZOOPORTAL_LHASH', default=''),
    '__hash_': config('ZOOPORTAL_HASH', default=''),
}

# =============================================================================
# BREEDARCHIVE
# =============================================================================

BREEDARCHIVE_BASE_URL = "https://siberianhusky.breedarchive.com"
BREEDARCHIVE_SEARCH_RECENT_DOGS = f"{BREEDARCHIVE_BASE_URL}/ng_animal/get_entries"
BREEDARCHIVE_SEARCH_BY_NAME_URL = f"{BREEDARCHIVE_BASE_URL}/ng_animal/data"
BREEDARCHIVE_SEARCH_BROWSE = f"{BREEDARCHIVE_BASE_URL}/animal/browse"
BREEDARCHIVE_SEARCH_DOG_GET_ANCESTORS = f"{BREEDARCHIVE_BASE_URL}/animal/get_ancestors"
BREEDARCHIVE_SEARCH_DOG_BASE_NO_ANCESTORS = f"{BREEDARCHIVE_BASE_URL}/animal/get_animal"
BREEDARCHIVE_DOG_PATH = "/animal/view"
BREEDARCHIVE_USER = config('BREEDARCHIVE_USER', default='971')

# Логин для автообновления куков (+)
BREEDARCHIVE_EMAIL    = config('BREEDARCHIVE_EMAIL',    default='')
BREEDARCHIVE_PASSWORD = config('BREEDARCHIVE_PASSWORD', default='')
BREEDARCHIVE_LOGIN_URL = f"{BREEDARCHIVE_BASE_URL}/auth_user/login"
BREEDARCHIVE_COOKIES = {
    '__eoi': config('BREEDARCHIVE_EOIID', default=''),
    '__gads': config('BREEDARCHIVE_GADSID', default=''),
    '__gpi': config('BREEDARCHIVE_GPUID', default=''),
    '_ga': config('BREEDARCHIVE_GA', default=''),
    '_gid': config('BREEDARCHIVE_GID', default=''),
    'CookieSettings': config('BREEDARCHIVE_COOKIE_SETTINGS', default=''),
    'session_tba_v3': config('BREEDARCHIVE_SESSION_TBA_V3', default=''),
    '_ga_QHDN3K0CPK': config('BREEDARCHIVE_GA_SITE', default=''),
}
BREEDARCHIVE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    # 'User-Agent': (
    #     'Mozilla/5.0 (X11; Linux x86_64) '
    #     'AppleWebKit/537.36 (KHTML, like Gecko) '
    #     'Chrome/120.0.0.0 Safari/537.36'
    # ),
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ru',
    'X-REQUESTED-WITH': 'XMLHttpRequest',
    'Priority': 'u=3, i',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Connection': 'keep-alive',
    # 'oam_remote_user': BREEDARCHIVE_USER,
}
# =============================================================================
# PLAYWRIGHT
# =============================================================================

PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_TIMEOUT = 60000  # 60 секунд

PLAYWRIGHT_BROWSER_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-blink-features=AutomationControlled",
]

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.1 Safari/605.1.15"

# =============================================================================
# DELAYS & RETRIES
# =============================================================================

DELAY_BETWEEN_REQUESTS = (1.5, 3.0)
MAX_RETRIES = 3