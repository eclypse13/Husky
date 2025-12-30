import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { getDict, pickValue } from "@/lib/dict";

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

export default function EventReports() {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let ignore = false;

    const load = async () => {
      setLoading(true);
      setErr(null);

      try {
        const dict = await getDict();
        if (ignore) return;

        const res = await fetch("/api/event-reports/");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const payload = await res.json();
        if (ignore) return;

        const fromApi = Array.isArray((payload as any)?.results)
          ? (payload as any).results
          : Array.isArray(payload)
          ? payload
          : [];

        const normalized: ReportItem[] = fromApi
          .map((r: any, idx: number): ReportItem | null => {
            const id = String(r?.id ?? idx);

            const titleKey =
              typeof r?.event_title_key === "string" ? r.event_title_key : "";

            const titleFromDict = titleKey ? pickValue(dict, titleKey, "ru") : null;

            // если titleKey уже “человеческий текст” (например "Test Event"), оставляем его
            const title = (titleFromDict || titleKey || `Отчёт #${id}`).toString();

            return {
              id,
              title,
              created_at: typeof r?.created_at === "string" ? r.created_at : null,
            };
          })
          .filter((x: ReportItem | null): x is ReportItem => Boolean(x));

        // сортировка: новые → старые
        normalized.sort((a, b) => safeTime(b.created_at) - safeTime(a.created_at));

        setReports(normalized);
      } catch (e: any) {
        setErr(e?.message || "Ошибка загрузки");
      } finally {
        setLoading(false);
      }
    };

    load();
    return () => {
      ignore = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return reports;
    return reports.filter((r) => r.title.toLowerCase().includes(q));
  }, [reports, query]);

  return (
    <div style={{}}>
      <div style={{margin: "0 auto" }}>
        <Breadcrumb
          title="Отчёты"
          items={[
            { label: "Главная", to: "/" },
            { label: "Мероприятия", to: "/events" },
            { label: "Отчёты" },
          ]}
        />
      </div>

      <div style={{ padding: 64, maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 12 }}>
          <h1 style={{ margin: 0 }}>Все отчёты</h1>
          <span style={{ opacity: 0.7 }}>({filtered.length})</span>
        </div>

        <div style={{ marginTop: 16 }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск по названию мероприятия…"
            style={{
              width: "100%",
              padding: "12px 14px",
              borderRadius: 12,
              border: "1px solid rgba(0,0,0,0.12)",
              outline: "none",
            }}
          />
        </div>

        {loading && <div style={{ marginTop: 16 }}>Загрузка…</div>}
        {err && <div style={{ marginTop: 16 }}>Ошибка: {err}</div>}

        {!loading && !err && (
          <div style={{ marginTop: 16, display: "grid", gap: 10 }}>
            {filtered.length === 0 && (
              <div style={{ opacity: 0.75 }}>Ничего не найдено.</div>
            )}

            {filtered.map((r) => (
              <Link
                key={r.id}
                to={`/event-report/${r.id}`}
                style={{
                  display: "block",
                  textDecoration: "none",
                  color: "inherit",
                  border: "1px solid rgba(0,0,0,0.08)",
                  borderRadius: 14,
                  padding: 14,
                }}
              >
                <div style={{ fontWeight: 700 }}>{r.title}</div>
                <div style={{ marginTop: 6, opacity: 0.7, fontSize: 14 }}>
                  {r.created_at ? dateTimeFormatter.format(new Date(r.created_at)) : "Дата неизвестна"}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
