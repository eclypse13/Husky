"""
Единый источник правды для кодов здоровья OFA / FCI / российских ДНК-тестов.
"""

HIP_SCORES = {
    "EXCELLENT": 0, "GOOD": 1, "FAIR": 2,
    "BORDERLINE": 3, "MILD": 4, "MODERATE": 5, "SEVERE": 6,
}
ELBOW_SCORES = {
    "NORMAL": 0,
    "GRADE I": 1, "GRADE II": 2, "GRADE III": 3,
    "GRADE1": 1, "GRADE2": 2, "GRADE3": 3,
}
EYE_SCORES = {
    "NORMAL": 0, "NORMAL W/BO": 0,
    "AFFECTED": 1,
    "DOUBTFUL": 1,  # «подозрительно» — для безопасности считаем позитивом
}
GENETIC_SCORES = {
    "CLEAR/NORMAL": 0, "CLEAR": 0, "NORMAL/CLEAR": 0, "NORMAL": 0,
    "CARRIER": 1, "CARRIER-PROBABLE": 1,
    "AFFECTED": 2,
}
CARDIAC_SCORES = {
    "NORMAL": 0, "NORMAL-PRACTITIONER": 0,
    "NORMAL-CARDIOLOGIST": 0, "NORMAL AUSC+ECHO": 0,
    "ABNORMAL": 1,
}
BINARY_SCORES = {"NORMAL": 0, "ABNORMAL": 1}

REGISTRY_GROUPS = {
    "HIPS": "hips",
    "ELBOW": "elbows",
    "ELBOWS": "elbows",
    "EYES": "eyes",
    "CERF": "eyes",
    "SIBERIAN HUSKY OPTH. REGISTRY": "eyes",
    "PRIMARY LENS LUXATION": "pll", "PLL": "pll",
    "PROGRESSIVE RETINAL ATROPHY": "pra", "PRA": "pra",
    "PRA - CONE ROD DYSTROPHY 3": "pra",
    "EARLY ONSET PRA": "pra",
    "DEGENERATIVE MYELOPATHY": "dm", "DM": "dm",
    "JUVENILE LARYNGEAL PARALYSIS & POLYNEUROPATHY (LPP)": "lpp",
    "POLYNEUROPATHY": "lpp",
    "SIBERIAN HUSKY POLYNEUROPATHY": "lpp",
    "LPP": "lpp",
    "BASIC CARDIAC": "cardiac",
    "ADVANCED CARDIAC": "cardiac",
    "CONGENITAL CARDIAC": "cardiac",
    "THYROID": "thyroid",
    "PATELLA": "patella",
    # Справочные группы — сохраняются в БД, но в признаках модели не используются.
    "HYPERURICOSURIA": "huu", "HUU": "huu",
    "MALIGNANT HYPERTHERMIA": "mh", "MH": "mh",
    "MDR1": "mdr1",
    "MULTIPLE DRUG RESISTANCE": "mdr1",
}

GROUP_SCORES = {
    "hips": HIP_SCORES,
    "elbows": ELBOW_SCORES,
    "eyes": EYE_SCORES,
    "pll": GENETIC_SCORES,
    "pra": GENETIC_SCORES,
    "dm": GENETIC_SCORES,
    "lpp": GENETIC_SCORES,
    "cardiac": CARDIAC_SCORES,
    "thyroid": BINARY_SCORES,
    "patella": BINARY_SCORES,
    "huu": GENETIC_SCORES,
    "mh": GENETIC_SCORES,
    "mdr1": GENETIC_SCORES,
}

BINARY_GROUPS = {"cardiac", "thyroid", "patella"}

HIP_PROBLEM_THRESHOLD = 3
ELBOW_PROBLEM_THRESHOLD = 1
EYE_PROBLEM_THRESHOLD = 1
HIP_DYSPLASIA_THRESHOLD = HIP_PROBLEM_THRESHOLD


def classify_registry(registry: str) -> str | None:
    if not registry:
        return None
    return REGISTRY_GROUPS.get(registry.upper().strip())


def score_conclusion(group: str, conclusion: str) -> int | None:
    table = GROUP_SCORES.get(group)
    if table is None:
        return None
    c = (conclusion or "").upper().strip()
    if not c:
        return None
    if c in table:
        return table[c]
    if "CLEAR" in c or "NORMAL" in c:
        return 0
    if "CARRIER" in c:
        return 1
    if "AFFECTED" in c or "ABNORMAL" in c:
        return 2 if group in ("pra", "dm", "pll", "lpp", "huu", "mh", "mdr1") else 1
    if group in BINARY_GROUPS:
        return 1
    return None


def extract_scores(records: list[dict]) -> dict:
    by_group: dict[str, list[dict]] = {}
    for rec in records:
        group = classify_registry(rec.get("registry"))
        if not group:
            continue
        by_group.setdefault(group, []).append(rec)

    scores: dict[str, int] = {}
    for group, recs in by_group.items():
        latest = max(recs, key=lambda r: r.get("test_date") or "")
        score = score_conclusion(group, latest.get("conclusion"))
        if score is not None:
            scores[group] = score
    return scores
