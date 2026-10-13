"""
Утилиты для нормализации загружаемых изображений щенков.

Все фото карточек приводятся к единому размеру (cover-crop до 4:3),
чтобы сетка объявлений выглядела ровно — как на Avito.
"""
import io

from django.core.files.uploadedfile import InMemoryUploadedFile

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover
    Image = None
    ImageOps = None


# Целевой размер нормализованного фото (4:3)
TARGET_WIDTH = 1200
TARGET_HEIGHT = 900
JPEG_QUALITY = 85


def normalize_image(file, target_width=TARGET_WIDTH, target_height=TARGET_HEIGHT):
    """
    Приводит изображение к единому размеру: cover-crop до соотношения
    target_width x target_height и перекодирование в JPEG.

    Возвращает Django-совместимый файл (InMemoryUploadedFile) или исходный
    файл, если Pillow недоступен либо файл не является изображением.
    """
    if Image is None or file is None:
        return file

    try:
        file.seek(0)
        img = Image.open(file)
    except Exception:
        # не изображение — возвращаем как есть
        try:
            file.seek(0)
        except Exception:
            pass
        return file

    # Учитываем EXIF-ориентацию (фото с телефонов)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Прозрачность / палитра → белый фон, RGB
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background
    else:
        img = img.convert("RGB")

    # Cover-crop до целевого соотношения сторон и ресайз
    img = ImageOps.fit(
        img,
        (target_width, target_height),
        method=Image.LANCZOS,
        centering=(0.5, 0.5),
    )

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    buffer.seek(0)

    original_name = getattr(file, "name", "photo.jpg")
    base_name = original_name.rsplit(".", 1)[0] if "." in original_name else original_name
    new_name = f"{base_name}.jpg"

    return InMemoryUploadedFile(
        buffer,
        field_name="image",
        name=new_name,
        content_type="image/jpeg",
        size=buffer.getbuffer().nbytes,
        charset=None,
    )
