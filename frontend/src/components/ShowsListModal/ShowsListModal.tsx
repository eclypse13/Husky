import {useEffect, useState} from "react";
import {Link} from "react-router-dom";
import {DogAvatar} from "@/components/DogAvatar/DogAvatar";
import "./ShowsListModal.css";

const API_BASE = "/api";

const getRatingYear = () => {
    const d = new Date();
    return d.getMonth() === 11 ? d.getFullYear() + 1 : d.getFullYear();
};
const DEFAULT_YEAR = getRatingYear();
const YEARS = [DEFAULT_YEAR, DEFAULT_YEAR - 1, DEFAULT_YEAR - 2, DEFAULT_YEAR - 3];

interface ShowEvent {
    id: number;
    title: string;
    event_date: string | null;
    organizer: string | null;
    city: string | null;
    results_parsed_at: string | null;
    results_count: number;
}

interface DogInfo {
    id: number;
    display_name?: string;
    registered_name?: string;
    call_name?: string;
    photo_url: string | null;
    dog_photo: string | null;
}

interface EventResult {
    id: number;
    dog: DogInfo;
    show_class?: string | null;
    grade?: string | null;
    place?: number | null;
    titles_won?: string | null;
    rating_points: number;
}

type Status = "done" | "unavailable" | "none";

const getStatus = (e: ShowEvent): Status => {
    if (!e.results_parsed_at) return "unavailable";
    return e.results_count > 0 ? "done" : "none";
};

const getName = (d: DogInfo) => d.registered_name || d.display_name || d.call_name || "—";

const fmtDate = (iso: string | null) =>
    iso ? new Date(iso).toLocaleDateString("ru-RU", {day: "numeric", month: "long"}) : "—";

interface Props {
    onClose: () => void;
}

export function ShowsListModal({onClose}: Props) {
    const [year, setYear] = useState(DEFAULT_YEAR);
    const [events, setEvents] = useState<ShowEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [openId, setOpenId] = useState<number | null>(null);
    const [resultsById, setResultsById] = useState<Record<number, EventResult[]>>({});
    const [loadingId, setLoadingId] = useState<number | null>(null);

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
        document.addEventListener("keydown", onKey);
        document.body.style.overflow = "hidden";
        return () => {
            document.removeEventListener("keydown", onKey);
            document.body.style.overflow = "";
        };
    }, [onClose]);

    useEffect(() => {
        setLoading(true);
        setOpenId(null);
        fetch(`${API_BASE}/shows/?year=${year}`)
            .then(r => r.json())
            .then(data => setEvents(Array.isArray(data) ? data : (data.results ?? [])))
            .catch(() => setEvents([]))
            .finally(() => setLoading(false));
    }, [year]);

    const toggle = (e: ShowEvent) => {
        if (getStatus(e) !== "done") return;
        if (openId === e.id) {
            setOpenId(null);
            return;
        }
        setOpenId(e.id);
        if (!resultsById[e.id]) {
            setLoadingId(e.id);
            fetch(`${API_BASE}/shows/${e.id}/results/`)
                .then(r => r.json())
                .then(data => setResultsById(prev => ({
                    ...prev,
                    [e.id]: Array.isArray(data) ? data : (data.results ?? []),
                })))
                .catch(() => setResultsById(prev => ({...prev, [e.id]: []})))
                .finally(() => setLoadingId(null));
        }
    };

    return (
        <div
            className="slm-backdrop"
            onClick={e => e.target === e.currentTarget && onClose()}
            role="dialog"
            aria-modal="true"
            aria-label="Список выставок"
        >
            <div className="slm-modal">

                <div className="slm-header">
                    <p className="slm-title">Список выставок</p>
                    <button className="slm-close" onClick={onClose} aria-label="Закрыть">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                             stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                            <line x1="18" y1="6" x2="6" y2="18"/>
                            <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>

                <div className="rt-year-tabs slm-year-tabs" role="tablist" aria-label="Год рейтинга">
                    {YEARS.map(y => (
                        <button key={y} role="tab" aria-selected={year === y}
                                className={`rt-year-tab${year === y ? " is-active" : ""}`}
                                onClick={() => setYear(y)}>
                            {y}
                        </button>
                    ))}
                </div>

                <div className="slm-body">
                    {loading && (
                        <div className="rt-shows-loading">
                            <span className="rt-spinner"/>
                            Загрузка…
                        </div>
                    )}

                    {!loading && events.length === 0 && (
                        <p className="rt-shows-empty" style={{textAlign: "center"}}>Нет данных за {year} год</p>
                    )}

                    {!loading && events.length > 0 && (
                        <div className="rt-shows-list">
                            {events.map(e => {
                                const status = getStatus(e);
                                const isOpen = openId === e.id;
                                return (
                                    <div key={e.id} className="slm-event">
                                        <div
                                            className={`slm-show-item${status === "done" ? " slm-show-item--clickable" : ""}`}
                                            onClick={() => toggle(e)}
                                            role={status === "done" ? "button" : undefined}
                                        >
                                            <div className="rt-show-event">
                                                <span className="rt-show-date">{fmtDate(e.event_date)}</span>
                                                <span className="rt-show-name">{e.title}</span>
                                                {(e.organizer || e.city) && (
                                                    <span className="rt-show-type">
                                                        {[e.organizer, e.city].filter(Boolean).join(" · ")}
                                                    </span>
                                                )}
                                            </div>

                                            <div className="slm-status-slot">
                                                {status === "done" && (
                                                    <svg className={`rt-chevron${isOpen ? " rt-chevron--up" : ""}`}
                                                         width="18" height="18" viewBox="0 0 24 24" fill="none"
                                                         stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                                                        <polyline points="6 9 12 15 18 9"/>
                                                    </svg>
                                                )}
                                                {status === "unavailable" && (
                                                    <span className="slm-status">Результаты недоступны</span>
                                                )}
                                            </div>
                                        </div>

                                        {isOpen && (
                                            <div className="slm-expand">
                                                {loadingId === e.id && (
                                                    <div className="rt-shows-loading">
                                                        <span className="rt-spinner"/>
                                                        Загрузка результатов…
                                                    </div>
                                                )}
                                                {loadingId !== e.id && (resultsById[e.id] ?? []).length === 0 && (
                                                    <p className="rt-shows-empty">Нет данных</p>
                                                )}
                                                {loadingId !== e.id && groupByClass(resultsById[e.id] ?? []).map(section => (
                                                    <div key={section.label} className="slm-section">
                                                        <p className="slm-section-title">{section.label}</p>
                                                        <div className="slm-dog-list">
                                                            {section.items.map(r => (
                                                                <div key={r.id} className="slm-dog-item">
                                                                    <DogAvatar
                                                                        dog_photo={r.dog.dog_photo}
                                                                        photo_url={r.dog.photo_url}
                                                                        alt={getName(r.dog)}
                                                                        size={40}
                                                                        wrapClassName="rt-avatar-wrap"
                                                                        className="rt-avatar-img"
                                                                    />
                                                                    <div className="slm-dog-main">
                                                                        <Link to={`/archive/dog/${r.dog.id}`}
                                                                              className="slm-dog-name rt-dog-link"
                                                                              onClick={onClose}>
                                                                            {getName(r.dog)}
                                                                        </Link>
                                                                        {r.grade && (
                                                                            <p className="slm-dog-grade">{r.grade}</p>
                                                                        )}
                                                                        {r.titles_won && (
                                                                            <div className="slm-dog-badges">
                                                                                {r.titles_won.split(",").map(t => (
                                                                                    <span key={t}
                                                                                          className="rt-badge">{t.trim()}</span>
                                                                                ))}
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function groupByClass(results: EventResult[]) {
    const byClass = new Map<string, EventResult[]>();
    for (const r of results) {
        const key = r.show_class || "Без класса";
        const list = byClass.get(key) ?? [];
        list.push(r);
        byClass.set(key, list);
    }
    return Array.from(byClass.entries()).map(([label, items]) => ({label, items}));
}
