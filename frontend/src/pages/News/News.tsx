import { useEffect, useRef, useState } from "react";
import { getDict, pickValue } from "@/lib/dict";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./News.css";

const newsDateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

function formatNewsDate(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return newsDateFormatter.format(date);
}

function capitalizeTag(tag: string): string {
  if (!tag) return tag;
  const [first, ...rest] = tag.trim();
  return `${first?.toLocaleUpperCase?.("ru-RU") ?? first}${rest.join("")}`;
}

export default function News() {
  const pageRef = useRef<HTMLDivElement | null>(null);
  type NewsItem = {
    id: string;
    title: string;
    lead?: string | null;
    body?: string | null;
    tags: string[];
    slug?: string;
    publishedAt?: string | null;
  };
  const [items, setItems] = useState<NewsItem[]>([]);
  const [filteredItems, setFilteredItems] = useState<NewsItem[]>([]);
  const [categoryOptions, setCategoryOptions] = useState<string[]>([]);
  const [yearOptions, setYearOptions] = useState<string[]>([]);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [yearFilter, setYearFilter] = useState("all");

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

  // Load news items from API and hydrate titles via dictionary keys
  useEffect(() => {
    let ignore = false;

    const loadNews = async () => {
      try {
        const dict = await getDict();
        if (ignore) return;

        let payload: unknown = null;
        try {
          const res = await fetch("/api/news/");
          if (res.ok) {
            payload = await res.json();
          }
        } catch {
          payload = null;
        }
        if (ignore) return;

        const results: any[] = Array.isArray((payload as any)?.results)
          ? (payload as any).results
          : Array.isArray(payload)
          ? (payload as any)
          : [];

        const mapped: NewsItem[] = results
          .map((entry, index): NewsItem | null => {
            if (!entry) return null;
            const titleKey = typeof entry.title_key === "string" ? entry.title_key : "";
            const leadKey = typeof entry.lead_key === "string" ? entry.lead_key : "";
            const bodyKey = typeof entry.body_key === "string" ? entry.body_key : "";
            const title = titleKey ? pickValue(dict, titleKey, "ru") : null;
            if (!title) return null;
            const lead = leadKey ? pickValue(dict, leadKey, "ru") : null;
            const body = bodyKey ? pickValue(dict, bodyKey, "ru") : null;
            const tags = Array.isArray(entry.tags) ? entry.tags.filter((t: unknown) => typeof t === "string").map((t: string) => t.trim()).filter(Boolean) : [];
            const publishedAt = typeof entry.published_at === "string" ? entry.published_at : null;
            return {
              id: String(entry.id ?? entry.slug ?? index),
              title,
              lead,
              body,
              tags,
              slug: typeof entry.slug === "string" ? entry.slug : undefined,
              publishedAt,
            };
          })
          .filter((n): n is NewsItem => Boolean(n));

        mapped.sort((a, b) => {
          const aTime = a.publishedAt ? new Date(a.publishedAt).getTime() : 0;
          const bTime = b.publishedAt ? new Date(b.publishedAt).getTime() : 0;
          return bTime - aTime;
        });

        const categorySet = new Set<string>();
        const yearSet = new Set<string>();
        const isYear = (tag: string) => /^\d{4}$/.test(tag);
        mapped.forEach((item) => {
          item.tags.forEach((tag) => {
            if (isYear(tag)) yearSet.add(tag);
            else categorySet.add(tag);
          });
        });

        if (!ignore) {
          setItems(mapped);
          setFilteredItems(mapped);
          setCategoryOptions(Array.from(categorySet).sort((a, b) => a.localeCompare(b, "ru", { sensitivity: "base" })));
          setYearOptions(Array.from(yearSet).sort((a, b) => b.localeCompare(a, "ru")));
        }
      } catch {
        if (!ignore) {
          setItems([]);
          setFilteredItems([]);
          setCategoryOptions([]);
          setYearOptions([]);
        }
      }
    };

    loadNews();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    setFilteredItems(
      items.filter((item) => {
        if (categoryFilter !== "all" && !item.tags.includes(categoryFilter)) return false;
        if (yearFilter !== "all" && !item.tags.includes(yearFilter)) return false;
        return true;
      })
    );
  }, [items, categoryFilter, yearFilter]);

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
              <select
                className="news-select"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="all">Все категории</option>
                {categoryOptions.map((tag) => (
                  <option key={tag} value={tag}>
                    {capitalizeTag(tag)}
                  </option>
                ))}
              </select>
              <select
                className="news-select"
                value={yearFilter}
                onChange={(e) => setYearFilter(e.target.value)}
              >
                <option value="all">Год</option>
                {yearOptions.map((tag) => (
                  <option key={tag} value={tag}>
                    {tag}
                  </option>
                ))}
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
            {/* Dynamic from API */}
            {filteredItems.length > 0 && filteredItems.map((n) => (
              <article className="news-card" key={n.id}>
                <div className="news-avatar">📰</div>
                <div className="news-info">
                  <h3 className="news-card-title">{n.title}</h3>
                  <div className="news-meta">
                    {n.tags.map((tag) => (
                      <span key={`${n.id}-${tag}`} className="news-meta-item">
                        {capitalizeTag(tag)}
                      </span>
                    ))}
                    {formatNewsDate(n.publishedAt) && (
                      <span className="news-meta-item">{formatNewsDate(n.publishedAt)}</span>
                    )}
                  </div>
                  <p className="news-desc">{n.lead ?? n.body}</p>
                </div>
                <div className="news-actions">
                  <a className="news-action news-action--primary" href={n.slug ? `/news/${n.slug}` : "#"}>
                    Читать
                  </a>
                </div>
              </article>
            ))}
            {/* Fallback static */}
            {items.length === 0 && [
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
