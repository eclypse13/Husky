import {useEffect, useMemo, useState} from "react";
import {DogAvatar} from "@/components/DogAvatar/DogAvatar";
import "./DogDetailShowResultModal.css";

const API_BASE = "/api";

const SHOW_LABELS: Record<string, string> = {
    pk: "Монопородная ПК",
    kchk: "Монопородная КЧК",
    speciality: "Специализированная",
    sport: "Соревнование",
    world: "World / Euro Dog Show",
    other: "Выставка",
};

const NOMINATION_LABELS: Record<string, string> = {
    main: "Лучший Хаски",
    junior: "Юниоры",
    veteran: "Ветераны",
    working: "Рабочие",
};

const NOMINATION_ORDER = ["main", "junior", "veteran", "working"];

const getRatingYear = () => {
    const d = new Date();
    return d.getMonth() === 11 ? d.getFullYear() + 1 : d.getFullYear();
};
const DEFAULT_YEAR = getRatingYear();
const YEARS = [DEFAULT_YEAR, DEFAULT_YEAR - 1, DEFAULT_YEAR - 2, DEFAULT_YEAR - 3];

interface ShowResult {
    id: number;
    event_title: string;
    event_date: string;
    show_type: string;
    show_class?: string | null;
    grade?: string | null;
    place?: number | null;
    titles_won?: string | null;
    rating_points: number;
    nomination: string;
}

interface RatingEntry {
    nomination: string;
    label: string;
    points: number;
    place: number;
}

interface Section {
    nomination: string;
    label: string;
    items: ShowResult[];
    rating: RatingEntry | null;
}

interface DogInfo {
    id: number;
    name: string;
    photo_url: string | null;
    dog_photo: string | null;
}

interface Props {
    dog: DogInfo;
    onClose: () => void;
}

const fmtDate = (iso: string) =>
    new Date(iso).toLocaleDateString("ru-RU", {
        day: "numeric", month: "long", year: "numeric",
    });

export function DogDetailShowResultModal({dog, onClose}: Props) {
    const [year, setYear] = useState(DEFAULT_YEAR);
    const [results, setResults] = useState<ShowResult[] | null>(null);
    const [ratings, setRatings] = useState<RatingEntry[] | null>(null);

    // Закрытие по Escape
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
        document.addEventListener("keydown", onKey);
        document.body.style.overflow = "hidden";
        return () => {
            document.removeEventListener("keydown", onKey);
            document.body.style.overflow = "";
        };
    }, [onClose]);

    // Загрузка выступлений за выбранный сезон
    useEffect(() => {
        let cancelled = false;
        setResults(null);
        fetch(`${API_BASE}/dogs/${dog.id}/show_results/?year=${year}`)
            .then(r => r.json())
            .then(data => {
                if (cancelled) return;
                const list = Array.isArray(data) ? data : (data.results ?? []);
                setResults(list as ShowResult[]);
            })
            .catch(() => !cancelled && setResults([]));
        return () => {
            cancelled = true;
        };
    }, [dog.id, year]);

    // Баллы и место собаки за выбранный сезон — считает бэкенд (1 точечный COUNT-запрос
    // на номинацию по индексу year+nomination), а не клиент по уже загруженным выступлениям.
    useEffect(() => {
        let cancelled = false;
        setRatings(null);
        fetch(`${API_BASE}/dogs/${dog.id}/rating_summary/?year=${year}`)
            .then(r => r.json())
            .then((data: { nomination: string; points: number; place: number }[]) => {
                if (cancelled) return;
                setRatings(
                    data.map(r => ({
                        nomination: r.nomination,
                        label: NOMINATION_LABELS[r.nomination] ?? r.nomination,
                        points: r.points,
                        place: r.place,
                    }))
                );
            })
            .catch(() => !cancelled && setRatings([]));
        return () => {
            cancelled = true;
        };
    }, [dog.id, year]);

    // Группируем выступления по номинации: у каждой номинации, где есть хоть одно
    // выступление за сезон, — своя секция (карточка места + список именно её
    // выступлений), а не общий список под общим рядом карточек.
    const sections = useMemo<Section[]>(() => {
        if (!results) return [];
        const byNomination = new Map<string, ShowResult[]>();
        for (const r of results) {
            const list = byNomination.get(r.nomination) ?? [];
            list.push(r);
            byNomination.set(r.nomination, list);
        }
        return NOMINATION_ORDER
            .filter(n => byNomination.has(n))
            .map(nomination => ({
                nomination,
                label: NOMINATION_LABELS[nomination] ?? nomination,
                items: byNomination.get(nomination)!,
                rating: ratings?.find(r => r.nomination === nomination) ?? null,
            }));
    }, [results, ratings]);

    const loading = results === null || ratings === null;

    return (
        <div
            className="dsm-backdrop"
            onClick={e => e.target === e.currentTarget && onClose()}
            role="dialog"
            aria-modal="true"
            aria-label={`Выступления ${dog.name}`}
        >
            <div className="dsm-modal">

                <div className="dsm-header">
                    <div className="dsm-dog-info">
                        <div>
                            <p className="dsm-dog-name">{dog.name}</p>
                            <p className="dsm-dog-sub">Выступления и рейтинг по сезонам</p>
                        </div>
                    </div>
                    <button className="dsm-close" onClick={onClose} aria-label="Закрыть">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                             stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                            <line x1="18" y1="6" x2="6" y2="18"/>
                            <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>

                <div className="dsm-year-tabs" role="tablist" aria-label="Год рейтинга">
                    {YEARS.map(y => (
                        <button key={y} role="tab" aria-selected={year === y}
                                className={`dsm-year-tab${year === y ? " is-active" : ""}`}
                                onClick={() => setYear(y)}>
                            {y}
                        </button>
                    ))}
                </div>

                <div className="dsm-body">

                    {loading && (
                        <div className="dsm-loading">
                            <span className="dsm-spinner"/>
                            Загрузка выступлений…
                        </div>
                    )}

                    {!loading && results!.length === 0 && (
                        <div className="dsm-empty">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
                                 stroke="var(--border-light)" strokeWidth="1.2">
                                <rect x="3" y="4" width="18" height="18" rx="2"/>
                                <line x1="16" y1="2" x2="16" y2="6"/>
                                <line x1="8" y1="2" x2="8" y2="6"/>
                                <line x1="3" y1="10" x2="21" y2="10"/>
                            </svg>
                            <p>Нет выступлений за {year} год</p>
                        </div>
                    )}

                    {!loading && results!.length > 0 && sections.map(section => (
                        <section key={section.nomination} className="dsm-section">
                            <div className="dsm-rating-card">
                                {section.rating && (
                                    <span className="dsm-rating-place">Место: {section.rating.place}</span>
                                )}
                                <span className="dsm-rating-cat">{section.label}</span>
                                <span className="dsm-rating-pts">
                                    <strong>{section.rating?.points ?? 0}</strong> баллов
                                    {" · "}{section.items.length} выступлений
                                </span>
                            </div>

                            <div className="dsm-list">
                                {section.items.map(r => (
                                    <div key={r.id} className="dsm-item">
                                        <div className="dsm-item-date">
                                            {fmtDate(r.event_date)}
                                        </div>

                                        <div className="dsm-item-main">
                                            <p className="dsm-item-title">{r.event_title}</p>
                                            <div className="dsm-item-meta">
                                                {r.show_type && r.show_type !== "other" && (
                                                    <span className="dsm-tag dsm-tag--type">
                                                        {SHOW_LABELS[r.show_type] ?? r.show_type}
                                                    </span>
                                                )}
                                                {r.show_class && (
                                                    <span className="dsm-tag">Класс: {r.show_class}</span>
                                                )}
                                                {r.grade && (
                                                    <span className="dsm-tag">
                                                        {r.grade}{r.place ? `, ${r.place} место` : ""}
                                                    </span>
                                                )}
                                            </div>
                                            {r.titles_won && (
                                                <div className="dsm-badges">
                                                    {r.titles_won.split(",").map(t => (
                                                        <span key={t} className="dsm-badge">{t.trim()}</span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>

                                        <div className="dsm-item-pts">
                                            {r.rating_points > 0 ? (
                                                <>
                                                    <span className="dsm-pts-num">+{r.rating_points}</span>
                                                    <span className="dsm-pts-label">
                                                        балл{r.rating_points === 1 ? "" : "ов"}
                                                    </span>
                                                </>
                                            ) : (
                                                <span className="dsm-pts-zero">—</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    ))}
                </div>
            </div>
        </div>
    );
}
