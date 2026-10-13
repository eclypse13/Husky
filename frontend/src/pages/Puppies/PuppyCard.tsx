import { Link } from "react-router-dom";
import type { PuppyListing } from "@/types/puppy";
import { DEFAULT_DOG_IMG } from "@/utils/dogPhoto";

export function formatPrice(price: string | null): string {
    if (!price) return "Цена договорная";
    const n = Number(price);
    if (!Number.isFinite(n) || n <= 0) return "Цена договорная";
    return `${n.toLocaleString("ru-RU")} ₽`;
}

const STATUS_CLASS: Record<string, string> = {
    available: "puppy-badge--available",
    reserved: "puppy-badge--reserved",
    sold: "puppy-badge--sold",
};

export default function PuppyCard({ puppy }: { puppy: PuppyListing }) {
    const cover = puppy.photos[0]?.image || DEFAULT_DOG_IMG;

    return (
        <Link to={`/puppies/${puppy.id}`} className="puppy-card">
            <div className="puppy-card__media">
                <img
                    src={cover}
                    alt={puppy.name}
                    loading="lazy"
                    decoding="async"
                    onError={(e) => {
                        (e.currentTarget as HTMLImageElement).src = DEFAULT_DOG_IMG;
                    }}
                />
                {puppy.photos.length > 1 && (
                    <span className="puppy-card__count">📷 {puppy.photos.length}</span>
                )}
                {puppy.is_nkp_member && <span className="puppy-card__nkp">НКП</span>}
                {!puppy.is_published && <span className="puppy-card__draft">Скрыто</span>}
            </div>

            <div className="puppy-card__body">
                <div className="puppy-card__price">{formatPrice(puppy.price)}</div>
                <h3 className="puppy-card__name">{puppy.name}</h3>

                <div className="puppy-card__meta">
                    {puppy.sex_display && <span>{puppy.sex === "male" ? "♂" : "♀"} {puppy.sex_display}</span>}
                    {puppy.color && <span>{puppy.color}</span>}
                </div>

                {puppy.kennel_name && <div className="puppy-card__kennel">🏠 {puppy.kennel_name}</div>}

                <div className="puppy-card__footer">
                    {puppy.city && <span className="puppy-card__city">📍 {puppy.city}</span>}
                    <span className={`puppy-badge ${STATUS_CLASS[puppy.status] || ""}`}>
                        {puppy.status_display}
                    </span>
                </div>
            </div>
        </Link>
    );
}
