import DEFAULT_DOG_IMG from "@/assets/no-image-dog.png";
const PLACEHOLDER_URLS = ["https://zooportal.pro/images/logo1.png"];

// const DEFAULT_DOG_IMG  = "@/assets/no-image-dog.png";

/**
 * Возвращает лучшую доступную ссылку на фото собаки.
 *
 * Использование:
 *   dogPhoto(dog.photo, dog.photo_url)   // полный вариант
 *   dogPhoto(dog.photo)                  // если photo уже содержит fallback
 */
export function dogPhoto(
  dog_photo:    string | null | undefined,
  photoUrl: string | null | undefined = null,
): string {
  const url = dog_photo || photoUrl;
  return url && !PLACEHOLDER_URLS.includes(url) ? url : DEFAULT_DOG_IMG;
}

export { DEFAULT_DOG_IMG, PLACEHOLDER_URLS };