import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { getDict, pickValue } from "@/lib/dict";
import { useEventReportsList } from "@/generated/event-reports/event-reports";
import "./EventReports.css";

type ReportItem = {
  id: string;
  title: string;
  created_at?: string | null;
};

const dateTimeFormatter = new Intl.DateTimeFormat("ru-RU", {
  year: "numeric",
  month: "long",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function safeTime(s?: string | null): number {
  if (!s) return 0;
  const t = new Date(s).getTime();
  return Number.isNaN(t) ? 0 : t;
}

const SKELETON_COUNT = 6;

export default function EventReports() {
  const [query, setQuery] = useState("");
  const [dict, setDict] = useState<any>(null);
  const pageRef = useRef<HTMLDivElement | null>(null);

  const { data: reportsData, isLoading: loading, error: fetchError } = useEventReportsList();
  const err = fetchError ? String(fetchError) : null;

  useEffect(() => {
    let ignore = false;
    getDict().then((d) => { if (!ignore) setDict(d); }).catch(() => {});
    return () => { ignore = true; };
  }, []);

  const reports = useMemo((): ReportItem[] => {
    const fromApi = reportsData?.data?.results ?? [];
    const normalized: ReportItem[] = fromApi
      .map((r, idx): ReportItem | null => {
        const id = String(r?.id ?? idx);
        const titleKey = typeof r?.event_title_key === "string" ? r.event_title_key : "";
        const titleFromDict = titleKey && dict ? pickValue(dict, titleKey, "ru") : null;
        const title = (titleFromDict || titleKey || `Отчёт #${id}`).toString();
        return {
          id,
          title,
          created_at: typeof r?.created_at === "string" ? r.created_at : null,
        };
      })
      .filter((x): x is ReportItem => Boolean(x));

    normalized.sort((a, b) => safeTime(b.created_at) - safeTime(a.created_at));
    return normalized;
  }, [reportsData, dict]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return reports;
    return reports.filter((r) => r.title.toLowerCase().includes(q));
  }, [reports, query]);

  useEffect(() => {
    const root = pageRef.current;
    if (!root || loading) return;

    const prefersReduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const els = root.querySelectorAll<HTMLElement>(
      ".reports-search-section, .reports-card, .reports-empty"
    );

    if (prefersReduced) {
      els.forEach((el) => el.setAttribute("data-visible", "1"));
      return;
    }

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
  }, [filtered, loading]);

  return (
    <div ref={pageRef} className="reports-page">
      <Breadcrumb
        title="Отчёты"
        items={[
          { label: "Главная", to: "/" },
          { label: "Мероприятия", to: "/events" },
          { label: "Отчёты" },
        ]}
      />

      <main className="reports-main">
        <div className="reports-container">
          <div className="reports-head">
            <h1 className="reports-title">Все отчёты</h1>
            <span className="reports-count">({filtered.length})</span>
          </div>

          <div className="reports-search-section">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Поиск по названию мероприятия…"
              className="reports-search-input"
            />
          </div>

          {err && <div className="reports-error">Ошибка: {err}</div>}

          {loading && (
            <div className="reports-grid">
              {Array.from({ length: SKELETON_COUNT }, (_, i) => (
                <div key={i} className="reports-skeleton">
                  <div className="reports-skeleton__line reports-skeleton__line--title" />
                  <div className="reports-skeleton__line reports-skeleton__line--date" />
                </div>
              ))}
            </div>
          )}

          {!loading && !err && (
            <div className="reports-grid">
              {filtered.length === 0 && (
                <div className="reports-empty">
                  <div className="reports-empty__icon">
                    {query.trim() ? "🔍" : "📋"}
                  </div>
                  <h3 className="reports-empty__title">
                    {query.trim() ? "Ничего не найдено" : "Отчётов пока нет"}
                  </h3>
                  <p className="reports-empty__sub">
                    {query.trim()
                      ? "Попробуйте изменить поисковый запрос"
                      : "Здесь будут отображаться отчёты о мероприятиях"}
                  </p>
                </div>
              )}

              {filtered.map((r) => (
                <Link key={r.id} to={`/events/reports/${r.id}`} className="reports-card">
                  <div className="reports-card__title">{r.title}</div>
                  <div className="reports-card__date">
                    {r.created_at
                      ? dateTimeFormatter.format(new Date(r.created_at))
                      : "Дата неизвестна"}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
