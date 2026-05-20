// src/pages/Stats/Stats.tsx
import { useEffect, useRef, useState } from "react";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./Stats.css";

const API_URL = "/api/dogs/stats/population/";

// ── Типы ──────────────────────────────────────────────────────────────────────
interface Overview {
  total: number; males: number; females: number;
  with_coi: number; with_photo: number; with_rating: number;
}
interface YearItem    { year: number; count: number; }
interface CountryItem { country: string; count: number; }
interface CoiBucket   { label: string; count: number; }
interface CovItem     { count: number; pct: number; }

interface Stats {
  overview:   Overview;
  by_year:    YearItem[];
  by_country: CountryItem[];
  coi_stats:  { avg: number; min: number; max: number; total: number; buckets: CoiBucket[] };
  coverage:   Record<string, CovItem>;
}

const fmt = (n: number) => n.toLocaleString("ru-RU");
const pct  = (a: number, b: number) => b ? Math.round(a / b * 100) : 0;

function Skeleton({ h = 120 }: { h?: number }) {
  return <div className="st-skel" style={{ height: h }} />;
}

function Bar({ value, max, color = "var(--bright-blue)" }: {
  value: number; max: number; color?: string;
}) {
  const w = max ? Math.round(value / max * 100) : 0;
  return (
    <div className="st-bar-wrap">
      <div className="st-bar-fill" style={{ width: `${w}%`, background: color }} />
    </div>
  );
}

function KpiCard({ icon, label, value, sub }: {
  icon: string; label: string; value: string | number; sub?: string;
}) {
  return (
    <div className="st-kpi">
      <span className="st-kpi-icon">{icon}</span>
      <span className="st-kpi-value">{typeof value === "number" ? fmt(value) : value}</span>
      <span className="st-kpi-label">{label}</span>
      {sub && <span className="st-kpi-sub">{sub}</span>}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="st-section">
      <h2 className="st-section-title">{title}</h2>
      {children}
    </section>
  );
}

export default function Stats() {
  const pageRef = useRef<HTMLDivElement>(null);
  const [data,    setData]    = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);

  useEffect(() => {
    fetch(API_URL)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!data) return;
    const root = pageRef.current;
    if (!root) return;
    const io = new IntersectionObserver(
      entries => entries.forEach(e =>
        e.isIntersecting && e.target.setAttribute("data-visible", "1")
      ),
      { threshold: 0.08 }
    );
    root.querySelectorAll<HTMLElement>("[data-anim]").forEach(el => {
      el.setAttribute("data-visible", "0");
      io.observe(el);
    });
    return () => io.disconnect();
  }, [data]);

  const ov         = data?.overview;
  const maxYear    = data ? Math.max(...data.by_year.map(y => y.count))    : 0;
  const maxCountry = data ? Math.max(...data.by_country.map(c => c.count)) : 0;
  const maxCoi     = data ? Math.max(...data.coi_stats.buckets.map(b => b.count)) : 0;

  return (
    <div ref={pageRef} className="st-page">
      <Breadcrumb
        title="Аналитика породы"
        items={[{ label: "Главная", to: "/" }, { label: "Аналитика" }]}
      />

      <main className="st-main">
        <div className="st-container">

          <div className="st-hero" data-anim>
            <h1 className="st-hero-title">
              Популяционная аналитика<br />
              <span className="st-hero-accent">Сибирский Хаски</span>
            </h1>
          </div>

          {error && (
            <div className="st-error">
              Не удалось загрузить статистику. Попробуйте позже.
            </div>
          )}

          {/* KPI */}
          <div className="st-kpi-grid" data-anim>
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} h={110} />)
            ) : ov ? (
              <>
                <KpiCard icon="🐕" label="Собак в базе"   value={ov.total} />
                <KpiCard icon="♂"  label="Кобелей"        value={ov.males}
                  sub={`${pct(ov.males, ov.total)}%`} />
                <KpiCard icon="♀"  label="Сук"            value={ov.females}
                  sub={`${pct(ov.females, ov.total)}%`} />
                <KpiCard icon="🧬" label="С данными COI"  value={ov.with_coi}
                  sub={`${pct(ov.with_coi, ov.total)}%`} />
                <KpiCard icon="📸" label="С фото"         value={ov.with_photo}
                  sub={`${pct(ov.with_photo, ov.total)}%`} />
                <KpiCard icon="🏆" label="В рейтинге"     value={ov.with_rating} />
              </>
            ) : null}
          </div>

          {/* Три секции */}
          <div className="st-grid" data-anim>

            {/* Регистрации по годам */}
            <Section title="Регистрации по году рождения">
              {loading ? <Skeleton h={200} /> : data && (
                <div className="st-year-chart">
                  {data.by_year.slice(-25).map(y => (
                    <div key={y.year} className="st-year-col">
                      <div
                        className="st-year-bar"
                        style={{ height: `${maxYear ? Math.round(y.count / maxYear * 140) : 0}px` }}
                        title={`${y.year}: ${fmt(y.count)}`}
                      />
                      {y.year % 5 === 0 && (
                        <span className="st-year-label">{y.year}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Section>

            {/* Страны */}
            <Section title="Страны происхождения">
              {loading ? <Skeleton h={200} /> : data && (
                <div className="st-list">
                  {data.by_country.map(c => (
                    <div key={c.country} className="st-list-row">
                      <span className="st-list-label">{c.country}</span>
                      <Bar value={c.count} max={maxCountry} />
                      <span className="st-list-value">{fmt(c.count)}</span>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            {/* COI */}
            <Section title="Распределение COI">
              {loading ? <Skeleton h={200} /> : data && (
                <div>
                  <div className="st-coi-summary">
                    <div className="st-coi-stat">
                      <span className="st-coi-num">{data.coi_stats.avg}%</span>
                      <span className="st-coi-lbl">Средний COI</span>
                    </div>
                    <div className="st-coi-stat">
                      <span className="st-coi-num">{fmt(data.coi_stats.total)}</span>
                      <span className="st-coi-lbl">Рассчитано</span>
                    </div>
                  </div>
                  <div className="st-list">
                    {data.coi_stats.buckets.map(b => (
                      <div key={b.label} className="st-list-row">
                        <span className="st-list-label">{b.label}</span>
                        <Bar value={b.count} max={maxCoi} color="var(--accent-cyan)" />
                        <span className="st-list-value">{fmt(b.count)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Section>

          </div>

        </div>
      </main>
    </div>
  );
}
