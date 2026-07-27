import {useEffect, useState} from "react";
import {Link, useParams} from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import {getDogDetail} from "@/api/dogs";
import type {CoiCalculationResult, DogDetail} from "@/types/dog";
import "./DogDetail.css";
import HealthModal from "@/components/HealthModal/HealthModal";
import {PLACEHOLDER_URLS} from "@/utils/dogPhoto";
import {DogAvatar} from "@/components/DogAvatar/DogAvatar";
import {DogDetailShowResultModal} from "@/components/DogDetailShowResultModal/DogDetailShowResultModal";

const SEX_LABEL: Record<number, string> = {1: "♂ Кобель", 2: "♀ Сука"};

function formatDate(raw: string | null): string | null {
    if (!raw) return null;
    const d = new Date(raw);
    if (isNaN(d.getTime())) return raw;
    return d.toLocaleDateString("ru-RU", {day: "numeric", month: "long", year: "numeric"});
}

function Row({label, value}: { label: string; value?: string | number | null }) {
    return (
        <div className="dd-row">
            <span className="dd-row-label">{label}</span>
            <span className={`dd-row-value${!value && value !== 0 ? " dd-row-value--empty" : ""}`}>
                {value ?? "Не указано"}
            </span>
        </div>
    );
}

function ParentCard({label, parent}: {
    label: string;
    parent: {
        id: number; registered_name: string; sex: number;
        year_of_birth: number | null; color: string | null; photo_url: string | null; dog_photo: string | null;
    } | null;
}) {
    return (
        <div className="dd-parent">
            <span className="dd-parent-label">{label}</span>
            {parent ? (
                <Link to={`/archive/dog/${parent.id}`} className="dd-parent-link">
                    <DogAvatar
                        dog_photo={parent.dog_photo}
                        photo_url={parent.photo_url}
                        alt={parent.registered_name}
                        wrapClassName="dd-parent-avatar"
                    />
                    <div className="dd-parent-body">
                        <span className="dd-parent-name">{parent.registered_name}</span>
                    </div>
                    <span className="dd-parent-arrow">→</span>
                </Link>
            ) : (
                <span className="dd-parent-empty">Не указано</span>
            )}
        </div>
    );
}

function Skeleton() {
    return (
        <div className="dd-skeleton">
            <div className="dd-skeleton-photo"/>
            <div className="dd-skeleton-lines">
                {[160, 260, 180, 140, 210].map((w, i) => (
                    <div key={i} className="dd-skeleton-line" style={{width: w}}/>
                ))}
            </div>
        </div>
    );
}

export default function DogDetail() {
    const {id} = useParams<{ id: string }>();
    const [dog, setDog] = useState<DogDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [healthOpen, setHealthOpen] = useState(false);
    const [showsOpen, setShowsOpen] = useState(false);

    const [photoOpen, setPhotoOpen] = useState(false);

    const [coiLoading, setCoiLoading] = useState(false);
    const [coiResult, setCoiResult] = useState<CoiCalculationResult | null>(null);
    const [coiError, setCoiError] = useState<string | null>(null);

    const handleCalculateCoi = async () => {
        if (!dog) return;
        setCoiLoading(true);
        setCoiError(null);
        setCoiResult(null);
        try {
            const csrfToken = document.cookie
                .split("; ")
                .find((r) => r.startsWith("csrftoken="))
                ?.split("=")[1] ?? "";

            const res = await fetch(`/api/dogs/${dog.id}/calculate_coi/`, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    ...(csrfToken ? {"X-CSRFToken": csrfToken} : {}),
                },
                body: JSON.stringify({generations: 10}),
            });

            const contentType = res.headers.get("content-type") ?? "";
            if (!contentType.includes("application/json")) {
                setCoiError(`Сервер вернул ${res.status} (${res.statusText})`);
                return;
            }

            const data = await res.json();
            if (!res.ok) {
                setCoiError(data.error ?? data.detail ?? `Ошибка ${res.status}`);
            } else {
                setCoiResult(data);
                setDog((prev) => prev ? {...prev, coi: data.coi, coi_updated_on: data.coi_updated_on} : prev);
            }
        } catch (e) {
            setCoiError(e instanceof Error ? e.message : "Сетевая ошибка");
        } finally {
            setCoiLoading(false);
        }
    };

    useEffect(() => {
        if (!id) return;
        setLoading(true);
        setError(null);
        setCoiResult(null);
        setCoiError(null);
        setCoiLoading(false);
        getDogDetail(Number(id))
            .then(setDog)
            .catch((e) => setError(e instanceof Error ? e.message : "Ошибка загрузки"))
            .finally(() => setLoading(false));
    }, [id]);

    useEffect(() => {
        if (!photoOpen) return;
        const handler = (e: KeyboardEvent) => {
            if (e.key === "Escape") setPhotoOpen(false);
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, [photoOpen]);

    const suffixTitles = dog?.titles.filter((t) => !t.is_prefix) ?? [];
    const isClickable = !!dog?.photo_url && !PLACEHOLDER_URLS.includes(dog.photo_url);

    return (
        <div className="dd-page">
            <Breadcrumb
                title="Карточка собаки"
                items={[
                    {label: "Главная", to: "/"},
                    {label: "Архив", to: "/archive"},
                    {label: dog?.registered_name ?? "…"},
                ]}
            />

            <div className="dd-container">
                {loading && <Skeleton/>}

                {error && (
                    <div className="dd-error">
                        <span>⚠️</span>
                        <p>{error}</p>
                        <Link to="/archive" className="dd-btn">← Вернуться в архив</Link>
                    </div>
                )}

                {!loading && !error && dog && (
                    <>
                        {photoOpen && (
                            <div className="dd-lightbox" onClick={() => setPhotoOpen(false)}>
                                <button
                                    className="dd-lightbox-close"
                                    onClick={() => setPhotoOpen(false)}
                                    aria-label="Закрыть"
                                >
                                    ✕
                                </button>
                                <DogAvatar
                                    dog_photo={dog.dog_photo}
                                    photo_url={dog.photo_url}
                                    alt={dog.registered_name}
                                    className="dd-lightbox-img"
                                    loading="eager"
                                    onClick={(e) => e.stopPropagation()}
                                />
                            </div>
                        )}

                        <div className="dd-header">
                            <div className="dd-photo-wrap">
                                <DogAvatar
                                    dog_photo={dog.dog_photo}
                                    photo_url={dog.photo_url}
                                    alt={dog.registered_name}
                                    className={`dd-photo${isClickable ? " dd-photo--clickable" : ""}`}
                                    loading="eager"
                                    onClick={isClickable ? () => setPhotoOpen(true) : undefined}
                                />
                            </div>

                            <div className="dd-header-info">
                                <h1 className="dd-name">{dog.registered_name}</h1>
                                {dog.call_name && dog.call_name !== dog.registered_name && (
                                    <p className="dd-callname">«{dog.call_name}»</p>
                                )}
                                {dog.kennel && <p className="dd-kennel">🏠 {dog.kennel}</p>}

                                <div className="dd-actions">
                                    <div className="dd-actions-row">
                                        <Link to={`/archive/pedigree/${dog.id}`} className="dd-btn dd-btn--primary">
                                            Родословная
                                        </Link>

                                        <button className="dd-btn dd-btn--primary" onClick={() => setHealthOpen(true)}>
                                            Здоровье
                                        </button>

                                        <button className="dd-btn dd-btn--primary" onClick={() => setShowsOpen(true)}>
                                            Выступления
                                        </button>
                                    </div>

                                    {(dog.zooportal_id || dog.uuid) && (
                                        <div className="dd-actions-row">
                                            {dog.zooportal_id && (
                                                <a href={`https://zooportal.pro/pedigree/view/${dog.zooportal_id}/`}
                                                   target="_blank" rel="noopener noreferrer" className="dd-btn">
                                                    Zooportal<span className="dd-external-icon">↗</span>
                                                </a>
                                            )}
                                            {dog.uuid && (
                                                <a href={`https://siberianhusky.breedarchive.com/animal/view/${dog.link_name}-${dog.uuid}`}
                                                   target="_blank" rel="noopener noreferrer" className="dd-btn">
                                                    BreedArchive<span className="dd-external-icon">↗</span>
                                                </a>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="dd-grid">
                            <section className="dd-card">
                                <h2 className="dd-card-title"><span className="dd-card-icon">📄</span>Основные данные
                                </h2>
                                <div className="dd-rows">
                                    <Row label="Кличка" value={dog.call_name || dog.registered_name}/>
                                    <Row label="Пол" value={SEX_LABEL[dog.sex]}/>
                                    <Row label="Дата рождения" value={formatDate(dog.date_of_birth)}/>
                                    <Row label="Страна рождения" value={dog.land_of_birth}/>
                                    <Row label="Окрас" value={dog.color}/>
                                    <Row
                                        label="Размер / Вес"
                                        value={dog.size && dog.weight ? `${dog.size} см / ${dog.weight} кг` : null}
                                    />
                                    <div className="dd-row">
                                        <span className="dd-row-label">COI</span>
                                        <span className="dd-coi-inline">
                                            {coiError && (
                                                <span className="dd-coi-error dd-coi-error--float">{coiError}</span>
                                            )}
                                            <button
                                                className="dd-coi-refresh"
                                                onClick={handleCalculateCoi}
                                                disabled={coiLoading}
                                                title="Рассчитать / обновить COI"
                                                aria-label="Обновить COI"
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                                                     stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
                                                     strokeLinejoin="round">
                                                    <polyline points="23 4 23 10 17 10"/>
                                                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                                                </svg>
                                            </button>
                                            {coiLoading ? (
                                                <span className="dd-coi-spinner"/>
                                            ) : coiResult ? (
                                                <span className="dd-row-value">{coiResult.coi.toFixed(2)} %</span>
                                            ) : dog.coi != null ? (
                                                <span className="dd-row-value">{dog.coi.toFixed(2)} %</span>
                                            ) : (
                                                <span className="dd-row-value dd-row-value--empty">Не указано</span>
                                            )}
                                        </span>
                                    </div>
                                </div>
                            </section>

                            <section className="dd-card">
                                <h2 className="dd-card-title"><span className="dd-card-icon">🐾</span>Родители</h2>
                                <div className="dd-parents">
                                    <ParentCard label="Отец (Sire)" parent={dog.sire}/>
                                    <ParentCard label="Мать (Dam)" parent={dog.dam}/>
                                </div>
                            </section>

                            <section className="dd-card">
                                <h2 className="dd-card-title"><span className="dd-card-icon">🏷️</span>Регистрация</h2>
                                <div className="dd-rows">
                                    <Row label="№ родословной" value={dog.registration_number}/>
                                    <Row label="Чип / Клеймо" value={dog.brand_chip}/>
                                </div>
                            </section>

                            <section className="dd-card">
                                <h2 className="dd-card-title"><span className="dd-card-icon">👤</span>Заводчик и владелец
                                </h2>
                                <div className="dd-rows">
                                    <div className="dd-row dd-row--block">
                                        <span className="dd-row-label">Заводчик</span>
                                        <div className="dd-people">
                                            {dog.breeders.length
                                                ? dog.breeders.map((b) => (
                                                    <span key={b.id} className="dd-person">
                                                        {b.name}{b.kennel &&
                                                        <span className="dd-person-kennel"> · {b.kennel}</span>}
                                                    </span>
                                                ))
                                                : <span className="dd-row-value--empty">Не указано</span>}
                                        </div>
                                    </div>
                                    <div className="dd-row dd-row--block">
                                        <span className="dd-row-label">Владелец</span>
                                        <div className="dd-people">
                                            {dog.owners.length
                                                ? dog.owners.map((o) => (
                                                    <span key={o.id} className="dd-person">
                                                        {o.name}{o.kennel &&
                                                        <span className="dd-person-kennel"> · {o.kennel}</span>}
                                                    </span>
                                                ))
                                                : <span className="dd-row-value--empty">Не указано</span>}
                                        </div>
                                    </div>
                                </div>
                            </section>
                        </div>

                        {dog.titles.length > 0 && (
                            <section className="dd-card dd-card--wide">
                                <h2 className="dd-card-title"><span className="dd-card-icon">🏆</span>Титулы</h2>
                                <div className="dd-titles-grid">
                                    {dog.titles.map((t) => (
                                        <div key={t.id}
                                             className={`dd-title-card ${t.is_prefix ? "dd-title-card--prefix" : "dd-title-card--suffix"}`}>
                                            <span className="dd-title-card-short">
                                                {t.short_name.toUpperCase()}
                                                {t.country && <em>.{t.country.toUpperCase()}</em>}
                                            </span>
                                            {t.long_name && <span className="dd-title-card-long">{t.long_name}</span>}
                                            {t.winner_year &&
                                                <span className="dd-title-card-year">{t.winner_year}</span>}
                                        </div>
                                    ))}
                                </div>
                                {suffixTitles.length > 0 && (
                                    <div className="dd-suffix-row">
                                        <span className="dd-row-label">Суффиксные:</span>
                                        {suffixTitles.map((t) => (
                                            <span key={t.id} className="dd-title-badge dd-title-badge--suffix">
                                                {t.short_name.toUpperCase()}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </section>
                        )}

                        <div className="dd-nav">
                            <Link to="/archive" className="dd-btn">← Назад в архив</Link>
                        </div>
                    </>
                )}
            </div>

            {healthOpen && dog && (
                <HealthModal
                    dogId={dog.id}
                    dogName={dog.registered_name}
                    onClose={() => setHealthOpen(false)}
                />
            )}

            {showsOpen && dog && (
                <DogDetailShowResultModal
                    dog={{
                        id: dog.id,
                        name: dog.registered_name || dog.call_name,
                        dog_photo: dog.dog_photo,
                        photo_url: dog.photo_url,
                    }}
                    onClose={() => setShowsOpen(false)}
                />
            )}
        </div>
    );
}
