/**
 * Сжатие фотографий в браузере перед загрузкой.
 *
 * Оригиналы с телефона весят по несколько МБ; несколько таких фото в одном
 * multipart-запросе пробивают лимиты (nginx client_max_body_size, таймаут
 * gunicorn) и запрос обрывается ещё до ответа сервера ("Failed to fetch").
 *
 * Уменьшаем по большей стороне и перекодируем в JPEG прямо на клиенте.
 * Финальную нормализацию до 4:3 всё равно делает сервер (см. core/images.py) —
 * здесь задача только сбить вес до разумного, чтобы запрос гарантированно дошёл.
 */

// Больше, чем целевой размер сервера (1200×900), чтобы не терять качество
// до серверного кропа, но достаточно мало, чтобы вес был ~200–600 КБ.
const MAX_SIDE = 1600;
const JPEG_QUALITY = 0.82;
// Мелкие файлы не трогаем — нет смысла перекодировать.
const SKIP_BELOW_BYTES = 600 * 1024;

function loadImage(url: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error("Не удалось прочитать изображение"));
        img.src = url;
    });
}

/**
 * Возвращает сжатый File (JPEG). Если сжать не удалось или файл не растровое
 * изображение — возвращает исходный файл без изменений (сервер разберётся).
 */
export async function compressImage(file: File): Promise<File> {
    if (!file.type.startsWith("image/")) return file;
    // SVG и уже маленькие файлы — как есть.
    if (file.type === "image/svg+xml") return file;
    if (file.size <= SKIP_BELOW_BYTES) return file;

    const url = URL.createObjectURL(file);
    try {
        const img = await loadImage(url);
        const { width, height } = img;
        if (!width || !height) return file;

        const scale = Math.min(1, MAX_SIDE / Math.max(width, height));
        const w = Math.round(width * scale);
        const h = Math.round(height * scale);

        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) return file;
        ctx.drawImage(img, 0, 0, w, h);

        const blob: Blob | null = await new Promise((resolve) =>
            canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY)
        );
        // Если браузер не отдал blob или он вдруг тяжелее оригинала — оставляем оригинал.
        if (!blob || blob.size >= file.size) return file;

        const base = file.name.replace(/\.[^.]+$/, "");
        return new File([blob], `${base}.jpg`, {
            type: "image/jpeg",
            lastModified: Date.now(),
        });
    } catch {
        return file;
    } finally {
        URL.revokeObjectURL(url);
    }
}

/** Сжимает список файлов; неудачные элементы остаются оригиналами. */
export async function compressImages(files: File[]): Promise<File[]> {
    return Promise.all(files.map(compressImage));
}
