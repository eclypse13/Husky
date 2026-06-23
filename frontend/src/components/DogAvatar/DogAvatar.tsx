import type {CSSProperties, MouseEvent, SyntheticEvent} from "react";
import {DEFAULT_DOG_IMG} from "@/utils/dogPhoto";

export interface DogAvatarProps {
    // прокси-ссылка на ЯД
    dog_photo?: string | null;
    // запасное фото
    photo_url?: string | null;
    alt?: string;
    size?: number;
    className?: string;
    style?: CSSProperties;
    wrapClassName?: string;
    loading?: "lazy" | "eager";
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

    const candidates = Array.from(
        new Set([dog_photo, photo_url].filter(Boolean) as string[])
    );
    const initialSrc = candidates[0] ?? DEFAULT_DOG_IMG;

    const handleError = (e: SyntheticEvent<HTMLImageElement>) => {
        const el = e.currentTarget;
        if (el.dataset.done === "1") return;
        const next = Number(el.dataset.idx ?? "0") + 1;
        if (next < candidates.length) {
            el.dataset.idx = String(next);
            el.src = candidates[next];
        } else {
            el.dataset.done = "1";
            el.src = DEFAULT_DOG_IMG;
        }
    };

    const img = (
        <img
            src={initialSrc}
            data-idx="0"
            alt={alt}
            loading={loading}
            className={className}
            style={{
                ...(!wrapClassName && size ? {width: size, height: size} : {}),
                ...style,
            }}
            onError={handleError}
            onClick={onClick}
        />
    );

    if (wrapClassName) {
        return (
            <div className={wrapClassName} style={size ? {width: size, height: size} : undefined}>
                {img}
            </div>
        );
    }
    return img;
}
