// src/components/DogAvatar/DogAvatar.tsx
import type { CSSProperties, MouseEvent, SyntheticEvent } from "react";
import { dogPhoto, DEFAULT_DOG_IMG } from "@/utils/dogPhoto";

export interface DogAvatarProps {
  /** Приоритетное фото (поле dog_photo из API) */
  dog_photo?: string | null;
  /** Запасное фото (поле photo_url из API) */
  photo_url?: string | null;
  alt?: string;
  /**
   * Если передан wrapClassName — size применяется к wrapper-div,
   * img растягивается через CSS.
   * Если wrapper нет — size применяется к img напрямую.
   */
  size?: number;
  /** CSS-класс на тег <img> */
  className?: string;
  /** Инлайн-стили на тег <img> */
  style?: CSSProperties;
  /**
   * Если указан — img оборачивается в <div className={wrapClassName}>.
   * Используй, когда в CSS уже есть стили для этой обёртки
   * (object-fit, border-radius и т.д.).
   */
  wrapClassName?: string;
  loading?: "lazy" | "eager";
  /** Event передаётся, чтобы можно было вызвать e.stopPropagation() в lightbox */
  onClick?: (e: MouseEvent<HTMLImageElement>) => void;
}

export function DogAvatar({
  dog_photo,
  photo_url,
  alt = "",
  size,
  className,
  style,
  wrapClassName,
  loading = "lazy",
  onClick,
}: DogAvatarProps) {
  const handleError = (e: SyntheticEvent<HTMLImageElement>) => {
    (e.target as HTMLImageElement).src = DEFAULT_DOG_IMG;
  };

  const img = (
    <img
      src={dogPhoto(dog_photo ?? null, photo_url ?? null)}
      alt={alt}
      loading={loading}
      className={className}
      style={{
        ...(!wrapClassName && size ? { width: size, height: size } : {}),
        ...style,
      }}
      onError={handleError}
      onClick={onClick}
    />
  );

  if (wrapClassName) {
    return (
      <div
        className={wrapClassName}
        style={size ? { width: size, height: size } : undefined}
      >
        {img}
      </div>
    );
  }

  return img;
}

