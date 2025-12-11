import { Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { getDict, pickValue } from "@/lib/dict";
import "./ClubSidebar.css";

const CACHE_KEY = "club-documents-v1";
const CACHE_EXPIRY_MS = 30 * 60 * 1000; // 30 минут

export type Doc = { id: string; icon: string; title: string; sub?: string; to?: string };
export type Stat = { id: string; value: string; label: string };
export type Action = { id: string; label: string; to: string; kind?: "primary" | "info" | "neutral" };

type Props = {
  stats?: Stat[];
  actions?: Action[];
  stickyTopPx?: number;
};

const defaultStats: Stat[] = [
  { id: "s1", value: "1,250+", label: "Членов" },
  { id: "s2", value: "350+", label: "Питомников" },
  { id: "s3", value: "15,000+", label: "Собак в архиве" },
  { id: "s4", value: "85", label: "Регионов" },
];

const defaultActions: Action[] = [
  { id: "a1", label: "Подать заявление", to: "/join", kind: "primary" },
  { id: "a2", label: "Задать вопрос", to: "/contact", kind: "info" },
  { id: "a3", label: "Календарь мероприятий", to: "/events", kind: "neutral" },
];

const getIconByType = (type: string): string => {
  switch (type) {
    case "standard": return "📐";
    case "charter": return "📋";
    case "regulation": return "📜";
    case "exhibition": return "🏆";
    case "form": return "📝";
    case "payment": return "💰";
    default: return "📄";
  }
};

const getFileMeta = (url: string | null, fallbackDesc?: string): string => {
  if (!url) return fallbackDesc || "–";
  try {
    const u = new URL(url, window.location.origin);
    const path = u.pathname;
    const parts = path.split('/');
    const filename = parts[parts.length - 1];
    const extMatch = filename.match(/\.([a-z0-9]+)$/i);
    const ext = extMatch ? extMatch[1].toUpperCase() : "–";
    return `${ext}, файл`;
  } catch {
    return fallbackDesc || "Файл";
  }
};

export default function ClubSidebar({
  stats = defaultStats,
  actions = defaultActions,
  stickyTopPx = 120,
}: Props) {
  const sidebarRef = useRef<HTMLDivElement>(null);
  const [isSticky, setIsSticky] = useState(false);
  const [docsState, setDocsState] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Скролл-логика — без изменений
  useEffect(() => {
    const handleScroll = () => {
      if (sidebarRef.current) {
        const sidebarRect = sidebarRef.current.getBoundingClientRect();
        const shouldSticky = sidebarRect.top <= stickyTopPx;
        if (shouldSticky !== isSticky) {
          setIsSticky(shouldSticky);
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isSticky, stickyTopPx]);

  // 🔥 ЕДИНЫЙ useEffect: кэш при старте + загрузка API + обновление кэша
  useEffect(() => {
    let ignore = false;

    // 1️⃣ Пытаемся восстановить из кэша
    const restoreFromCache = () => {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        try {
          const { data, timestamp } = JSON.parse(cached);
          if (
            Array.isArray(data) &&
            Date.now() - timestamp <= CACHE_EXPIRY_MS
          ) {
            if (!ignore) {
              setDocsState(data);
              setLoading(false);
            }
            return true; // кэш использован
          } else {
            localStorage.removeItem(CACHE_KEY);
          }
        } catch (e) {
          console.warn("Invalid cache format", e);
          localStorage.removeItem(CACHE_KEY);
        }
      }
      return false;
    };

    const hasCache = restoreFromCache();
    if (ignore) return;

    // 2️⃣ Если кэша нет или он просрочен — грузим с API
    if (!hasCache) {
      setLoading(true);
      setError(null);
    }

    const loadFromApi = async () => {
      try {
        const res = await fetch("/api/club/documents/");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const results: any[] = Array.isArray(data.results) ? data.results : [];
        const dict = await getDict();

        if (ignore) return;

        const mappedDocs: Doc[] = results.map((entry) => ({
          id: String(entry.id),
          icon: getIconByType(entry.document_type),
          title: entry.title_key
            ? pickValue(dict, entry.title_key, "ru") || entry.title_key
            : "Без названия",
          sub: getFileMeta(entry.file, entry.description_key),
          to: entry.file ?? "#",
        }));

        if (!ignore) {
          setDocsState(mappedDocs);
          // ✅ Сохраняем в кэш
          localStorage.setItem(
            CACHE_KEY,
            JSON.stringify({
              data: mappedDocs,
              timestamp: Date.now(),
            })
          );
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Ошибка загрузки";
        console.error("API load failed:", err);
        if (!ignore) {
          setError(msg);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    // Запускаем API-запрос ВСЕГДА (даже при кэше — для актуализации!)
    loadFromApi();

    return () => {
      ignore = true;
    };
  }, []);

  return (
    <aside className="club-sidebar" ref={sidebarRef}>
      <div className="club-sidebar__container">
        <div className="club-sidebar__empty"></div>
        <div
          className={`club-sidebar__sticky ${isSticky ? 'club-sidebar__sticky--fixed' : ''}`}
        >
          <div className="club-sidebar__card sidebar-card">
            <h3 className="club-sidebar__title">📄 Документы клуба</h3>
            <div className="club-sidebar__documents">
              {loading ? (
                <div className="club-sidebar__document-placeholder">Загрузка…</div>
              ) : error ? (
                <div className="club-sidebar__document-error">❌ {error}</div>
              ) : docsState.length === 0 ? (
                <div className="club-sidebar__document-empty">Нет документов</div>
              ) : (
                docsState.map((d) => (
                  <Link
                    to={d.to ?? "#"}
                    target={d.to && d.to !== "#" ? "_blank" : undefined}
                    rel={d.to && d.to !== "#" ? "noopener noreferrer" : undefined}
                    className="club-sidebar__document"
                    key={d.id}
                  >
                    <div className="club-sidebar__document-icon">{d.icon}</div>
                    <div>
                      <div className="club-sidebar__document-title">{d.title}</div>
                      {d.sub && <div className="club-sidebar__document-sub">{d.sub}</div>}
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>

          <div className="club-sidebar__card sidebar-card">
            <h3 className="club-sidebar__title">📊 Статистика клуба</h3>
            <div className="club-sidebar__stats">
              {stats.map((s) => (
                <div className="club-sidebar__stat" key={s.id}>
                  <div className="club-sidebar__stat-number">{s.value}</div>
                  <div className="club-sidebar__stat-label">{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="club-sidebar__card sidebar-card">
            <h3 className="club-sidebar__title">🚀 Быстрые действия</h3>
            <div className="club-sidebar__quick">
              {actions.map((a) => (
                <Link
                  key={a.id}
                  to={a.to}
                  className={
                    "club-sidebar__qa " +
                    (a.kind === "info"
                      ? "club-sidebar__qa--info"
                      : a.kind === "neutral"
                        ? "club-sidebar__qa--neutral"
                        : "club-sidebar__qa--primary")
                  }
                >
                  {a.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}