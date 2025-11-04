import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./Archive.css";

export default function Archive() {
  const pageRef = useRef<HTMLDivElement | null>(null);
  const [advOpen, setAdvOpen] = useState(false);

  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    const els = root.querySelectorAll<HTMLElement>(
      ".archive-search-section, .archive-stats .archive-stat, .archive-dog-card, .archive-sidebar-card"
    );

    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && e.target.setAttribute("data-visible", "1")),
      { threshold: 0.12, rootMargin: "0px 0px -50px 0px" }
    );

    els.forEach((el) => {
      el.setAttribute("data-visible", "0");
      io.observe(el);
    });

    return () => io.disconnect();
  }, []);

  useEffect(() => {
    const nums = pageRef.current?.querySelectorAll<HTMLElement>(".archive-stat-number");
    if (!nums) return;

    nums.forEach((node) => {
      const raw = node.dataset.target || node.textContent || "0";
      const target = parseInt(raw.replace(/[^\d]/g, ""), 10);
      let cur = 0;
      const step = Math.max(1, Math.floor(target / 100));
      const t = setInterval(() => {
        cur += step;
        if (cur >= target) {
          cur = target;
          clearInterval(t);
        }
        node.textContent = cur.toLocaleString("ru-RU");
      }, 16);
    });
  }, []);

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
  };

  return (
    <div ref={pageRef} className="archive-page">
      <Breadcrumb
        title="Породный архив"
        items={[{ label: "Главная", to: "/" }, { label: "Породный архив" }]}
      />

      <main className="archive-main">
        <div className="archive-container">
          <section className="archive-search-section">
            <div className="archive-search-head">
              <h2 className="archive-search-title">Поиск собак</h2>
              <p className="archive-search-sub">
                Найдите информацию о любой собаке в нашей базе данных. Более 15,000 записей с родословными, здоровьем и достижениями.
              </p>
            </div>

            <form className="archive-search-form" onSubmit={onSearch}>
              <input
                className="archive-search-input"
                placeholder="Введите кличку, регистрационный номер или клеймо..."
              />
              <button className="archive-search-btn" type="submit">🔍 Найти</button>
            </form>

            <div className="archive-filters">
              <select className="archive-filter"><option value="">Все полы</option><option value="m">Кобель</option><option value="f">Сука</option></select>
              <select className="archive-filter"><option value="">Все окрасы</option><option>Черно-белый</option><option>Серо-белый</option><option>Соболино-белый</option><option>Рыже-белый</option><option>Белый</option></select>
              <select className="archive-filter"><option value="">Все титулы</option><option>Чемпион</option><option>Гранд Чемпион</option><option>Юный Чемпион</option><option>Ветеран Чемпион</option></select>
              <button type="button" className="archive-filter archive-filter--accent" onClick={() => setAdvOpen(true)}>🔧 Расширенный поиск</button>
            </div>
          </section>

          <section className="archive-stats">
            {[
              { icon: "📊", num: "15247", label: "Собак в архиве", trend: "+342 за месяц" },
              { icon: "🏆", num: "3891", label: "Чемпионов", trend: "+67 за месяц" },
              { icon: "🧬", num: "8456", label: "ДНК-тестов", trend: "+124 за месяц" },
              { icon: "📈", num: "95.3%", label: "Полнота данных", trend: "+2.1% за квартал" },
            ].map((s) => (
              <article key={s.label} className="archive-stat">
                <div className="archive-stat-icon">{s.icon}</div>
                <div className="archive-stat-number" data-target={s.num}>{s.num}</div>
                <div className="archive-stat-label">{s.label}</div>
                <div className="archive-stat-trend">{s.trend}</div>
              </article>
            ))}
          </section>

          <section className="archive-results-grid">
            <div className="archive-results">
              <div className="archive-results-head">
                <h3>Результаты поиска</h3>
                <div className="archive-results-count">Найдено: <strong>1 247</strong> собак</div>
              </div>

              <div className="archive-dogs">
                {[
                  { icon: "🐕", name: "Arctic Storm's Thunder King", meta: ["♂ Кобель", "Черно-белый", "5 лет", "RKF 4578123"], badges: ["Гранд Чемпион", "PRA Clear"] },
                  { icon: "🐕‍🦺", name: "Siberian Dream's Ice Walker", meta: ["♀ Сука", "Серо-белый", "3 года", "RKF 4679234"], badges: ["Чемпион", "SHOR Normal"] },
                  { icon: "🦮", name: "Northern Light's Aurora", meta: ["♀ Сука", "Рыже-белый", "7 лет", "RKF 4123567"], badges: ["Интер Чемпион", "Full Panel Clear"] },
                ].map((d) => (
                  <article key={d.name} className="archive-dog-card">
                    <div className="archive-dog-avatar">{d.icon}</div>
                    <div className="archive-dog-info">
                      <h4 className="archive-dog-name">{d.name}</h4>
                      <div className="archive-dog-meta">
                        {d.meta.map((m) => <span key={m} className="archive-dog-meta-item">{m}</span>)}
                      </div>
                      <div className="archive-dog-badges">
                        {d.badges.map((b) => <span key={b} className={`archive-badge ${/Clear|Normal|Panel/.test(b) ? "archive-badge--health" : "archive-badge--champ"}`}>{b}</span>)}
                      </div>
                    </div>
                    <div className="archive-dog-actions">
                      <Link to="#" className="archive-btn archive-btn--primary">Родословная</Link>
                      <Link to="#" className="archive-btn">Здоровье</Link>
                    </div>
                  </article>
                ))}
              </div>

              <div className="archive-pagination">
                <Link to="#" className="archive-page-btn">« Пред</Link>
                <Link to="#" className="archive-page-btn is-active">1</Link>
                <Link to="#" className="archive-page-btn">2</Link>
                <Link to="#" className="archive-page-btn">3</Link>
                <span className="archive-page-ellipsis">…</span>
                <Link to="#" className="archive-page-btn">25</Link>
                <Link to="#" className="archive-page-btn">След »</Link>
              </div>
            </div>

            <aside className="archive-sidebar">
              <div className="archive-sidebar-card">
                <h3 className="archive-sidebar-title">🚀 Быстрые ссылки</h3>
                <nav className="archive-ql">
                  {[
                    { icon: "📊", t: "Породный рейтинг", s: "Топ собаки породы" },
                    { icon: "🏆", t: "Чемпионы 2024", s: "Новые титулы" },
                    { icon: "🧬", t: "База ДНК-тестов", s: "Результаты генетики" },
                    { icon: "👁️", t: "SHOR реестр", s: "Офтальмология" },
                    { icon: "📈", t: "Статистика породы", s: "Аналитика" },
                  ].map((i) => (
                    <Link to="#" key={i.t} className="archive-ql-item">
                      <div className="archive-ql-icon">{i.icon}</div>
                      <div>
                        <div className="archive-ql-title">{i.t}</div>
                        <div className="archive-ql-sub">{i.s}</div>
                      </div>
                    </Link>
                  ))}
                </nav>
              </div>

              <div className="archive-sidebar-card">
                <h3 className="archive-sidebar-title">🔗 Партнёры</h3>
                <div className="archive-partner">
                  <div className="archive-partner-tile">
                    <div className="archive-partner-emoji">🌐</div>
                    <div className="archive-partner-name">breedarchive.com</div>
                    <div className="archive-partner-sub">Глобальная база родословных</div>
                  </div>
                  <Link to="#" className="archive-btn archive-btn--primary">Перейти к партнёру</Link>
                </div>

                <div className="archive-labs">
                  <h3 className="archive-sidebar-title">🧪 Лаборатории</h3>
                  <div className="archive-labs-list">
                    {["Genomia", "Embark Veterinary", "Laboklin", "ЗООГЕН"].map((x) => (
                      <Link to="#" key={x}>{x}</Link>
                    ))}
                  </div>
                </div>
              </div>

              <div className="archive-sidebar-card">
                <h3 className="archive-sidebar-title">📝 Добавить данные</h3>
                <p className="archive-note">
                  Помогите пополнить архив! Добавьте информацию о своей собаке
                  или обновите существующие данные.
                </p>
                <div className="archive-sidebar-actions">
                  <Link to="#" className="archive-btn archive-btn--primary">Добавить собаку</Link>
                  <Link to="#" className="archive-btn archive-btn--ghost">Обновить данные</Link>
                </div>
              </div>
            </aside>
          </section>
        </div>
      </main>

      {advOpen && (
        <div className="archive-modal" onClick={() => setAdvOpen(false)}>
          <div className="archive-modal-inner" onClick={(e) => e.stopPropagation()}>
            <div className="archive-modal-head">
              <h3>Расширенный поиск</h3>
              <button className="archive-modal-close" onClick={() => setAdvOpen(false)}>×</button>
            </div>

            <div className="archive-form-grid">
              {[
                "Кличка", "Рег. номер", "Клеймо / микрочип", "Питомник",
                "Отец", "Мать", "Год рождения", "Страна рождения"
              ].map((l, i) => (
                <label key={l} className="archive-field">
                  <span>{l}</span>
                  {i >= 6 ? (
                    <select><option>Любой</option></select>
                  ) : (
                    <input />
                  )}
                </label>
              ))}
            </div>

            <div className="archive-modal-actions">
              <button className="archive-btn" onClick={() => setAdvOpen(false)}>Очистить</button>
              <button className="archive-btn archive-btn--primary" onClick={() => setAdvOpen(false)}>
                Найти
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
