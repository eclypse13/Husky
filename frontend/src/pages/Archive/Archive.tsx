// src/pages/Archive/Archive.tsx
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { useDogsList, useDogsStatsRetrieve } from "@/generated/dogs/dogs";
import type { DogList } from "@/generated/api.schemas";
import "./Archive.css";

// Хелперы
const sexLabel = (sex: number) => (sex === 1 ? "♂ Кобель" : sex === 2 ? "♀ Сука" : "—");

const PLACEHOLDER_URLS = ["https://zooportal.pro/images/logo1.png"];
const DEFAULT_DOG_IMG = "/no-image-dog.png";
const dogPhoto = (url: string | null | undefined): string =>
  url && !PLACEHOLDER_URLS.includes(url) ? url : DEFAULT_DOG_IMG;

const titleBadges = (dog: DogList) => {
  const badges: string[] = [];
  if (dog.prefix_titles) badges.push(...dog.prefix_titles.split(",").map((s) => s.trim()));
  if (dog.suffix_titles) badges.push(...dog.suffix_titles.split(",").map((s) => s.trim()));
  return badges.filter(Boolean);
};

export default function Archive() {
  const pageRef = useRef<HTMLDivElement | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [advOpen, setAdvOpen] = useState(false);

  // Состояние поиска (из URL)
  const query = searchParams.get("q") || "";
  const sexFilter = searchParams.get("sex") || "";
  const currentPage = Number(searchParams.get("page")) || 1;

  // Локальные инпуты (синхронизируются с URL при сабмите)
  const [queryInput, setQueryInput] = useState(query);
  const [sexInput, setSexInput] = useState(sexFilter);

  // Расширенный поиск
  const [advKennel, setAdvKennel] = useState("");
  const [advCountry, setAdvCountry] = useState("");
  const [advYearFrom, setAdvYearFrom] = useState("");
  const [advYearTo, setAdvYearTo] = useState("");

  const PER_PAGE = 20;

  // ============================================================
  // Данные через сгенерированные хуки
  // ============================================================
  const { data: statsResponse } = useDogsStatsRetrieve();
  const stats = statsResponse?.data;

  const { data: dogsResponse, isLoading: loading, error: fetchError } = useDogsList({
    page: currentPage,
    ...(query ? { q: query } : {}),
    ...(sexFilter ? { sex: Number(sexFilter) } : {}),
  });

  const dogs = dogsResponse?.data?.results ?? [];
  const totalDogs = dogsResponse?.data?.count ?? 0;
  const totalPages = Math.ceil(totalDogs / PER_PAGE);
  const error = fetchError ? "Ошибка поиска" : null;

  // ============================================================
  // Обработчики
  // ============================================================
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const p = new URLSearchParams();
    if (queryInput) p.set("q", queryInput);
    if (sexInput) p.set("sex", sexInput);
    p.set("page", "1");
    setSearchParams(p);
  };

  const handleAdvSearch = () => {
    const p = new URLSearchParams();
    if (queryInput) p.set("q", queryInput);
    if (sexInput) p.set("sex", sexInput);
    p.set("page", "1");
    setSearchParams(p);
    setAdvOpen(false);
  };

  const handlePageChange = (page: number) => {
    const p = new URLSearchParams(searchParams);
    p.set("page", String(page));
    setSearchParams(p);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Анимация появления
  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;
    const els = root.querySelectorAll<HTMLElement>(
      ".archive-search-section, .archive-stats .archive-stat, .archive-dog-card, .archive-sidebar-card"
    );
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => e.isIntersecting && e.target.setAttribute("data-visible", "1")),
      { threshold: 0.12, rootMargin: "0px 0px -50px 0px" }
    );
    els.forEach((el) => {
      el.setAttribute("data-visible", "0");
      io.observe(el);
    });
    return () => io.disconnect();
  }, [dogs]);

  // ============================================================
  // РЕНДЕР
  // ============================================================
  return (
    <div ref={pageRef} className="archive-page">
      <Breadcrumb
        title="Породный архив"
        items={[{ label: "Главная", to: "/" }, { label: "Породный архив" }]}
      />

      <main className="archive-main">
        <div className="archive-container">
          {/* ПОИСК */}
          <section className="archive-search-section">
            <div className="archive-search-head">
              <h2 className="archive-search-title">Поиск собак</h2>
              <p className="archive-search-sub">
                Найдите информацию о любой собаке в нашей базе данных.
                {stats?.total != null && ` Более ${stats.total.toLocaleString("ru-RU")} записей.`}
              </p>
            </div>

            <form className="archive-search-form" onSubmit={handleSearch}>
              <input
                className="archive-search-input"
                placeholder="Введите кличку, рег. номер или клеймо..."
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
              />
              <button className="archive-search-btn" type="submit" disabled={loading}>
                {loading ? "⏳ Ищем..." : "🔍 Найти"}
              </button>
            </form>

            <div className="archive-filters">
              <select
                className="archive-filter"
                value={sexInput}
                onChange={(e) => setSexInput(e.target.value)}
              >
                <option value="">Все полы</option>
                <option value="1">Кобель</option>
                <option value="2">Сука</option>
              </select>
              <button
                type="button"
                className="archive-filter archive-filter--accent"
                onClick={() => setAdvOpen(true)}
              >
                🔧 Расширенный поиск
              </button>
            </div>
          </section>

          {/* СТАТИСТИКА */}
          <section className="archive-stats">
            {[
              {
                icon: "📊",
                num: stats?.total ?? "—",
                label: "Собак в архиве",
              },
              {
                icon: "♂",
                num: stats?.males ?? "—",
                label: "Кобелей",
              },
              {
                icon: "♀",
                num: stats?.females ?? "—",
                label: "Сук",
              },
              {
                icon: "🏠",
                num: stats?.breeders ?? "—",
                label: "Заводчиков",
              },
            ].map((s) => (
              <article key={s.label} className="archive-stat">
                <div className="archive-stat-icon">{s.icon}</div>
                <div className="archive-stat-number">
                  {typeof s.num === "number" ? s.num.toLocaleString("ru-RU") : s.num}
                </div>
                <div className="archive-stat-label">{s.label}</div>
              </article>
            ))}
          </section>

          {/* РЕЗУЛЬТАТЫ */}
          <section className="archive-results-grid">
            <div className="archive-results">
              <div className="archive-results-head">
                <h3>Результаты поиска</h3>
                <div className="archive-results-count">
                  Найдено: <strong>{totalDogs.toLocaleString("ru-RU")}</strong> собак
                </div>
              </div>

              {error && (
                <div className="archive-error">
                  ⚠️ {error}
                </div>
              )}

              {loading && (
                <div className="archive-loading">
                  Загрузка...
                </div>
              )}

              <div className="archive-dogs">
                {dogs.map((d) => (
                  <article key={d.id} className="archive-dog-card">
                    <div className="archive-dog-avatar">
                      <img
                        src={dogPhoto(d.photo_url)}
                        alt={d.display_name}
                        loading="lazy"
                        decoding="async"
                      />
                    </div>
                    <div className="archive-dog-info">
                      <h4 className="archive-dog-name">{d.display_name}</h4>
                      <div className="archive-dog-meta">
                        <span className="archive-dog-meta-item">{sexLabel(d.sex)}</span>
                        {d.color && <span className="archive-dog-meta-item capitalize-text">{d.color}</span>}
                        {d.breeder_names && (
                          <span className="archive-dog-meta-item">
                            🏠 {d.breeder_names}
                          </span>
                        )}
                      </div>
                      <div className="archive-dog-badges">
                        {titleBadges(d).map((b) => (
                          <span key={b} className="archive-badge archive-badge--champ">
                            {b}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="archive-dog-actions">
                      <Link to={`/archive/pedigree/${d.id}`} className="archive-btn archive-btn--primary">
                        Родословная
                      </Link>
                      <Link to={`/archive/dog/${d.id}`} className="archive-btn">
                        Подробнее
                      </Link>
                    </div>
                  </article>
                ))}

                {!loading && dogs.length === 0 && !error && (
                  <div className="archive-empty">
                    Собаки не найдены. Попробуйте изменить параметры поиска.
                  </div>
                )}
              </div>

              {/* ПАГИНАЦИЯ */}
              {totalPages > 1 && (
                <div className="archive-pagination">
                  <button
                    className="archive-page-btn"
                    disabled={currentPage <= 1}
                    onClick={() => handlePageChange(currentPage - 1)}
                  >
                    « Пред
                  </button>

                  {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                    let page: number;
                    if (totalPages <= 7) {
                      page = i + 1;
                    } else if (currentPage <= 4) {
                      page = i + 1;
                    } else if (currentPage >= totalPages - 3) {
                      page = totalPages - 6 + i;
                    } else {
                      page = currentPage - 3 + i;
                    }
                    return (
                      <button
                        key={page}
                        className={`archive-page-btn ${page === currentPage ? "is-active" : ""}`}
                        onClick={() => handlePageChange(page)}
                      >
                        {page}
                      </button>
                    );
                  })}

                  <button
                    className="archive-page-btn"
                    disabled={currentPage >= totalPages}
                    onClick={() => handlePageChange(currentPage + 1)}
                  >
                    След »
                  </button>
                </div>
              )}
            </div>

            {/* САЙДБАР */}
            <aside className="archive-sidebar">
              <div className="archive-sidebar-card">
                <h3 className="archive-sidebar-title">🚀 Быстрые ссылки</h3>
                <nav className="archive-ql">
                  {[
                    { icon: "📊", t: "Породный рейтинг", s: "Топ собаки породы", to: "#" },
                    { icon: "🏆", t: "Чемпионы", s: "Новые титулы", to: "#" },
                    { icon: "📈", t: "Статистика породы", s: "Аналитика", to: "#" },
                  ].map((i) => (
                    <Link to={i.to} key={i.t} className="archive-ql-item">
                      <div className="archive-ql-icon">{i.icon}</div>
                      <div>
                        <div className="archive-ql-title">{i.t}</div>
                        <div className="archive-ql-sub">{i.s}</div>
                      </div>
                    </Link>
                  ))}
                </nav>
              </div>
              <a href="https://siberianhusky.breedarchive.com/home/index" className="archive-partner-link" target="_blank" rel="noopener noreferrer">
                <div className="archive-sidebar-card">
                  <h3 className="archive-sidebar-title">🔗 Партнёры</h3>
                  <div className="archive-partner">
                    <div className="archive-partner-tile">
                      <div className="archive-partner-emoji">🌐</div>
                      <div className="archive-partner-name">breedarchive.com</div>
                      <div className="archive-partner-sub">Глобальная база родословных</div>
                    </div>
                  </div>
                </div>
              </a>
            </aside>
          </section>
        </div>
      </main>

      {/* МОДАЛКА РАСШИРЕННОГО ПОИСКА */}
      {advOpen && (
        <div className="archive-modal" onClick={() => setAdvOpen(false)}>
          <div className="archive-modal-inner" onClick={(e) => e.stopPropagation()}>
            <div className="archive-modal-head">
              <h3>Расширенный поиск</h3>
              <button className="archive-modal-close" onClick={() => setAdvOpen(false)}>
                ×
              </button>
            </div>

            <div className="archive-form-grid">
              <label className="archive-field">
                <span>Кличка</span>
                <input value={queryInput} onChange={(e) => setQueryInput(e.target.value)} />
              </label>
              <label className="archive-field">
                <span>Питомник</span>
                <input value={advKennel} onChange={(e) => setAdvKennel(e.target.value)} />
              </label>
              <label className="archive-field">
                <span>Страна</span>
                <input value={advCountry} onChange={(e) => setAdvCountry(e.target.value)} />
              </label>
              <label className="archive-field">
                <span>Год рождения от</span>
                <input
                  type="number"
                  value={advYearFrom}
                  onChange={(e) => setAdvYearFrom(e.target.value)}
                  placeholder="2015"
                />
              </label>
              <label className="archive-field">
                <span>Год рождения до</span>
                <input
                  type="number"
                  value={advYearTo}
                  onChange={(e) => setAdvYearTo(e.target.value)}
                  placeholder="2024"
                />
              </label>
              <label className="archive-field">
                <span>Пол</span>
                <select value={sexInput} onChange={(e) => setSexInput(e.target.value)}>
                  <option value="">Любой</option>
                  <option value="1">Кобель</option>
                  <option value="2">Сука</option>
                </select>
              </label>
            </div>

            <div className="archive-modal-actions">
              <button
                className="archive-btn"
                onClick={() => {
                  setQueryInput("");
                  setSexInput("");
                  setAdvKennel("");
                  setAdvCountry("");
                  setAdvYearFrom("");
                  setAdvYearTo("");
                }}
              >
                Очистить
              </button>
              <button className="archive-btn archive-btn--primary" onClick={handleAdvSearch}>
                Найти
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
