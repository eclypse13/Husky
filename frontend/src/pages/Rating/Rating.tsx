// src/pages/Rating/Rating.tsx
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import RatingSidebar from "@/components/Sidebar/RatingSidebar";
import { ShowResultsModal } from "@/components/ShowResultsModal/ShowResultsModal";
import "./Rating.css";
import {dogPhoto, DEFAULT_DOG_IMG} from "@/utils/dogPhoto";

const API_BASE = "/api";

const getRatingYear = () => {
  const d = new Date();
  return d.getMonth() === 11 ? d.getFullYear() + 1 : d.getFullYear();
};
const DEFAULT_YEAR = getRatingYear();
const YEARS = [DEFAULT_YEAR, DEFAULT_YEAR - 1, DEFAULT_YEAR - 2, DEFAULT_YEAR - 3];

const NOMINATIONS = [
  { key: "main",    label: "Лучший Хаски" },
  { key: "junior",  label: "Юниоры" },
  { key: "veteran", label: "Ветераны" },
  { key: "working", label: "Рабочие" },
];

interface DogRating {
  id: number; rank?: number;
  registered_name?: string; call_name?: string; display_name?: string; name?: string;
  photo_url: string | null; dog_photo: string | null; sex: number; sex_display?: string;
  kennel?: string | null; rating?: number; points?: number;
}

interface ModalDog {
  id: number; name: string; dog_photo: string | null; photo_url: string | null; points: number;
}

const getName = (d: DogRating) => d.registered_name || d.display_name || d.name || "—";
const getPts  = (d: DogRating) => d.points ?? d.rating ?? 0;

// ── Аватар ─────────────────────────────────────────────────────────────────────
function Avatar({ dog_photo, photoUrl, alt, size }: { dog_photo: string | null; photoUrl: string | null; alt: string; size: number }) {
  return (
    <div className="rt-avatar-wrap" style={{ width: size, height: size }}>
      <img
        src={dogPhoto(dog_photo, photoUrl)}
        alt={alt}
        loading="lazy"
        className="rt-avatar-img"
        onError={e => { (e.target as HTMLImageElement).src = DEFAULT_DOG_IMG; }}
      />
    </div>
  );
}

// ── Карточка подиума ───────────────────────────────────────────────────────────
function PodiumCard({ dog, rank, onShowResults }: {
  dog: DogRating; rank: number; onShowResults: (dog: DogRating) => void;
}) {
  return (
    <article className={`rating-card rt-podium-card rt-podium-card--top`}>
      <div className="rt-podium-rank">
        <span className={`rt-rank-badge rt-rank-badge--top`}>{rank}</span>
      </div>

      <div className="rt-podium-avatar"
        style={{ borderColor: "var(--accent-orange)" }}>
        <Avatar photo={dog.dog_photo} photoUrl={dog.photo_url} alt={getName(dog)} size={80} />
      </div>

      <Link to={`/archive/dog/${dog.id}`} className="rating-card-name rt-dog-link">
        {getName(dog)}
      </Link>
      <p className="rating-card-sub">
        {dog.sex === 1 ? "♂ Кобель" : dog.sex === 2 ? "♀ Сука" : dog.sex_display ?? ""}
      </p>
      <p className="rating-card-pts">
        <strong className="rt-pts-big">{getPts(dog)}</strong> баллов
      </p>

      <button className="rt-expand-btn" onClick={() => onShowResults(dog)}>
        Выступления
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
    </article>
  );
}

// ── Строка таблицы ─────────────────────────────────────────────────────────────
function RatingTableRow({ dog, rank, onShowResults }: {
  dog: DogRating; rank: number; onShowResults: (dog: DogRating) => void;
}) {
  return (
    <tr className="rt-tr" onClick={() => onShowResults(dog)}
      role="button" tabIndex={0}
      onKeyDown={e => (e.key === "Enter" || e.key === " ") && onShowResults(dog)}>
      <td className="rt-td-rank">
        <span className="rt-rank-badge">{rank}</span>
      </td>
      <td className="rt-td-avatar">
        <Avatar photo={dog.dog_photo} photoUrl={dog.photo_url} alt={getName(dog)} size={40} />
      </td>
      <td className="rt-td-name">
        <Link to={`/archive/dog/${dog.id}`} className="rt-dog-link"
          onClick={e => e.stopPropagation()}>
          {getName(dog)}
        </Link>
        {dog.kennel && <span className="rt-kennel">{dog.kennel}</span>}
      </td>
      <td className="rt-td-pts">
        <strong className="rt-pts">{getPts(dog)}</strong>
      </td>
      <td className="rt-td-toggle">
        <button className="rt-toggle-btn" aria-label="Показать выступления"
          onClick={e => { e.stopPropagation(); onShowResults(dog); }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </td>
    </tr>
  );
}

// ── Скелетон ───────────────────────────────────────────────────────────────────
function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <tr key={i} className="rt-tr rt-tr--skel" aria-hidden>
          <td><div className="rt-skel" style={{ width: 28, height: 28, borderRadius: "50%" }} /></td>
          <td><div className="rt-skel" style={{ width: 40, height: 40, borderRadius: "50%" }} /></td>
          <td>
            <div className="rt-skel" style={{ width: "60%", height: 14 }} />
            <div className="rt-skel" style={{ width: "35%", height: 11, marginTop: 5 }} />
          </td>
          <td><div className="rt-skel" style={{ width: 48, height: 18 }} /></td>
          <td />
        </tr>
      ))}
    </>
  );
}

// ── Главная страница ───────────────────────────────────────────────────────────
export default function Rating() {
  const pageRef = useRef<HTMLDivElement>(null);
  const [year,       setYear]       = useState(DEFAULT_YEAR);
  const [nomination, setNomination] = useState("main");
  const [dogs,       setDogs]       = useState<DogRating[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [modal,      setModal]      = useState<ModalDog | null>(null);

  const openModal = (dog: DogRating) => setModal({
    id:       dog.id,
    name:     getName(dog),
    photo_url: dog.photo_url,
    points:   getPts(dog),
  });

  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const els = root.querySelectorAll<HTMLElement>(".rating-section, .rating-card, .rsb__card");
    if (reduced) { els.forEach(el => el.setAttribute("data-visible", "1")); return; }
    const io = new IntersectionObserver(
      entries => entries.forEach(e => e.isIntersecting && e.target.setAttribute("data-visible", "1")),
      { threshold: 0.12, rootMargin: "0px 0px -50px 0px" }
    );
    els.forEach(el => { el.setAttribute("data-visible", "0"); io.observe(el); });
    return () => io.disconnect();
  }, [dogs]);

  useEffect(() => {
    setLoading(true);
    setDogs([]);
    fetch(`${API_BASE}/dogs/rating/?nomination=${nomination}&year=${year}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => setDogs(Array.isArray(data) ? data : (data.results ?? [])))
      .catch(() =>
        fetch(`${API_BASE}/dogs/?ordering=-rating`)
          .then(r => r.json())
          .then(data => {
            const list = (Array.isArray(data) ? data : (data.results ?? [])) as DogRating[];
            setDogs(list.filter(d => getPts(d) > 0).map((d, i) => ({ ...d, rank: i + 1 })));
          })
          .catch(() => setDogs([]))
      )
      .finally(() => setLoading(false));
  }, [year, nomination]);

  const podium   = dogs.slice(0, 3);
  const nomLabel = NOMINATIONS.find(n => n.key === nomination)?.label ?? "";

  return (
    <div ref={pageRef} className="rating-page">
      <Breadcrumb
        title="Породный рейтинг"
        items={[{ label: "Главная", to: "/" }, { label: "Породный рейтинг" }]}
      />

      <main className="rating-main">
        <div className="rating-container">
          <div className="rating-grid">
            <div className="rating-main-col">

              {/* Фильтры */}
              <section className="rating-section" aria-label="Фильтры рейтинга">
                <div className="rt-header-row">
                  <div>
                    <h1 className="rating-title">Породный рейтинг</h1>
                    <p className="rating-sub">
                      Официальный рейтинг НКП — учитываются монопородные
                      и специализированные выставки. Период: 1 декабря — 30 ноября.
                    </p>
                  </div>
                </div>

                <div className="rt-tabs-row">
                  <div className="rt-year-tabs" role="tablist" aria-label="Год рейтинга">
                    {YEARS.map(y => (
                      <button key={y} role="tab" aria-selected={year === y}
                        className={`rt-year-tab${year === y ? " is-active" : ""}`}
                        onClick={() => setYear(y)}>
                        {y}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="rt-nom-tabs" role="tablist" aria-label="Номинация">
                  {NOMINATIONS.map(n => (
                    <button key={n.key} role="tab" aria-selected={nomination === n.key}
                      className={`rt-nom-tab${nomination === n.key ? " is-active" : ""}`}
                      onClick={() => setNomination(n.key)}>
                      {n.label}
                    </button>
                  ))}
                </div>
              </section>

              {/* Подиум */}
              {!loading && podium.length > 0 && (
                <section className="rating-section" aria-label="Лидеры">
                  <h2 className="rating-title">
                    Лидеры · {year}
                    <span className="rt-nom-tag">{nomLabel}</span>
                  </h2>
                  <div className="rating-leaders-grid">
                    {podium.map((dog, i) => (
                      <PodiumCard key={`${dog.id}-${year}-${nomination}`}
                        dog={dog} rank={i + 1} onShowResults={openModal} />
                    ))}
                  </div>
                </section>
              )}

              {/* Таблица */}
              <section className="rating-section" aria-labelledby="rt-table-title">
                <div className="rt-table-header">
                  <h2 id="rt-table-title" className="rating-title">
                    Рейтинг {year}
                    <span className="rt-nom-tag">{nomLabel}</span>
                  </h2>
                </div>

                <div className="rating-table-wrap">
                  <table className="rating-table">
                    <thead>
                      <tr>
                        <th scope="col" style={{ width: 40 }}>#</th>
                        <th scope="col" style={{ width: 48 }} />
                        <th scope="col">Собака</th>
                        <th scope="col" style={{ width: 80 }}>Баллы</th>
                        <th scope="col" style={{ width: 40 }} />
                      </tr>
                    </thead>
                    <tbody>
                      {loading && <SkeletonRows />}

                      {!loading && dogs.length === 0 && (
                        <tr>
                          <td colSpan={5} className="rt-empty-cell">
                            <div className="rt-empty">
                              <p>Нет данных за {year} год</p>
                            </div>
                          </td>
                        </tr>
                      )}

                      {!loading && dogs.map((dog, i) => (
                        <RatingTableRow key={`${dog.id}-${year}-${nomination}`}
                          dog={dog} rank={i + 1} onShowResults={openModal} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

            </div>

            <RatingSidebar />
          </div>
        </div>
      </main>

      {/* Модалка выступлений */}
      {modal && (
        <ShowResultsModal
          dog={modal}
          year={year}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
}

