import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./AllPuppies.css";

export default function AllPuppies() {
  const pageRef = useRef<HTMLDivElement | null>(null);

  // reveal-анимация секций
  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;
    const prefersReduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const els = root.querySelectorAll<HTMLElement>(
      ".puppies-section, .puppy-card, .stat-card, .sidebar-card"
    );

    if (prefersReduced) {
      els.forEach((el) => el.setAttribute("data-visible", "1"));
      return;
    }

    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && e.target.setAttribute("data-visible", "1")),
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );

    els.forEach((el) => {
      el.setAttribute("data-visible", "0");
      io.observe(el);
    });

    return () => io.disconnect();
  }, []);

  const litter = {
    kennel: "Silver Snow",
    city: "Москва",
    dob: "20.06.2025",
    sire: "Storm ♂",
    dam: "Ice Queen ♀",
    puppies: [
      { id: "p1", name: "Arctic Jewel", sex: "♀", img: "https://siberians.ru/assets/img/yasen-s.jpg" },
      { id: "p2", name: "Ice Runner", sex: "♂", img: "https://siberians.ru/assets/img/yasen-s.jpg" },
    ],
  };

  return (
    <div ref={pageRef} className="puppies-page">
      <Breadcrumb title="Все помёты" items={[{ label: "Главная", to: "/" }, { label: "Все помёты" }]} />

      <main className="puppies-main">
        <div className="puppies-container">
          <div className="puppies-grid">
            {/* Левая колонка — выбранный помёт + статистика */}
            <div className="puppies-col">
              <section className="puppies-section puppies-litter" id="selected-litter">
                <h3 className="puppies-litter-title">Питомник {litter.kennel} ({litter.city})</h3>
                <p className="puppies-meta">Дата рождения: {litter.dob}</p>
                <p className="puppies-meta">Родители: <strong>{litter.sire} × {litter.dam}</strong></p>

                <div className="puppies-kids-row">
                  {litter.puppies.map((p) => (
                    <div key={p.id} className="puppy-mini">
                      <img src={p.img} alt={p.name} loading="lazy" decoding="async" />
                      <div className="puppy-mini-name">🐶 {p.name} {p.sex}</div>
                    </div>
                  ))}
                </div>

                {/* Родословная 3 колена (упрощённый макет из HTML) */}
                <div className="pedigree-block">
                  <h4 className="pedigree-title">🧬 Родословная (3 колена)</h4>
                  <div className="pedigree-grid">
                    {[
                      { name: "Storm ♂", role: "Отец", ring: "blue" },
                      { name: "Arctic King ♂", role: "Дед по отцу" },
                      { name: "Snow Queen ♀", role: "Бабка по отцу" },
                      { name: "Ice Queen ♀", role: "Мать", ring: "orange" },
                      { name: "Polar Knight ♂", role: "Дед по матери" },
                      { name: "Frost Mistress ♀", role: "Бабка по матери" },
                    ].map((x, i) => (
                      <div key={i} className="pedigree-item">
                        <img
                          src={`https://via.placeholder.com/120x120?text=${encodeURIComponent(x.name)}`}
                          alt={x.name}
                          style={x.ring ? { borderColor: x.ring === "blue" ? "#3b82f6" : "#f59e0b" } : undefined}
                        />
                        <div className="pedigree-name"><strong>{x.name}</strong></div>
                        <div className="pedigree-role">{x.role}</div>
                      </div>
                    ))}
                  </div>

                  <div className="pedigree-cta">
                    <a className="pill-btn pill-btn--primary" href="#">📄 Скачать родословную PDF</a>
                  </div>
                </div>
              </section>

              <section className="stats-grid">
                {[
                  { icon: "🏠", number: "2", label: "Размер помёта", trend: "1 сука, 1 кобель" },
                  { icon: "🐶", number: "20.06", label: "Дата рождения", trend: "Возраст 1 месяц" },
                  { icon: "🧬", number: "ч/б × с/б", label: "Окрас родителей", trend: "Смотреть родословную" },
                  { icon: "📃", number: "Silver Snow", label: "Питомник", trend: <Link to="#">О питомнике</Link> },
                ].map((s, i) => (
                  <div key={i} className="stat-card">
                    <div className="stat-icon" aria-hidden>{s.icon}</div>
                    <div className="stat-number">{s.number}</div>
                    <div className="stat-label">{s.label}</div>
                    <div className="stat-trend">{s.trend}</div>
                  </div>
                ))}
              </section>
            </div>

            {/* Правая колонка — поиск + результаты */}
            <div className="puppies-col">
              <section className="puppies-section search-section">
                <div className="search-header">
                  <h2 className="search-title">Поиск по доступным помётам</h2>
                  <p className="search-subtitle">Используйте фильтры, чтобы найти щенков, соответствующих вашим критериям</p>
                </div>

                <form className="filters-row" onSubmit={(e) => e.preventDefault()}>
                  {[
                    "Питомник","Наличие","Возраст","Окрас","Глаза","С фото"
                  ].map((label, idx) => (
                    <select key={idx} className="filter-select" defaultValue="">
                      <option value="" disabled>{label}</option>
                      <option>Опция 1</option>
                      <option>Опция 2</option>
                    </select>
                  ))}
                </form>

                <div className="search-cta-row">
                  <button type="button" className="search-button">🔍 Найти</button>
                  <button type="button" className="search-button search-button--soft">🔄 Сбросить</button>
                </div>
              </section>

              <section className="puppies-section results-section">
                <div className="search-header">
                  <h2 className="search-title">Найденные помёты</h2>
                  <p className="search-subtitle">Выберите интересующий помёт из списка для просмотра подробностей</p>
                </div>

                <ul className="results-list" role="list">
                  {[
                    {
                      img: "https://siberians.ru/pups/backxshanya/backxshanya.jpg",
                      title: "Silver Snow • д.р. 20.06.2025",
                      desc: "Storm × Ice Queen — 2 щенка",
                    },
                    {
                      img: "https://siberians.ru/pups/marshallxlady/marshallxlady.jpg",
                      title: "Aurora Pack • д.р. 12.07.2025",
                      desc: "Blaze × Northern Light — 3 щенка",
                    },
                  ].map((r, i) => (
                    <li key={i} className="result-item">
                      <img src={r.img} alt={r.title} loading="lazy" decoding="async" />
                      <div className="result-text">
                        <strong>{r.title}</strong>
                        <div>{r.desc}</div>
                        <a className="result-link" href="#selected-litter">Посмотреть →</a>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}