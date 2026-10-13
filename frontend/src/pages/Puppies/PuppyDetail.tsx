import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { deletePuppy, fetchPuppy, savePuppy } from "@/api/puppies";
import { DEFAULT_DOG_IMG } from "@/utils/dogPhoto";
import { formatPrice } from "./PuppyCard";
import "./Puppies.css";

function ParentLink({ label, archiveId, name }: { label: string; archiveId: number | null; name: string }) {
    if (!name) return null;
    return (
        <div className="puppy-detail__parent">
            <span className="puppy-detail__parent-label">{label}</span>
            {archiveId ? (
                <Link to={`/archive/dog/${archiveId}`} className="puppy-detail__parent-link">
                    {name} ↗
                </Link>
            ) : (
                <span>{name}</span>
            )}
        </div>
    );
}

export default function PuppyDetail() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [active, setActive] = useState(0);
    const [deleting, setDeleting] = useState(false);
    const [toggling, setToggling] = useState(false);

    const { data: puppy, isLoading, isError, error } = useQuery({
        queryKey: ["puppy", id],
        queryFn: () => fetchPuppy(id!),
        enabled: Boolean(id),
    });

    const handleDelete = async () => {
        if (!puppy) return;
        if (!window.confirm("Удалить объявление? Действие необратимо.")) return;
        setDeleting(true);
        try {
            await deletePuppy(puppy.id);
            queryClient.invalidateQueries({ queryKey: ["puppies"] });
            navigate("/puppies");
        } catch (e) {
            alert(e instanceof Error ? e.message : "Не удалось удалить");
            setDeleting(false);
        }
    };

    const handleTogglePublish = async () => {
        if (!puppy) return;
        setToggling(true);
        try {
            const fd = new FormData();
            fd.set("is_published", puppy.is_published ? "false" : "true");
            await savePuppy(fd, puppy.id);
            queryClient.invalidateQueries({ queryKey: ["puppy", String(puppy.id)] });
            queryClient.invalidateQueries({ queryKey: ["puppies"] });
        } catch (e) {
            alert(e instanceof Error ? e.message : "Не удалось изменить видимость");
        } finally {
            setToggling(false);
        }
    };

    if (isLoading) return <div className="puppies-state">Загрузка…</div>;
    if (isError || !puppy)
        return (
            <div className="puppies-state puppies-state--error">
                {error instanceof Error ? error.message : "Объявление не найдено"}
            </div>
        );

    const photos = puppy.photos.length ? puppy.photos : [{ id: 0, image: DEFAULT_DOG_IMG, order: 0 }];
    const cover = photos[active]?.image || DEFAULT_DOG_IMG;

    return (
        <div className="puppies-page">
            <Breadcrumb
                title={puppy.name}
                items={[
                    { label: "Главная", to: "/" },
                    { label: "Щенки", to: "/puppies" },
                    { label: puppy.name },
                ]}
            />

            <main className="puppies-main">
                <div className="content-container">
                    <div className="puppy-detail">
                        <div className="puppy-detail__gallery">
                            <div className="puppy-detail__cover">
                                <img
                                    src={cover || DEFAULT_DOG_IMG}
                                    alt={puppy.name}
                                    onError={(e) => { (e.currentTarget as HTMLImageElement).src = DEFAULT_DOG_IMG; }}
                                />
                                {puppy.is_nkp_member && <span className="puppy-card__nkp">НКП</span>}
                            </div>
                            {photos.length > 1 && (
                                <div className="puppy-detail__thumbs">
                                    {photos.map((ph, i) => (
                                        <button
                                            key={ph.id}
                                            className={`puppy-detail__thumb ${i === active ? "is-active" : ""}`}
                                            onClick={() => setActive(i)}
                                            type="button"
                                        >
                                            <img src={ph.image || DEFAULT_DOG_IMG} alt="" />
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="puppy-detail__info">
                            <div className="puppy-detail__price">{formatPrice(puppy.price)}</div>
                            <h1 className="puppy-detail__name">{puppy.name}</h1>

                            <div className="puppy-detail__tags">
                                {puppy.sex_display && (
                                    <span className="puppy-chip">{puppy.sex === "male" ? "♂" : "♀"} {puppy.sex_display}</span>
                                )}
                                {puppy.color && <span className="puppy-chip">{puppy.color}</span>}
                                {puppy.date_of_birth && (
                                    <span className="puppy-chip">р. {new Date(puppy.date_of_birth).toLocaleDateString("ru-RU")}</span>
                                )}
                                <span className={`puppy-badge puppy-badge--${puppy.status}`}>{puppy.status_display}</span>
                                {puppy.can_edit && !puppy.is_published && (
                                    <span className="puppy-hidden-tag">Скрыто</span>
                                )}
                            </div>

                            {puppy.can_edit && (
                                <div className="puppy-detail__owner-actions">
                                    <Link to={`/puppies/${puppy.id}/edit`} className="puppy-btn puppy-btn--soft">
                                        ✏️ Редактировать
                                    </Link>
                                    <button className="puppy-btn puppy-btn--soft" onClick={handleTogglePublish} disabled={toggling}>
                                        {toggling
                                            ? "Сохранение…"
                                            : puppy.is_published
                                            ? "🙈 Скрыть"
                                            : "👁 Опубликовать"}
                                    </button>
                                    <button className="puppy-btn puppy-btn--danger" onClick={handleDelete} disabled={deleting}>
                                        🗑 {deleting ? "Удаление…" : "Удалить"}
                                    </button>
                                </div>
                            )}

                            {puppy.description && (
                                <div className="puppy-detail__section">
                                    <h3>Описание</h3>
                                    <p className="puppy-detail__desc">{puppy.description}</p>
                                </div>
                            )}

                            {(puppy.sire_name || puppy.dam_name) && (
                                <div className="puppy-detail__section">
                                    <h3>Родители</h3>
                                    <ParentLink label="Отец" archiveId={puppy.sire_archive_id} name={puppy.sire_name} />
                                    <ParentLink label="Мать" archiveId={puppy.dam_archive_id} name={puppy.dam_name} />
                                </div>
                            )}

                            <div className="puppy-detail__section">
                                <h3>Контакты</h3>
                                {puppy.kennel_name && (
                                    <div className="puppy-detail__row">
                                        🏠 Питомник:{" "}
                                        {puppy.kennel_url ? (
                                            <a href={puppy.kennel_url} target="_blank" rel="noreferrer">{puppy.kennel_name}</a>
                                        ) : (
                                            <span>{puppy.kennel_name}</span>
                                        )}
                                        {puppy.is_nkp_member && <span className="puppy-inline-nkp">член НКП</span>}
                                    </div>
                                )}
                                <div className="puppy-detail__row">📞 Заводчик: <strong>{puppy.breeder_contact}</strong></div>
                                {puppy.city && <div className="puppy-detail__row">📍 {puppy.city}</div>}
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
