// src/components/ShowResultsModal/ShowResultsModal.tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "./ShowResultsModal.css";
import { dogPhoto, DEFAULT_DOG_IMG } from "@/utils/dogPhoto";
const API_BASE = "/api";


const SHOW_LABELS: Record<string, string> = {
  pk: "Монопородная ПК",
  kchk: "Монопородная КЧК",
  speciality: "Специализированная",
  sport: "Соревнование",
  world: "World / Euro Dog Show",
  other: "Выставка",
};

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

interface DogInfo {
  id: number;
  name: string;
  photo_url: string | null;
  dog_photo: string | null;
  points: number;
}

interface Props {
  dog: DogInfo;
  year: number;
  onClose: () => void;
}

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric", month: "long", year: "numeric",
  });

export function ShowResultsModal({ dog, year, onClose }: Props) {
  const [results, setResults] = useState<ShowResult[] | null>(null);

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

  // Загрузка выступлений
  useEffect(() => {
    fetch(`${API_BASE}/dogs/${dog.id}/show_results/?year=${year}`)
      .then(r => r.json())
      .then(data => {
        const list = Array.isArray(data) ? data : (data.results ?? []);
        setResults(list as ShowResult[]);
      })
      .catch(() => setResults([]));
  }, [dog.id, year]);

  const total = results?.reduce((sum, r) => sum + r.rating_points, 0) ?? 0;

  return (
    <div
      className="srm-backdrop"
      onClick={e => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-label={`Выступления ${dog.name}`}
    >
      <div className="srm-modal">
        {/* Шапка */}
        <div className="srm-header">
          <div className="srm-dog-info">
            <div className="srm-dog-avatar">
              {(dog.dog_photo || dog.photo_url)?.startsWith("http") ? (
                <img
                  src={dogPhoto(dog.dog_photo, dog.photo_url)}
                  alt={dog.name}
                  onError={e => { (e.target as HTMLImageElement).src = DEFAULT_DOG_IMG; }}
                />
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                  <circle cx="12" cy="8" r="4" />
                  <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
                </svg>
              )}
            </div>
            <div>
              <Link to={`/archive/dog/${dog.id}`} className="srm-dog-name" onClick={onClose}>
                {dog.name}
              </Link>
              <p className="srm-dog-sub">
                Рейтинговый год {year} · <strong>{dog.points}</strong> баллов
              </p>
            </div>
          </div>
          <button className="srm-close" onClick={onClose} aria-label="Закрыть">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Тело */}
        <div className="srm-body">
          {results === null && (
            <div className="srm-loading">
              <span className="srm-spinner" />
              Загрузка выступлений…
            </div>
          )}

          {results !== null && results.length === 0 && (
            <div className="srm-empty">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
                stroke="var(--border-light)" strokeWidth="1.2">
                <rect x="3" y="4" width="18" height="18" rx="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
              <p>Нет выступлений за {year} год</p>
            </div>
          )}

          {results !== null && results.length > 0 && (
            <>
              {/* Итого */}
              <div className="srm-summary">
                <span>{results.length} выступлений</span>
                <span className="srm-summary-pts">
                  Итого: <strong>{total}</strong> баллов
                </span>
              </div>

              {/* Список */}
              <div className="srm-list">
                {results.map(r => (
                  <div key={r.id} className="srm-item">
                    <div className="srm-item-date">
                      {fmtDate(r.event_date)}
                    </div>

                    <div className="srm-item-main">
                      <p className="srm-item-title">{r.event_title}</p>
                      <div className="srm-item-meta">
                        {r.show_type && r.show_type !== "other" && (
                          <span className="srm-tag srm-tag--type">
                            {SHOW_LABELS[r.show_type] ?? r.show_type}
                          </span>
                        )}
                        {r.show_class && (
                          <span className="srm-tag">Класс: {r.show_class}</span>
                        )}
                        {r.grade && (
                          <span className="srm-tag">
                            {r.grade}{r.place ? `, ${r.place} место` : ""}
                          </span>
                        )}
                      </div>
                      {r.titles_won && (
                        <div className="srm-badges">
                          {r.titles_won.split(",").map(t => (
                            <span key={t} className="srm-badge">{t.trim()}</span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="srm-item-pts">
                      {r.rating_points > 0 ? (
                        <>
                          <span className="srm-pts-num">+{r.rating_points}</span>
                          <span className="srm-pts-label">балл{r.rating_points === 1 ? "" : "ов"}</span>
                        </>
                      ) : (
                        <span className="srm-pts-zero">—</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
