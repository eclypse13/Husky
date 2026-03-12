// src/pages/Archive/Archive.tsx
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { searchDogs, getDogStats } from "@/api/dogs";
import type { DogListItem, DogStats, DogSearchParams } from "@/types/dog";
import "./Archive.css";

// Хелперы
const sexLabel = (sex: number) => (sex === 1 ? "♂ Кобель" : sex === 2 ? "♀ Сука" : "—");
const sexIcon = (sex: number) => (sex === 2 ? "🕊️" : "🐕");

const PLACEHOLDER_URLS = ["https://zooportal.pro/images/logo1.png"];
const DEFAULT_DOG_IMG = "/no-image-dog.png";
const dogPhoto = (url: string | null | undefined): string =>
  url && !PLACEHOLDER_URLS.includes(url) ? url : DEFAULT_DOG_IMG;

const titleBadges = (dog: DogListItem) => {
  const badges: string[] = [];
  if (dog.prefix_titles) badges.push(...dog.prefix_titles.split(",").map((s) => s.trim()));
  if (dog.suffix_titles) badges.push(...dog.suffix_titles.split(",").map((s) => s.trim()));
  return badges.filter(Boolean);
};

export default function Archive() {
  const pageRef = useRef<HTMLDivElement | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [advOpen, setAdvOpen] = useState(false);

  // Состояние поиска
  const [query, setQuery] = useState(searchParams.get("q") || "");
  const [sexFilter, setSexFilter] = useState(searchParams.get("sex") || "");
  const [colorFilter, setColorFilter] = useState(searchParams.get("color") || "");
  const [currentPage, setCurrentPage] = useState(Number(searchParams.get("page")) || 1);

  // Расширенный поиск
  const [advKennel, setAdvKennel] = useState("");
  const [advCountry, setAdvCountry] = useState("");
  const [advYearFrom, setAdvYearFrom] = useState("");
  const [advYearTo, setAdvYearTo] = useState("");

  // Данные
  const [dogs, setDogs] = useState<DogListItem[]>([]);
  const [totalDogs, setTotalDogs] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<DogStats | null>(null);

  // ============================================================
  // Загрузка статистики (один раз)
  // ============================================================
  useEffect(() => {
    getDogStats()
      .then(setStats)
      .catch(() => {});
  }, []);

  // ============================================================
  // Поиск собак
  // ============================================================
  const doSearch = useCallback(
    async (params: DogSearchParams, page = 1) => {
      setLoading(true);
      setError(null);

      try {
        const result = await searchDogs({ ...params, page, per_page: 20 });
        setDogs(result.data);
        setTotalDogs(result.meta.total);
        setTotalPages(result.meta.total_pages);
        setCurrentPage(result.meta.page);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Ошибка поиска");
        setDogs([]);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Начальная загрузка + реакция на URL
  useEffect(() => {
    const params: DogSearchParams = {};
    const q = searchParams.get("q");
    const sex = searchParams.get("sex");
    const color = searchParams.get("color");
    const page = Number(searchParams.get("page")) || 1;

    if (q) params.q = q;
    if (sex) params.sex = sex;
    if (color) params.color = color;

    doSearch(params, page);
  }, [searchParams, doSearch]);

  // ============================================================
  // Обработчики
  // ============================================================
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const p = new URLSearchParams();
    if (query) p.set("q", query);
    if (sexFilter) p.set("sex", sexFilter);
    if (colorFilter) p.set("color", colorFilter);
    p.set("page", "1");
    setSearchParams(p);
  };

  const handleAdvSearch = () => {
    const params: DogSearchParams = { q: query };
    if (sexFilter) params.sex = sexFilter;
    if (colorFilter) params.color = colorFilter;
    if (advKennel) params.kennel = advKennel;
    if (advCountry) params.country = advCountry;
    if (advYearFrom) params.year_from = advYearFrom;
    if (advYearTo) params.year_to = advYearTo;

    setAdvOpen(false);
    doSearch(params, 1);
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
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <button className="archive-search-btn" type="submit" disabled={loading}>
                {loading ? "⏳ Ищем..." : "🔍 Найти"}
              </button>
            </form>

            <div className="archive-filters">
              <select
                className="archive-filter"
                value={sexFilter}
                onChange={(e) => setSexFilter(e.target.value)}
              >
                <option value="">Все полы</option>
                <option value="1">Кобель</option>
                <option value="2">Сука</option>
              </select>
              <select
                className="archive-filter"
                value={colorFilter}
                onChange={(e) => setColorFilter(e.target.value)}
              >
                <option value="">Все окрасы</option>
                <option value="черно-белый">Черно-белый</option>
                <option value="серо-белый">Серо-белый</option>
                <option value="рыже-белый">Рыже-белый</option>
                <option value="белый">Белый</option>
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
                        {d.color && <span className="archive-dog-meta-item">{d.color}</span>}
                        {d.year_of_birth && (
                          <span className="archive-dog-meta-item">{d.year_of_birth} г.р.</span>
                        )}
                        {d.breeder_names.length > 0 && (
                          <span className="archive-dog-meta-item">
                            🏠 {d.breeder_names.join(", ")}
                          </span>
                        )}
                        {d.land_of_birth && (
                          <span className="archive-dog-meta-item">🌍 {d.land_of_birth}</span>
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
                <input value={query} onChange={(e) => setQuery(e.target.value)} />
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
                <select value={sexFilter} onChange={(e) => setSexFilter(e.target.value)}>
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
                  setQuery("");
                  setSexFilter("");
                  setColorFilter("");
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
