"""
Общие мелкие хелперы модуля собак.
"""

from typing import Optional


def best_dog_photo_url(dog) -> Optional[str]:
    """Ссылка для dog_photo: стабильный прокси на ЯД, иначе исходник."""
    if dog.photo_yadisk_path:
        return f"/api/dogs/photos/{dog.id}/raw/"
    return dog.photo_url or None
