import { Link } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import "./Home.css";

/* Mock-данные */
const stats = [
  { label: "Членов клуба", value: 1250, plus: true },
  { label: "Питомников", value: 350, plus: true },
  { label: "Лет работы", value: 15, plus: true },
];

const news = [
  { id: 1, tag: "Выставки", date: "18 июля 2025", title: "«Сибирская красота 2025» — рекордное участие", excerpt: "В Москве прошла крупнейшая специализированная выставка сибирских хаски с участием более 200 собак из 15 стран. Эксперты из Финляндии отметили высокий уровень российского поголовья и прогресс в селекционной работе.", featured: true, link: "Читать полный отчет", icon: "🏆", to: "/news/1" },
  { id: 2, tag: "Здоровье", date: "15 июля 2025", title: "Новые генетические тесты", excerpt: "Расширена панель доступных тестов для породы...", link: "Подробнее", icon: "🧬", to: "/news/2" },
  { id: 3, tag: "Спорт", date: "12 июля 2025", title: "Чемпионат по драйленду", excerpt: "Старт летнего сезона ездового спорта...", link: "Результаты", icon: "❄️", to: "/news/3" },
  { id: 4, tag: "Образование", date: "10 июля 2025", title: "Семинар для судей", excerpt: "Обучающий семинар по породе...", link: "Регистрация", icon: "🎓", to: "/news/4" },
  { id: 5, tag: "Достижения", date: "8 июля 2025", title: "Новые чемпионы", excerpt: "Поздравляем владельцев собак...", link: "Список", icon: "🌟", to: "/news/5" },
];

const puppies = [
  { id: "p1", icon: "🐶", name: "Arctic Jewel", sex: "♀", dob: "20.06.2025", sire: "Storm ♂", dam: "Ice Queen ♀" },
  { id: "p2", icon: "🐕", name: "Northern Fire", sex: "♂", dob: "22.06.2025", sire: "Blaze ♂", dam: "Aurora ♀" },
  { id: "p3", icon: "🐾", name: "Blue Snowflake", sex: "♀", dob: "18.06.2025", sire: "Polar ♂", dam: "Elsa ♀" },
];

type Activity = { icon: string; text: string; time: string };
const initialActivity: Activity[] = [
  { icon: "🏆", text: "Arctic Storm's Thunder King получил статус Гранд Чемпион", time: "2 минуты назад" },
  { icon: "🐕", text: "Новый помёт в питомнике «Snowflake» — 6 щенков", time: "15 минут назад" },
  { icon: "🧬", text: "Добавлен результат ДНК-теста для Ice Walker", time: "1 час назад" },
  { icon: "📊", text: "Новая родословная в архиве — 4 поколения", time: "2 часа назад" },
];
const randomActivityPool: Activity[] = [
  { icon: "🎯", text: "Планирование вязки: найдена идеальная пара", time: "минут назад" },
  { icon: "📈", text: "Статистика здоровья породы обновлена", time: "часа назад" },
  { icon: "🌟", text: "Новый член клуба: питомник «Aurora Borealis»", time: "часов назад" },
];

/* Утилиты */
function useCounter(target: number, duration = 1600) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    let start: number | null = null;
    const step = (ts: number) => {
      if (start === null) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setValue(Math.floor(target * p));
      if (p < 1) requestAnimationFrame(step);
    };
    const id = requestAnimationFrame(step);
    return () => cancelAnimationFrame(id);
  }, [target, duration]);
  return value;
}

/* Компоненты */
function AnimatedBackground() {
  const shapesRef = useRef<Array<HTMLDivElement | null>>([]);

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY;
      shapesRef.current.forEach((el, i) => {
        if (!el) return;
        const speed = 0.5 + i * 0.1;
        el.style.transform = `translateY(${y * speed}px)`;
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="animated-bg" aria-hidden>
      <div className="floating-shapes">
        <div
          className="shape shape-1"
          ref={(el) => { shapesRef.current[0] = el; }}
        />
        <div
          className="shape shape-2"
          ref={(el) => { shapesRef.current[1] = el; }}
        />
        <div
          className="shape shape-3"
          ref={(el) => { shapesRef.current[2] = el; }}
        />
      </div>
    </div>
  );
}

function StatCard({ label, value, plus }: { label: string; value: number; plus?: boolean }) {
  const n = useCounter(value);
  return (
    <div className="stat-item">
      <div className="stat-number">{n}{plus ? "+" : ""}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function NewsCard({ item, featured }: { item: (typeof news)[number]; featured?: boolean }) {
  return (
    <article className={`news-card ${featured ? "featured" : ""}`}>
      <div className="news-image">{item.icon}</div>
      <div className="news-inner">
        <div className="news-meta">
          <span className="news-tag">{item.tag}</span>
          <span className="news-date">{item.date}</span>
        </div>
        <h3 className="news-title">{item.title}</h3>
        <p className="news-excerpt">{item.excerpt}</p>
        <Link to={item.to} className="feature-link">{item.link} →</Link>
      </div>
    </article>
  );
}

function ActivityFeed() {
  const [items, setItems] = useState<Activity[]>(initialActivity);

  useEffect(() => {
    const id = setInterval(() => {
      setItems((prev) => {
        const next = randomActivityPool[Math.floor(Math.random() * randomActivityPool.length)];
        const minutes = Math.floor(Math.random() * 30) + 1;
        const item = { ...next, time: `${minutes} ${next.time}` };
        return [item, ...prev].slice(0, 4);
      });
    }, 10000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const nodes = document.querySelectorAll<HTMLElement>(".home-page .activity-item");
    nodes.forEach((el, i) => {
      requestAnimationFrame(() => {
        setTimeout(() => el.classList.add("activity-item--visible"), i * 120);
      });
    });
  }, [items]);

  return (
    <div className="activity-feed">
      {items.map((a, i) => (
        <div key={i} className="activity-item">
          <div className="activity-avatar">{a.icon}</div>
          <div className="activity-text">
            <strong>{a.text}</strong>
            <div className="activity-time">{a.time}</div>
          </div>
        </div>
      ))}
      <div className="typing-indicator" style={{ marginTop: ".5rem" }}>
        <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
        <span>Обновления поступают…</span>
      </div>
    </div>
  );
}

/* Страница */
export default function Home() {
  const featured = useMemo(() => news.find((n) => n.featured)!, []);
  const others = useMemo(() => news.filter((n) => !n.featured).slice(0, 4), []);

  return (
    <div className="home-page">
      <AnimatedBackground />

      {/* HERO */}
      <section className="hero">
        <div className="hero-content">
          <div className="hero-text">
            <h2>Сибирские хаски<br />мирового класса</h2>
            <p className="hero-subtitle">
              Ведущий национальный клуб России, объединяющий заводчиков, владельцев и любителей породы сибирский хаски.
              Сохраняем традиции, развиваем будущее.
            </p>
            <div className="hero-buttons">
              <Link to="/archive" className="btn btn-primary">🔍 Найти собаку</Link>
              <Link to="/breed" className="btn btn-secondary">📚 О породе</Link>
            </div>

            <div className="hero-stats">
              {stats.map(s => <StatCard key={s.label} {...s} />)}
            </div>
          </div>

          <div className="hero-visual">
            <div className="hero-card">
              <div className="hero-image">🐕</div>
              <h3>Arctic Storm&apos;s Thunder King</h3>
              <p>Чемпион России 2023, Гранд Чемпион</p>
              <Link to="/pedigree/123" className="btn btn-primary">Посмотреть профиль</Link>
            </div>
          </div>
        </div>
      </section>

      {/* MAP */}
      <section className="interactive-map-section">
        <div className="map-content">
          <div className="section-header">
            <h2 className="section-title">Наша география</h2>
            <p className="section-subtitle">Питомники и члены клуба по всей России</p>
          </div>

          <div className="map-container">
            <div className="russia-map">
              <svg viewBox="0 0 1000 600" className="map-svg">
                <path d="M100,200 L200,180 L300,160 L400,140 L500,130 L600,125 L700,120 L800,125 L850,140 L900,160 L920,200 L900,250 L850,300 L800,350 L700,380 L600,400 L500,420 L400,430 L300,425 L200,410 L150,380 L100,320 Z"
                  fill="var(--ice-blue)" stroke="var(--bright-blue)" strokeWidth="2" />
                {[
                  { cx: 300, cy: 250, r: 12, t: "Москва — 45 питомников" },
                  { cx: 320, cy: 280, r: 10, t: "Санкт-Петербург — 28 питомников" },
                  { cx: 450, cy: 300, r: 8, t: "Екатеринбург — 15 питомников" },
                  { cx: 600, cy: 280, r: 7, t: "Новосибирск — 12 питомников" },
                  { cx: 750, cy: 250, r: 6, t: "Владивосток — 8 питомников" },
                  { cx: 400, cy: 200, r: 5, t: "Архангельск — 6 питомников" },
                ].map((p, i) => (
                  <circle key={i} cx={p.cx} cy={p.cy} r={p.r} className="kennel-point"
                    onClick={() => alert(`Информация: ${p.t}`)} />
                ))}
              </svg>
            </div>

            <div className="map-stats">
              {[
                { icon: "🏙️", value: 45, label: "Москва и МО" },
                { icon: "🏛️", value: 28, label: "Санкт-Петербург" },
                { icon: "🏔️", value: 89, label: "Другие регионы" },
              ].map(x => (
                <div key={x.label} className="region-stat">
                  <div className="stat-icon">{x.icon}</div>
                  <div>
                    <div className="stat-number">{x.value}</div>
                    <div className="stat-label">{x.label}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ACTIVITY */}
      <section className="activity-section">
        <div className="activity-content">
          <div className="section-header">
            <h2 className="section-title">Живая лента активности</h2>
            <p className="section-subtitle">Что происходит в мире хаски прямо сейчас</p>
          </div>
          <ActivityFeed />
        </div>
      </section>

      {/* FEATURES */}
      <section className="features">
        <div className="features-content">
          <div className="section-header">
            <h2 className="section-title">Всё для породы хаски</h2>
            <p className="section-subtitle">Комплексная экосистема для заводчиков, владельцев и любителей сибирских хаски</p>
          </div>

          <div className="features-grid">
            {[
              { icon: "📊", title: "Породный архив", desc: "15,000+ собак в базе данных с интерактивными родословными, результатами тестов здоровья и полной историей титулов.", link: "Перейти к архиву", to: "/archive" },
              { icon: "🧬", title: "Здоровье породы", desc: "Генетические тесты, офтальмологические обследования, реестры здоровья и инструменты для планирования вязок.", link: "Тестирование", to: "/health" },
              { icon: "🏆", title: "Выставки и спорт", desc: "Календарь мероприятий, результаты выставок, ездовой спорт, семинары и обучающие программы.", link: "Мероприятия", to: "/events" },
              { icon: "🤝", title: "Сообщество", desc: "Объединяем заводчиков и владельцев, обмениваемся опытом, поддерживаем новичков и развиваем породу вместе.", link: "Присоединиться", to: "/about" },
              { icon: "🎯", title: "Умные инструменты", desc: "AI-анализ совместимости, предиктивная аналитика наследственных заболеваний, компьютерное зрение для оценки экстерьера.", link: "Инновации", to: "/tools" },
              { icon: "🌐", title: "Интеграция", desc: "Партнерство с breedarchive.com, обмен данными с ведущими клубами мира, участие в глобальных проектах.", link: "Узнать больще", to: "/about" },
            ].map(f => (
              <div key={f.title} className="feature-card">
                <div className="feature-icon">{f.icon}</div>
                <h3 className="feature-title">{f.title}</h3>
                <p className="feature-description">{f.desc}</p>
                <Link to={f.to} className="feature-link">{f.link} →</Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* NEWS */}
      <section className="news-section">
        <div className="news-content">
          <div className="section-header">
            <h2 className="section-title">Последние новости</h2>
            <p className="section-subtitle">Будьте в курсе всех событий в мире сибирских хаски</p>
          </div>

          <div className="news-grid">
            <NewsCard item={featured} featured />
            {others.map(n => <NewsCard key={n.id} item={n} />)}
          </div>
        </div>
      </section>

      {/* PUPPIES */}
      <section className="features">
        <div className="features-content">
          <div className="section-header">
            <h2 className="section-title">🐾 Доступные щенки</h2>
            <p className="section-subtitle">Помёты от проверенных питомников — только от членов НКП. Щенки с родословной и заботой.</p>
          </div>

          <div className="features-grid">
            {puppies.map(p => (
              <div key={p.id} className="feature-card">
                <div className="feature-icon">{p.icon}</div>
                <h3 className="feature-title">{p.name}</h3>
                <p className="feature-description">
                  {p.sex}, род. {p.dob}<br />
                  Отец: {p.sire} × Мать: {p.dam}
                </p>
                <Link to={`/puppies/${p.id}`} className="feature-link">Подробнее →</Link>
              </div>
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: "2rem" }}>
            <Link to="/puppies" className="btn btn-primary">Все помёты</Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <div className="cta-content">
          <h2 className="cta-title">Готовы присоединиться?</h2>
          <p className="cta-subtitle">Станьте частью сообщества, которое формирует будущее породы сибирский хаски в России.</p>
          <div className="cta-buttons">
            <Link to="/contact" className="btn btn-white">🚀 Стать членом клуба</Link>
            <Link to="/contact" className="btn btn-outline">📞 Связаться с нами</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
