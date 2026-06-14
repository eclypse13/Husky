# dogs_module/config/ofa.py
"""URL и заголовки OFA."""

API_URL = "https://api.ofa.org/api/as.php"
BB_URL = "https://api.ofa.org/api/bb.php"
BROWSE_BY_BREED_URL = "https://ofa.org/chic-programs/browse-by-breed/?breed="
BREED_CODE = "SH"

HEADERS = {
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

# Обратная совместимость
OFA_API_URL = API_URL
OFA_BB_URL = BB_URL
OFA_BROWSE_BY_BREED_CHOOSE_BREED_PATH = BROWSE_BY_BREED_URL
OFA_HEADERS = HEADERS
