"""Конфиг парсинга с BreedArchive."""
from decouple import config as _config

BASE_URL = "https://siberianhusky.breedarchive.com"
SEARCH_RECENT_DOGS = f"{BASE_URL}/ng_animal/get_entries"
SEARCH_BY_NAME_URL = f"{BASE_URL}/ng_animal/data"
SEARCH_BROWSE = f"{BASE_URL}/animal/browse"
SEARCH_DOG_GET_ANCESTORS = f"{BASE_URL}/animal/get_ancestors"
SEARCH_DOG_BASE_NO_ANCESTORS = f"{BASE_URL}/animal/get_animal"
DOG_PATH = "/animal/view"
LOGIN_URL = f"{BASE_URL}/auth_user/login"

USER = _config('BREEDARCHIVE_USER', default='971')
EMAIL = _config('BREEDARCHIVE_EMAIL', default='')
PASSWORD = _config('BREEDARCHIVE_PASSWORD', default='')

COOKIES = {
    '__eoi': _config('BREEDARCHIVE_EOIID', default=''),
    '__gads': _config('BREEDARCHIVE_GADSID', default=''),
    '__gpi': _config('BREEDARCHIVE_GPUID', default=''),
    '_ga': _config('BREEDARCHIVE_GA', default=''),
    '_gid': _config('BREEDARCHIVE_GID', default=''),
    'CookieSettings': _config('BREEDARCHIVE_COOKIE_SETTINGS', default=''),
    'session_tba_v3': _config('BREEDARCHIVE_SESSION_TBA_V3', default=''),
    '_ga_QHDN3K0CPK': _config('BREEDARCHIVE_GA_SITE', default=''),
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ru',
    'X-REQUESTED-WITH': 'XMLHttpRequest',
    'Priority': 'u=3, i',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Connection': 'keep-alive',
}

# Обратная совместимость
BREEDARCHIVE_BASE_URL = BASE_URL
BREEDARCHIVE_SEARCH_RECENT_DOGS = SEARCH_RECENT_DOGS
BREEDARCHIVE_SEARCH_BY_NAME_URL = SEARCH_BY_NAME_URL
BREEDARCHIVE_SEARCH_BROWSE = SEARCH_BROWSE
BREEDARCHIVE_SEARCH_DOG_GET_ANCESTORS = SEARCH_DOG_GET_ANCESTORS
BREEDARCHIVE_SEARCH_DOG_BASE_NO_ANCESTORS = SEARCH_DOG_BASE_NO_ANCESTORS
BREEDARCHIVE_DOG_PATH = DOG_PATH
BREEDARCHIVE_LOGIN_URL = LOGIN_URL
BREEDARCHIVE_USER = USER
BREEDARCHIVE_EMAIL = EMAIL
BREEDARCHIVE_PASSWORD = PASSWORD
BREEDARCHIVE_COOKIES = COOKIES
BREEDARCHIVE_HEADERS = HEADERS
