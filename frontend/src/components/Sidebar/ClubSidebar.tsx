import { Link } from "react-router-dom";
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
  stickyTopPx,
}: Props) {
  return (
    <aside
      className="sidebar"
      style={stickyTopPx != null ? { position: "sticky", top: `${stickyTopPx}px` } : undefined}
    >
      <div className="sidebar-card">
        <h3 className="sidebar-title">📄 Документы клуба</h3>
        <div className="document-list">
          {docs.map((d) => (
            <Link to={d.to ?? "#"} className="document-item" key={d.id}>
              <div className="document-icon">{d.icon}</div>
              <div>
                <div className="document-title">{d.title}</div>
                {d.sub && <div className="document-sub">{d.sub}</div>}
              </div>
            </Link>
          ))}
        </div>
      </div>

      <div className="sidebar-card">
        <h3 className="sidebar-title">📊 Статистика клуба</h3>
        <div className="stats-grid">
          {stats.map((s) => (
            <div className="stat-box" key={s.id}>
              <div className="stat-number">{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="sidebar-card">
        <h3 className="sidebar-title">🚀 Быстрые действия</h3>
        <div className="quick-actions">
          {actions.map((a) => (
            <Link
              key={a.id}
              to={a.to}
              className={
                a.kind === "info" ? "qa-info" : a.kind === "neutral" ? "qa-neutral" : "qa-primary"
              }
            >
              {a.label}
            </Link>
          ))}
        </div>
      </div>
    </aside>
  );
}
