import { useEffect, useRef } from "react";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./News.css";

export default function News() {
  const pageRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;
    const els = root.querySelectorAll<HTMLElement>(
      ".news-search, .news-stat, .news-card"
    );
    const io = new IntersectionObserver(
      (entries) => entries.forEach(e => e.isIntersecting && e.target.setAttribute("data-visible", "1")),
      { threshold: 0.12, rootMargin: "0px 0px -50px 0px" }
    );
    els.forEach(el => { el.setAttribute("data-visible", "0"); io.observe(el); });
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    const nums = pageRef.current?.querySelectorAll<HTMLElement>(".news-stat-number");
    nums?.forEach(node => {
      const target = parseInt((node.dataset.target || "0").replace(/[^\d]/g, ""), 10);
      let cur = 0; const step = Math.max(1, Math.floor(target / 100));
      const t = setInterval(() => {
        cur += step;
        if (cur >= target) { cur = target; clearInterval(t); }
        node.textContent = cur.toLocaleString("ru-RU");
      }, 16);
    });
  }, []);

  return (
    <div ref={pageRef} className="news-page">
      <Breadcrumb
        title="Новости"
        items={[{ label: "Главная", to: "/" }, { label: "Новости" }]}
      />

      <main className="news-main">
        <div className="news-container">
          {/* Поиск */}
          <section className="news-search">
            <div className="news-search-head">
              <h2 className="news-title">Все новости</h2>
              <p className="news-sub">
                Будьте в курсе событий: новости о выставках, здоровье породы, спортивных стартах, образовании и достижениях членов клуба.
              </p>
            </div>

            <form
              className="news-search-form"
              onSubmit={(e) => { e.preventDefault(); /* сюда добавишь поиск */ }}
            >
              <input className="news-input" placeholder="Поиск по заголовку или ключевым словам…" />
              <button className="news-btn news-btn--primary">🔍 Найти</button>
            </form>

            <div className="news-filters">
              <select className="news-select">
                <option>Все категории</option>
                <option>Выставки</option><option>Здоровье</option>
                <option>Спорт</option><option>Образование</option><option>Достижения</option>
              </select>
              <select className="news-select">
                <option>Год</option>
                <option>2025</option><option>2024</option><option>2023</option><option>Архив до 2022</option>
              </select>
            </div>
          </section>

          {/* Статистика */}
          <section className="news-stats">
            {[
              { icon: "📰", num: "126", label: "Новостей всего", trend: "+8 за месяц" },
              { icon: "🏆", num: "42", label: "Про выставки", trend: "+2" },
              { icon: "🧬", num: "18", label: "Про здоровье", trend: "+1" },
              { icon: "❄️", num: "23", label: "Про спорт", trend: "+3" },
            ].map(s => (
              <article className="news-stat" key={s.label}>
                <div className="news-stat-icon">{s.icon}</div>
                <div className="news-stat-number" data-target={s.num}>{s.num}</div>
                <div className="news-stat-label">{s.label}</div>
                <div className="news-stat-trend">{s.trend}</div>
              </article>
            ))}
          </section>

          {/* Карточки новостей */}
          <section className="news-list">
            {[
              {
                icon: "🏆",
                title: "«Сибирская Красота 2025» — рекордное участие",
                meta: ["Выставки", "18 июля 2025"],
                desc: "200+ собак, международные судьи и высокий уровень организации.",
                cta: "Читать",
              },
              {
                icon: "🧬",
                title: "Обновлён список ДНК-тестов",
                meta: ["Здоровье", "15 июля 2025"],
                desc: "Добавлены панели тестов от Embark и Genomia.",
                cta: "Подробнее",
              },
              {
                icon: "❄️",
                title: "Итоги чемпионата по драйленду",
                meta: ["Спорт", "12 июля 2025"],
                desc: "Поздравляем победителей! Результаты, фото и комментарии участников.",
                cta: "Смотреть",
              },
            ].map((n, i) => (
              <article className="news-card" key={i}>
                <div className="news-avatar">{n.icon}</div>
                <div className="news-info">
                  <h3 className="news-card-title">{n.title}</h3>
                  <div className="news-meta">
                    {n.meta.map(m => <span key={m} className="news-meta-item">{m}</span>)}
                  </div>
                  <p className="news-desc">{n.desc}</p>
                </div>
                <div className="news-actions">
                  <a className="news-action news-action--primary" href="#">{n.cta}</a>
                </div>
              </article>
            ))}
          </section>

          {/* Пагинация */}
          <nav className="news-pagination" aria-label="Pagination">
            <a className="news-page-btn" href="#prev">« Пред</a>
            <a className="news-page-btn is-active" href="#1">1</a>
            <a className="news-page-btn" href="#2">2</a>
            <a className="news-page-btn" href="#3">3</a>
            <span className="news-ellipsis">…</span>
            <a className="news-page-btn" href="#10">10</a>
            <a className="news-page-btn" href="#next">След »</a>
          </nav>
        </div>
      </main>
    </div>
  );
}
