import { Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { getDict, pickValue } from "@/lib/dict";
import "./ClubSidebar.css";

export type Doc = { id: string; icon: string; title: string; sub?: string; to?: string };
export type Stat = { id: string; value: string; label: string };
export type Action = { id: string; label: string; to: string; kind?: "primary" | "info" | "neutral" };

type Props = {
  docs?: Doc[];
  stats?: Stat[];
  actions?: Action[];
  stickyTopPx?: number;
};

const defaultDocs: Doc[] = [
  { id: "d1", icon: "📐", title: "Стандарт породы FCI", sub: "PDF, 0.9 МБ" },
  { id: "d2", icon: "📋", title: "Устав НКП СХ", sub: "PDF, 2.1 МБ" },
  { id: "d3", icon: "📜", title: "Племенное положение", sub: "PDF, 1.8 МБ" },
  { id: "d4", icon: "🏆", title: "Выставочное положение", sub: "PDF, 1.5 МБ" },
  { id: "d5", icon: "📝", title: "Заявление на членство", sub: "DOC, 0.2 МБ" },
  { id: "d6", icon: "💰", title: "Реквизиты для оплаты", sub: "PDF, 0.1 МБ" },
];

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

export default function ClubSidebar({
  docs = defaultDocs,
  stats = defaultStats,
  actions = defaultActions,
  stickyTopPx = 120,
}: Props) {
  const sidebarRef = useRef<HTMLDivElement>(null);
  const [isSticky, setIsSticky] = useState(false);
  const [docsState, setDocsState] = useState<Doc[]>(docs);

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

  // Load document titles from dictionary API (STANDARD_FCI_270, DOCS_CHARTER, DOCS_REGULATIONS)
  useEffect(() => {
    let ignore = false;
    getDict()
      .then((dict) => {
        if (ignore) return;
        const standard = pickValue(dict, 'STANDARD_FCI_270', 'ru');
        const charter = pickValue(dict, 'DOCS_CHARTER', 'ru');
        const regulations = pickValue(dict, 'DOCS_REGULATIONS', 'ru');
        setDocsState((prev) =>
          prev.map((d) =>
            d.id === 'd1' && standard
              ? { ...d, title: standard }
              : d.id === 'd2' && charter
                ? { ...d, title: charter }
                : d.id === 'd5' && regulations
                  ? { ...d, title: regulations }
                  : d
          )
        );
      })
      .catch(() => {});
    return () => { ignore = true; };
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
              {docsState.map((d) => (
                <Link to={d.to ?? "#"} className="club-sidebar__document" key={d.id}>
                  <div className="club-sidebar__document-icon">{d.icon}</div>
                  <div>
                    <div className="club-sidebar__document-title">{d.title}</div>
                    {d.sub && <div className="club-sidebar__document-sub">{d.sub}</div>}
                  </div>
                </Link>
              ))}
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
