// src/pages/DogDetail/DogDetail.tsx
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { useDogsRetrieve, useDogsCalculateCoiCreate } from "@/generated/dogs/dogs";
import type { DogDetail as DogDetailType } from "@/generated/api.schemas";
import "./DogDetail.css";

const SEX_LABEL: Record<number, string> = { 1: "♂ Кобель", 2: "♀ Сука" };
// const SEX_CLASS: Record<number, string> = { 1: "dd-sex--male", 2: "dd-sex--female" };

const PLACEHOLDER_URLS = ["https://zooportal.pro/images/logo1.png"];
const DEFAULT_DOG_IMG = "/no-image-dog.png";
const dogPhoto = (url: string | null | undefined): string =>
  url && !PLACEHOLDER_URLS.includes(url) ? url : DEFAULT_DOG_IMG;

function formatDate(raw: string | null): string | null {
    if (!raw) return null;
    const d = new Date(raw);
    if (isNaN(d.getTime())) return raw;
    return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
}

function Row({ label, value }: { label: string; value?: string | number | null }) {
    return (
        <div className="dd-row">
            <span className="dd-row-label">{label}</span>
            <span className={`dd-row-value${!value && value !== 0 ? " dd-row-value--empty" : ""}`}>
                {value ?? "Не указано"}
            </span>
        </div>
    );
}

function ParentCard({ label, parent }: {
    label: string;
    parent: {
        id: number; display_name: string; sex: number;
        year_of_birth: number | null; color: string | null; photo_url: string | null;
    } | null;
}) {
    return (
        <div className="dd-parent">
            <span className="dd-parent-label">{label}</span>
            {parent ? (
                <Link to={`/archive/dog/${parent.id}`} className="dd-parent-link">
                    <div className="dd-parent-avatar">
                        <img
                            src={dogPhoto(parent.photo_url)}
                            alt={parent.display_name}
                        />
                    </div>
                    <div className="dd-parent-body">
                        <span className="dd-parent-name">{parent.display_name}</span>
                    </div>
                    <span className="dd-parent-arrow">→</span>
                </Link>
            ) : (
                <span className="dd-parent-empty">Не указано</span>
            )}
        </div>
    );
}

// function TitleBadges({ titles }: { titles: DogTitle[] }) {
//     const prefix = titles.filter((t) => t.is_prefix);
//     if (!prefix.length) return null;
//     return (
//         <div className="dd-title-badges">
//             {prefix.map((t) => (
//                 <span key={t.id} className="dd-title-badge" title={t.long_name ?? undefined}>
//                     {t.short_name.toUpperCase()}
//                     {t.country ? <em>.{t.country.toUpperCase()}</em> : null}
//                     {t.winner_year ? <em className="dd-title-year"> '{String(t.winner_year).slice(-2)}</em> : null}
//                 </span>
//             ))}
//         </div>
//     );
// }

function Skeleton() {
    return (
        <div className="dd-skeleton">
            <div className="dd-skeleton-photo" />
            <div className="dd-skeleton-lines">
                {[160, 260, 180, 140, 210].map((w, i) => (
                    <div key={i} className="dd-skeleton-line" style={{ width: w }} />
                ))}
            </div>
        </div>
    );
}

export default function DogDetail() {
    const { id } = useParams<{ id: string }>();
    const numId = Number(id);

    const { data: response, isLoading: loading, error: fetchError } = useDogsRetrieve(numId, {
        query: { enabled: !!id && !isNaN(numId) },
    });
    const dog = response?.data as DogDetailType | undefined;
    const error = fetchError ? "Ошибка загрузки" : null;

    // ── COI ───────────────────────────────────────────────────────────────────
    const coiMutation = useDogsCalculateCoiCreate();
    const [coiOverride, setCoiOverride] = useState<{ coi: number; coi_updated_on: string } | null>(null);

    const handleCalculateCoi = () => {
        if (!dog) return;
        setCoiOverride(null);
        coiMutation.mutate(
            { id: dog.id, data: { generations: 10 } },
            {
                onSuccess: (res) => {
                    const data = res.data;
                    if ('coi' in data) {
                        setCoiOverride({ coi: data.coi, coi_updated_on: data.coi_updated_on });
                    }
                },
            },
        );
    };

    const coiResult = coiMutation.data?.data;
    const coiLoading = coiMutation.isPending;
    const coiError = coiMutation.error ? "Ошибка расчёта COI" : null;
    const displayCoi = coiOverride?.coi ?? (coiResult && 'coi' in coiResult ? coiResult.coi : null);

    const suffixTitles = dog?.titles?.filter((t) => !t.is_prefix) ?? [];

    return (
        <div className="dd-page">
            <Breadcrumb
                title="Карточка собаки"
                items={[
                    { label: "Главная", to: "/" },
                    { label: "Архив", to: "/archive" },
                    { label: dog?.display_name ?? "…" },
                ]}
            />

            <div className="dd-container">
                {loading && <Skeleton />}

                {error && (
                    <div className="dd-error">
                        <span>⚠️</span>
                        <p>{error}</p>
                        <Link to="/archive" className="dd-btn">← Вернуться в архив</Link>
                    </div>
                )}

                {!loading && !error && dog && (
                    <>
                        {/* ══ ШАПКА ══════════════════════════════════════════ */}
                        <div className="dd-header">
                            <div className="dd-header-bar" />

                            <div className="dd-photo-wrap">
                                <img
                                    src={dogPhoto(dog.photo_url)}
                                    alt={dog.display_name}
                                    className="dd-photo"
                                />
                            </div>

                            <div className="dd-header-info">
                                {/*{dog.titles.length > 0 && <TitleBadges titles={dog.titles} />}*/}
                                <h1 className="dd-name">{dog.display_name}</h1>
                                {dog.call_name && dog.call_name !== dog.display_name && (
                                    <p className="dd-callname">«{dog.call_name}»</p>
                                )}
                                {dog.kennel && <p className="dd-kennel">🏠 {dog.kennel}</p>}

                                <div className="dd-actions">
                                    {dog.zooportal_id && (
                                        <a href={`https://zooportal.pro/pedigree/view/${dog.zooportal_id}/`}
                                            target="_blank" rel="noopener noreferrer" className="dd-btn">
                                            🔗 Zooportal
                                        </a>
                                    )}
                                    {dog.uuid && (
                                        <a href={`https://siberianhusky.breedarchive.com/animal/view/${dog.link_name}-${dog.uuid}`}
                                            target="_blank" rel="noopener noreferrer" className="dd-btn">
                                            📋 BreedArchive
                                        </a>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* ══ КАРТОЧКИ ════════════════════════════════════════ */}
                        <div className="dd-grid">
                            <section className="dd-card">
                                <h2 className="dd-card-title"><span className="dd-card-icon">📄</span>Основные данные</h2>
                                <div className="dd-rows">
                                    <Row label="Кличка" value={dog.call_name || dog.display_name} />
                                    <Row label="Пол" value={SEX_LABEL[dog.sex]} />
                                    <Row label="Дата рождения" value={formatDate(dog.date_of_birth)} />
                                    <Row label="Страна рождения" value={dog.land_of_birth} />
                                    <Row label="Окрас" value={dog.color} />
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
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                                    <polyline points="23 4 23 10 17 10" />
                                                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                                                </svg>
                                            </button>
                                            {coiLoading ? (
                                                <span className="dd-coi-spinner" />
                                            ) : displayCoi != null ? (
                                                <span className="dd-row-value">{displayCoi.toFixed(2)} %</span>
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
                                    <ParentCard label="Отец (Sire)" parent={dog.sire} />
                                    <ParentCard label="Мать (Dam)" parent={dog.dam} />
                                </div>
                            </section>

                            <section className="dd-card">
                                <h2 className="dd-card-title"><span className="dd-card-icon">🏷️</span>Регистрация</h2>
                                <div className="dd-rows">
                                    <Row label="№ родословной" value={dog.registration_number} />
                                    <Row label="Чип / Клеймо" value={dog.brand_chip} />
                                </div>
                            </section>

                            <section className="dd-card">
                                <h2 className="dd-card-title"><span className="dd-card-icon">👤</span>Заводчик и владелец</h2>
                                <div className="dd-rows">
                                    <div className="dd-row dd-row--block">
                                        <span className="dd-row-label">Заводчик</span>
                                        <div className="dd-people">
                                            {dog.breeders.length
                                                ? dog.breeders.map((b) => (
                                                    <span key={b.id} className="dd-person">
                                                        {b.name}{b.kennel && <span className="dd-person-kennel"> · {b.kennel}</span>}
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
                                                        {o.name}{o.kennel && <span className="dd-person-kennel"> · {o.kennel}</span>}
                                                    </span>
                                                ))
                                                : <span className="dd-row-value--empty">Не указано</span>}
                                        </div>
                                    </div>
                                </div>
                            </section>
                        </div>

                        {/* ══ ТИТУЛЫ ══════════════════════════════════════════ */}
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
                                            {t.winner_year && <span className="dd-title-card-year">{t.winner_year}</span>}
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

                        {/* ══ НАВИГАЦИЯ ═══════════════════════════════════════ */}
                        <div className="dd-nav">
                            <Link to="/archive" className="dd-btn">← Назад в архив</Link>
                            <Link to={`/archive/pedigree/${dog.id}`} className="dd-btn dd-btn--primary">
                                Родословная
                            </Link>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

