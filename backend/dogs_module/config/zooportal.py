"""Конфиг парсинга с Zooportal."""
from decouple import config as _config

BASE_URL = "https://zooportal.pro"
DOG_PATH = "/pedigree/view"
SEARCH_URL = f"{BASE_URL}/pedigree/"
SHOW_LIST_URL = f"{BASE_URL}/show/"
SHOW_RESULTS_URL = f"{BASE_URL}/show/results/{{show_id}}/"

AUTH_PAGE_URL = f"{BASE_URL}/auth/?auth=yes"
AUTH_POST_URL = f"{BASE_URL}/auth/?login=yes&auth=yes"
LOGIN_URL = f"{BASE_URL}/auth/"

LOGIN = _config('ZOOPORTAL_LOGIN', default='')
PASSWORD = _config('ZOOPORTAL_PASSWORD', default='')

COOKIES = {
    'PHPSESSID': _config('ZOOPORTAL_PHPSESSID', default=''),
    'BITRIX_SM_LOGIN': _config('ZOOPORTAL_LOGIN', default=''),
    'BITRIX_SM_UIDH': _config('ZOOPORTAL_BITRIX_SM_UIDH', default=''),
    'BITRIX_SM_UIDL': _config('ZOOPORTAL_BITRIX_SM_UIDL', default=''),
    'BITRIX_SM_SALE_UID': _config('ZOOPORTAL_SALE_UID', default=''),
    'BITRIX_SM_GUEST_ID': _config('ZOOPORTAL_BITRIX_SM_GUEST_ID', default=''),
    'BITRIX_SM_NCC': _config('ZOOPORTAL_BITRIX_SM_NCC', default=''),
    'BITRIX_SM_LAST_VISIT': _config('ZOOPORTAL_BITRIX_SM_LAST_VISIT', default=''),
    'BITRIX_SM_SOUND_LOGIN_PLAYED': _config('ZOOPORTAL_BITRIX_SM_SOUND_LOGIN_PLAYED', default=''),
    'BITRIX_SM_BANNERS': _config('ZOOPORTAL_BITRIX_SM_BANNERS', default=''),
    'BITRIX_CONVERSION_CONTEXT_s1': _config('ZOOPORTAL_CONVERSION_CONTEXT_s1', default=''),
    '__jhash_': _config('ZOOPORTAL_JHASH', default=''),
    '__js_p_': _config('ZOOPORTAL_JS_P', default=''),
    '__jua_': _config('ZOOPORTAL_JUA', default=''),
    '__lhash_': _config('ZOOPORTAL_LHASH', default=''),
    '__hash_': _config('ZOOPORTAL_HASH', default=''),
}

PHOTO_HEADERS = {
    "Referer": f"{BASE_URL}/pedigree/",
    "Origin": BASE_URL,
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Sec-Fetch-Dest": "image",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-origin",
}

# Обратная совместимость: старые имена
ZOOPORTAL_BASE_URL = BASE_URL
ZOOPORTAL_DOG_PATH = DOG_PATH
ZOOPORTAL_SEARCH_URL = SEARCH_URL
ZOOPORTAL_SHOW_LIST_URL = SHOW_LIST_URL
ZOOPORTAL_SHOW_RESULTS_URL = SHOW_RESULTS_URL
ZOOPORTAL_AUTH_PAGE_URL = AUTH_PAGE_URL
ZOOPORTAL_AUTH_POST_URL = AUTH_POST_URL
ZOOPORTAL_LOGIN_URL = LOGIN_URL
ZOOPORTAL_LOGIN = LOGIN
ZOOPORTAL_PASSWORD = PASSWORD
ZOOPORTAL_COOKIES = COOKIES
ZOOPORTAL_PHOTO_HEADERS = PHOTO_HEADERS
