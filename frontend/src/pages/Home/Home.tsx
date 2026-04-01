import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { getDict, pickValue } from "@/lib/dict";
import "./Home.css";

const news = [
  { id: 1, tag: "Выставки", date: "18 июля 2025", title: "«Сибирская красота 2025» — рекордное участие", excerpt: "В Москве прошла крупнейшая специализированная выставка с участием более 200 собак из 15 стран.", featured: true, link: "Читать полный отчет", icon: "🏆", to: "/news/1" },
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

type HomeNewsItem = {
  id: string; tag: string; date: string; title: string;
  excerpt: string; link: string; icon: string; to: string;
};

type HeroDog = {
  id: number;
  display_name: string;
  photo_url: string | null;
  prefix_titles: string | null;
  suffix_titles: string | null;
  year_of_birth: number | null;
  color: string | null;
};

const homeNewsDateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric", month: "long", year: "numeric",
});

function formatNewsDate(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return homeNewsDateFormatter.format(d);
}

function capitalizeTag(tag: string): string {
  if (!tag) return tag;
  const trimmed = tag.trim();
  if (!trimmed) return trimmed;
  return `${trimmed[0].toLocaleUpperCase("ru-RU")}${trimmed.slice(1)}`;
}

/* UTILS */
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

function StatCard({ label, value, plus }: { label: string; value: number; plus?: boolean }) {
  const n = useCounter(value);
  return (
    <div className="home-stat-item">
      <div className="home-stat-number">{n}{plus ? "+" : ""}</div>
      <div className="home-stat-label">{label}</div>
    </div>
  );
}

function NewsCard({ item, featured }: { item: (typeof news)[number] | HomeNewsItem; featured?: boolean }) {
  return (
    <article className={`home-news-card ${featured ? "home-featured" : ""}`}>
      <div className="home-news-image">{item.icon}</div>
      <div className="home-news-inner">
        <div className="home-news-meta">
          <span className="home-news-tag">{capitalizeTag(item.tag)}</span>
          <span className="home-news-date">{item.date}</span>
        </div>
        <h3 className="home-news-title">{item.title}</h3>
        <p className="home-news-excerpt">{item.excerpt}</p>
        <Link to={item.to} className="home-feature-link">{item.link} →</Link>
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
    const nodes = document.querySelectorAll<HTMLElement>(".home-page .home-activity-item");
    nodes.forEach((el, i) => {
      requestAnimationFrame(() => {
        setTimeout(() => el.classList.add("home-activity-item--visible"), i * 120);
      });
    });
  }, [items]);

  return (
    <div className="home-activity-feed">
      {items.map((a, i) => (
        <div key={i} className="home-activity-item">
          <div className="home-activity-avatar">{a.icon}</div>
          <div className="home-activity-text">
            <strong>{a.text}</strong>
            <div className="home-activity-time">{a.time}</div>
          </div>
        </div>
      ))}
      <div className="home-typing-indicator" style={{ marginTop: ".5rem" }}>
        <div className="home-typing-dot" /><div className="home-typing-dot" /><div className="home-typing-dot" />
        <span>Обновления поступают…</span>
      </div>
    </div>
  );
}

const PLACEHOLDER_URLS = ["https://zooportal.pro/images/logo1.png"];
const DEFAULT_DOG_IMG = "/no-image-dog.png";
const dogPhoto = (url: string | null | undefined): string =>
  url && !PLACEHOLDER_URLS.includes(url) ? url : DEFAULT_DOG_IMG;

/* PAGE */
export default function Home() {
  const [homeNews, setHomeNews] = useState<HomeNewsItem[]>([]);
  const [breederCount, setBreederCount] = useState(350);
  const [heroDog, setHeroDog] = useState<HeroDog | null | "loading">("loading");

  const visibleNews = useMemo(() => {
    const source: Array<(typeof news)[number] | HomeNewsItem> = homeNews.length ? homeNews : news;
    return source.slice(0, 5);
  }, [homeNews]);
  const featured = visibleNews[0] ?? news[0];
  const others = featured ? visibleNews.slice(1) : visibleNews;

  // ── Загружаем кол-во питомников (заводчиков) из БД ──────────────────────────────
  useEffect(() => {
    fetch("/api/dogs/stats/")
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.breeders != null) setBreederCount(data.breeders);
      })
      .catch(() => {});
  }, []);

  // ── Загружаем собаку-звезду для hero-карточки ───────────────────────────────
  useEffect(() => {
    fetch("/api/dogs/search/?q=Chudni Medvezhonok Gold Sensation")
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        const results = Array.isArray(data) ? data : data?.results;
        if (results?.length) setHeroDog(results[0] as HeroDog);
        else setHeroDog(null);
      })
      .catch(() => setHeroDog(null));
  }, []);

  // ── Новости ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    let ignore = false;

    const loadNews = async () => {
      try {
        const dict = await getDict();
        if (ignore) return;

        let payload: any = null;
        try {
          const res = await fetch("/api/news/");
          if (res.ok) payload = await res.json();
        } catch { payload = null; }
        if (ignore) return;

        const results: any[] = Array.isArray(payload?.results)
          ? payload.results
          : Array.isArray(payload) ? payload : [];

        const mapped: HomeNewsItem[] = results.map((item: any) => ({
          id:      String(item.id ?? Math.random()),
          tag:     pickValue(dict, item.category) ?? item.category ?? "Новости",
          date:    formatNewsDate(item.published_at ?? item.created_at) || item.date || "",
          title:   item.title ?? "",
          excerpt: item.excerpt ?? item.description ?? "",
          link:    "Подробнее",
          icon:    item.icon ?? "📰",
          to:      `/news/${item.id ?? item.slug ?? "#"}`,
        }));

        if (!ignore && mapped.length) setHomeNews(mapped);
      } catch {
        if (!ignore) setHomeNews([]);
      }
    };

    loadNews();
    return () => { ignore = true; };
  }, []);

  const stats = [
    { label: "Членов клуба", value: 1250,        plus: true },
    { label: "Питомников",   value: breederCount, plus: true },
    { label: "Лет работы",   value: 15,           plus: true },
  ];

  return (
    <div className="home-page">
      {/* HERO */}
      <section className="home-hero">
        <div className="home-hero-content">
          <div className="home-hero-text">
            <h2>Сибирские хаски<br />мирового класса</h2>
            <p className="home-hero-subtitle">
              Ведущий национальный клуб России, объединяющий заводчиков, владельцев и любителей породы сибирский хаски.
              Сохраняем традиции, развиваем будущее.
            </p>
            <div className="home-hero-buttons">
              <Link to="/archive" className="home-btn home-btn-primary">🔍 Найти собаку</Link>
              <Link to="/breed" className="home-btn home-btn-secondary">📚 О породе</Link>
            </div>

            <div className="home-hero-stats">
              {stats.map(s => <StatCard key={s.label} {...s} />)}
            </div>
          </div>

          {/* ── Hero-карточка с реальной собакой ── */}
          <div className="home-hero-visual">
            {heroDog === "loading" || heroDog === null ? (
              <p className="home-hero-loading">Загрузка...</p>
            ) : (
              <div className="home-hero-card">
                <div className="home-hero-image">
                  {heroDog.photo_url ? (
                    <img
                      src={dogPhoto(heroDog.photo_url)}
                      alt={heroDog.display_name}
                      style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%" }}
                    />
                  ) : "🐕"}
                </div>
                <h3>{heroDog.display_name}</h3>
                <p>
                  {[heroDog.prefix_titles, heroDog.suffix_titles].filter(Boolean).join(" · ") || "Сибирский хаски"}
                </p>
                <Link to={`/archive/dog/${heroDog.id}`} className="home-btn home-btn-primary">
                  Посмотреть профиль
                </Link>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* MAP */}
      <section className="home-interactive-map-section">
        <div className="home-map-content">
          <div className="home-head-section-header">
            <h2 className="home-head-section-title">Наша география</h2>
            <p className="home-head-section-subtitle">Питомники и члены клуба по всей России</p>
          </div>

          <div className="home-map-container">
            <div className="home-russia-map">
              <svg viewBox="0 0 1000 600" className="home-map-svg">
                <path d="M100,200 L200,180 L300,160 L400,140 L500,130 L600,125 L700,120 L800,125 L850,140 L900,160 L920,200 L900,250 L850,300 L800,350 L700,380 L600,400 L500,420 L400,430 L300,425 L200,410 L150,380 L100,320 Z"
                  fill="var(--ice-blue)" stroke="var(--bright-blue)" strokeWidth="2" />
                {[
                  { cx: 300, cy: 250, r: 12, t: "Москва — 45 питомников" },
                  { cx: 320, cy: 280, r: 10, t: "Санкт-Петербург — 28 питомников" },
                  { cx: 450, cy: 300, r: 8,  t: "Екатеринбург — 15 питомников" },
                  { cx: 600, cy: 280, r: 7,  t: "Новосибирск — 12 питомников" },
                  { cx: 750, cy: 250, r: 6,  t: "Владивосток — 8 питомников" },
                  { cx: 400, cy: 200, r: 5,  t: "Архангельск — 6 питомников" },
                ].map((p, i) => (
                  <circle key={i} cx={p.cx} cy={p.cy} r={p.r} className="home-kennel-point"
                    onClick={() => alert(`Информация: ${p.t}`)} />
                ))}
              </svg>
            </div>

            <div className="home-map-stats">
              {[
                { icon: "🏙️", value: 45, label: "Москва и МО" },
                { icon: "🏛️", value: 28, label: "Санкт-Петербург" },
                { icon: "🏔️", value: 89, label: "Другие регионы" },
              ].map(x => (
                <div key={x.label} className="home-region-stat">
                  <div className="home-stat-icon">{x.icon}</div>
                  <div>
                    <div className="home-stat-number">{x.value}</div>
                    <div className="home-stat-label">{x.label}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ACTIVITY */}
      <section className="home-activity-section">
        <div className="home-activity-content">
          <div className="home-head-section-header">
            <h2 className="home-head-section-title">Живая лента активности</h2>
            <p className="home-head-section-subtitle">Что происходит в мире хаски прямо сейчас</p>
          </div>
          <ActivityFeed />
        </div>
      </section>

      {/* FEATURES */}
      <section className="home-features">
        <div className="home-features-content">
          <div className="home-head-section-header">
            <h2 className="home-head-section-title">Всё для породы хаски</h2>
            <p className="home-head-section-subtitle">Комплексная экосистема для заводчиков, владельцев и любителей сибирских хаски</p>
          </div>

          <div className="home-features-grid">
            {[
              { icon: "📊", title: "Породный архив", desc: "15,000+ собак в базе данных с интерактивными родословными, результатами тестов здоровья и полной историей титулов.", link: "Перейти к архиву", to: "/archive" },
              { icon: "🧬", title: "Здоровье породы", desc: "Генетические тесты, офтальмологические обследования, реестры здоровья и инструменты для планирования вязок.", link: "Тестирование", to: "/health" },
              { icon: "🏆", title: "Выставки и спорт", desc: "Календарь мероприятий, результаты выставок, ездовой спорт, семинары и обучающие программы.", link: "Мероприятия", to: "/events" },
              { icon: "🤝", title: "Сообщество", desc: "Объединяем заводчиков и владельцев, обмениваемся опытом, поддерживаем новичков и развиваем породу вместе.", link: "Присоединиться", to: "/about" },
              { icon: "🎯", title: "Умные инструменты", desc: "AI-анализ совместимости, предиктивная аналитика наследственных заболеваний, компьютерное зрение для оценки экстерьера.", link: "Инновации", to: "/tools" },
              { icon: "🌐", title: "Интеграция", desc: "Партнерство с breedarchive.com, обмен данными с ведущими клубами мира, участие в глобальных проектах.", link: "Узнать больше", to: "/about" },
            ].map(f => (
              <div key={f.title} className="home-feature-card">
                <div className="home-feature-icon">{f.icon}</div>
                <h3 className="home-feature-title">{f.title}</h3>
                <p className="home-feature-description">{f.desc}</p>
                <Link to={f.to} className="home-feature-link">{f.link} →</Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* NEWS */}
      <section className="home-news-section">
        <div className="home-news-content">
          <div className="home-head-section-header">
            <h2 className="home-head-section-title">Последние новости</h2>
            <p className="home-head-section-subtitle">Будьте в курсе всех событий в мире сибирских хаски</p>
          </div>

          <div className="home-news-grid">
            {featured && <NewsCard item={featured} featured />}
            {others.map(n => <NewsCard key={n.id} item={n} />)}
          </div>
        </div>
      </section>

      {/* PUPPIES */}
      <section className="home-features">
        <div className="home-features-content">
          <div className="home-head-section-header">
            <h2 className="home-head-section-title">🐾 Доступные щенки</h2>
            <p className="home-head-section-subtitle">Помёты от проверенных питомников — только от членов НКП.</p>
          </div>

          <div className="home-features-grid">
            {puppies.map(p => (
              <div key={p.id} className="home-feature-card">
                <div className="home-feature-icon">{p.icon}</div>
                <h3 className="home-feature-title">{p.name}</h3>
                <p className="home-feature-description">
                  {p.sex}, род. {p.dob}<br />
                  Отец: {p.sire} × Мать: {p.dam}
                </p>
                <Link to={`/puppies/${p.id}`} className="home-feature-link">Подробнее →</Link>
              </div>
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: "2rem" }}>
            <Link to="/puppies" className="home-btn home-btn-primary">Все помёты</Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="home-cta-section">
        <div className="home-cta-content">
          <h2 className="home-cta-title">Готовы присоединиться?</h2>
          <p className="home-cta-subtitle">Станьте частью сообщества, которое формирует будущее породы сибирский хаски в России.</p>
          <div className="home-cta-buttons">
            <Link to="/contact" className="home-btn home-btn-white">🚀 Стать членом клуба</Link>
            <Link to="/contact" className="home-btn home-btn-outline">📞 Связаться с нами</Link>
          </div>
        </div>
      </section>
    </div>
  );
}

