# dogs_module/constants/ofa_fallback.py
"""
Fallback-статистика OFA для породы Siberian Husky.
Источник: ofa.org/diseases/statistics (данные 2023).

Используется в ofa_service._fallback_stats() когда OFA сайт недоступен.
"""

OFA_FALLBACK_STATS: dict = {
    "HIPS": {"total": 22568, "normal": 21963, "pct_normal": 97.3},
    "EYES": {"total": 15178, "normal": 14005, "pct_normal": 92.3},
    "ELBOW": {"total": 1690, "normal": 1687, "pct_normal": 99.8},
    "CARDIAC": {"total": 2897, "normal": 2815, "pct_normal": 97.2},
    "PATELLA": {"total": 1543, "normal": 1529, "pct_normal": 99.1},
    "THYROID": {"total": 892, "normal": 855, "pct_normal": 95.8},
    "DEGENERATIVE MYELOPATHY": {"total": 287, "normal": 279, "pct_normal": 97.2},
}
