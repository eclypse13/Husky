import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./Judge.css";

type JudgePayload = {
  id: number | string;
  name: string;
  rank?: string | null;
  email?: string | null;
  photo?: string | null;
  materials?: unknown;
  judge_id?: number | null;
};

type JudgeDetailsPayload = {
  id: number;
  info?: unknown;
  additional_info_title?: unknown;
  additional_info_text?: unknown;
  work_directions?: unknown;
  initiative_title?: string | null;
  initiative_state?: string | null;
  initiative_text?: string | null;
  initiative_stack?: unknown;
  sidebar_text?: string | null;
  sidebar_achievements?: unknown;
  kennel_url?: string | null;
  kennel?: string | null;
};

type MaterialItem = {
  id: string;
  title: string;
  url?: string | null;
};

type WorkDirection = {
  title: string;
  desc: string;
  icon?: string | null;
};

const defaultProjects = [
  {
    status: "active",
    title: "Система личных кабинетов",
    desc: "Многоуровневая система авторизации и персональных кабинетов для разных ролей пользователей.",
    tech: ["React", "Node.js", "PostgreSQL"],
  },
  {
    status: "active",
    title: "Породный рейтинг",
    desc: "Автоматизированный подсчёт и визуализация рейтинга собак по выставочным результатам.",
    tech: ["Python", "Django", "Chart.js"],
  },
  {
    status: "development",
    title: "Интеграция с BreedArchive",
    desc: "Связь российского архива с международной базой данных для глобального доступа.",
    tech: ["API", "REST", "JSON"],
  },
  {
    status: "planning",
    title: "AI-ассистент НКП",
    desc: "Чат-бот на базе знаний клуба для консультаций по породе и документообороту.",
    tech: ["GPT", "NLP", "Vector DB"],
  },
];

function parseList(raw: unknown): string[] {
  try {
    const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => (typeof item === "string" ? item : null))
      .filter((p): p is string => Boolean(p));
  } catch {
    return [];
  }
}

function parseMaterials(raw: unknown): MaterialItem[] {
  try {
    const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item, index): MaterialItem | null => {
        if (typeof item === "string") {
          return { id: `${index}`, title: item, url: item.startsWith("http") ? item : null };
        }
        if (item && typeof item === "object") {
          const title = typeof (item as any).title === "string" ? (item as any).title : null;
          const url = typeof (item as any).url === "string" ? (item as any).url : null;
          if (title || url) {
            return { id: String((item as any).id ?? index), title: title || url || "Материал", url };
          }
        }
        return null;
      })
      .filter((m): m is MaterialItem => Boolean(m));
  } catch {
    return [];
  }
}

function parseWorkDirections(raw: unknown): WorkDirection[] {
  const list = parseList(raw);
  const result: WorkDirection[] = [];
  for (let i = 0; i < list.length; i += 3) {
    const title = list[i] || "";
    const desc = list[i + 1] || "";
    const icon = list[i + 2] || null;
    if (title || desc || icon) {
      result.push({ title, desc, icon });
    }
  }
  return result;
}

export default function Judge() {
  const { id } = useParams();
  const pageRef = useRef<HTMLDivElement | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [judge, setJudge] = useState<JudgePayload | null>(null);
  const [details, setDetails] = useState<JudgeDetailsPayload | null>(null);
  const [bio, setBio] = useState<string[]>([]);
  const [workDirections, setWorkDirections] = useState<WorkDirection[]>([]);
  const [initiativeStack, setInitiativeStack] = useState<string[]>([]);
  const [sidebarAchievements, setSidebarAchievements] = useState<string[]>([]);

  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    const targets = root.querySelectorAll<HTMLElement>(".judge-section, .judge-aside-card, .judge-hero-card");

    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.setAttribute("data-visible", "1");
        }),
      { threshold: 0.12, rootMargin: "0px 0px -50px 0px" }
    );

    targets.forEach((el) => {
      el.setAttribute("data-visible", "0");
      io.observe(el);
    });

    return () => io.disconnect();
  }, []);

  useEffect(() => {
    let ignore = false;
    if (!id) return;

    const load = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/judges/${id}/`);
        if (!res.ok) {
          if (!ignore) setNotFound(true);
          return;
        }
        const payload: JudgePayload = await res.json();
        if (ignore) return;
        setJudge(payload);

        if (payload?.judge_id) {
          try {
            const detRes = await fetch(`/api/judge-details/${payload.judge_id}/`);
            if (detRes.ok) {
              const det: JudgeDetailsPayload = await detRes.json();
              if (!ignore) {
                setDetails(det);
                setBio(parseList(det.info));
                setWorkDirections(parseWorkDirections(det.work_directions));
                setInitiativeStack(parseList(det.initiative_stack));
                setSidebarAchievements(parseList(det.sidebar_achievements));
              }
            }
          } catch {
            // ignore details errors
          }
        }
      } catch {
        if (!ignore) setNotFound(true);
      } finally {
        if (!ignore) setLoading(false);
      }
    };

    load();
    return () => {
      ignore = true;
    };
  }, [id]);

  const heroInitial = useMemo(() => {
    const letter = judge?.name?.trim().charAt(0);
    return letter || "J";
  }, [judge?.name]);

  const bioParagraphs = bio;
  const highlightTitle = parseList(details?.additional_info_title)[0] || "";
  const highlightText = parseList(details?.additional_info_text)[0] || "";
  const responsibilities = workDirections;
  const projects =
    details?.initiative_title || details?.initiative_state || details?.initiative_text
      ? [
          {
            status: details?.initiative_state || "active",
            title: details?.initiative_title || "Инициатива",
            desc: details?.initiative_text || "Описание инициативы в процессе обновления.",
            tech: initiativeStack.length ? initiativeStack : ["API", "Data"],
          },
        ]
      : defaultProjects;

  const getStatusClass = (status?: string | null) => {
    if (!status) return "status-active";
    if (status === "in developing" || status === "development") return "status-development";
    if (status === "planning") return "status-planning";
    return status === "active" ? "status-active" : "status-active";
  };

  const sidebarText =
    details?.sidebar_text ||
    "Команда информационных систем занимается экосистемой сервисов НКП: сайт, архив, аналитика, интеграции и поддержка IT-инфраструктуры клуба.";

  const badgePalette = ["badge-blue", "badge-green", "badge-orange"];
  const getBadgeClass = (idx: number) => badgePalette[idx] || badgePalette[badgePalette.length - 1];

  return (
    <div className="judge-page" ref={pageRef}>
      <div className="judge-ambient">
        <div className="judge-shape judge-shape--one" />
        <div className="judge-shape judge-shape--two" />
        <div className="judge-shape judge-shape--three" />
      </div>

      <Breadcrumb
        title={judge?.name || "Эксперт"}
        items={[
          { label: "Главная", to: "/" },
          { label: "События", to: "/events" },
          { label: judge?.name || "Эксперт" },
        ]}
      />

      <main className="judge-main">
        <div className="judge-container">
          <div className="judge-grid">
            <div className="judge-col">
              <section className="judge-section judge-card">
                {loading && <p className="judge-muted">Загрузка данных...</p>}
                {notFound && !loading && <p className="judge-muted">Эксперт не найден.</p>}
                {!loading && (
                  <>
                    {bioParagraphs.map((p, idx) => (
                      <p key={idx} className="judge-text">
                        {p}
                      </p>
                    ))}
                    {(highlightTitle || highlightText) && (
                      <div className="judge-highlight">
                        {highlightTitle && <h3>{highlightTitle}</h3>}
                        {highlightText && <p>{highlightText}</p>}
                      </div>
                    )}
                  </>
                )}
              </section>

              <section className="judge-section judge-card">
                <h2 className="judge-section-title mt-0">Основные направления работы</h2>
                {responsibilities.length > 0 ? (
                  <div className="judge-resp-grid">
                    {responsibilities.map((item, idx) => (
                      <div key={idx} className="judge-resp-card">
                        <div className="judge-resp-head">
                          <div className="judge-resp-icon">{item.icon}</div>
                          <h3 className="judge-resp-title">{item.title}</h3>
                        </div>
                        <p className="judge-resp-desc judge-muted">{item.desc}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="judge-muted">Данные скоро появятся.</p>
                )}
              </section>

              <section className="judge-section judge-card">
                <h2 className="judge-section-title">Инициативы и проекты</h2>
                <div className="judge-projects-grid">
                  {projects.map((project, idx) => {
                    const statusClass = getStatusClass(project.status);
                    const statusLabel =
                      project.status === "planning"
                        ? "Планирование"
                        : project.status === "in developing" || project.status === "development"
                        ? "В разработке"
                        : "Активный";
                    return (
                      <article key={idx} className={`judge-project-card ${statusClass}`}>
                        <span className={`judge-project-status ${statusClass}`}>{statusLabel}</span>
                        <h3 className="judge-project-title">{project.title}</h3>
                        <p className="judge-muted">{project.desc}</p>
                        {project.tech?.length > 0 && (
                          <div className="judge-project-tags">
                            {project.tech.map((tag) => (
                              <span key={tag} className="judge-project-tag">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </article>
                    );
                  })}
                </div>
              </section>
            </div>

            <aside className="judge-sidebar">
              <div className="judge-aside-card judge-aside-profile">
                <div className="judge-aside-avatar">
                  <div className="judge-aside-avatar-ring" />
                  {judge?.photo ? <img src={judge.photo} alt={judge.name} /> : <span>{heroInitial}</span>}
                </div>
                <h3 className="judge-aside-name">{judge?.name || "Влада Кугуракова"}</h3>
                <div className="judge-aside-role">{judge?.rank || "Руководитель группы"}</div>
                <p className="judge-aside-text">{sidebarText}</p>
                {sidebarAchievements.length > 0 && (
                  <div className="judge-aside-badges">
                    {sidebarAchievements.map((item, idx) => {
                      const badgeClass = getBadgeClass(idx);
                      return (
                        <span key={`${item}-${idx}`} className={`judge-aside-badge ${badgeClass}`}>
                          {item}
                        </span>
                      );
                    })}
                  </div>
                )}
                <div className="judge-aside-actions">
                  {judge?.email && (
                    <a className="judge-pill-link" href={`mailto:${judge.email}`}>
                      ?? Написать письмо
                    </a>
                  )}
                  {details?.kennel_url && (
                    <a
                      className="judge-pill-link judge-pill-link--ghost"
                      href={details.kennel_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      ?? {details?.kennel || "Питомник"}
                    </a>
                  )}
                  <Link className="judge-pill-link judge-pill-link--ghost" to="/events">
                    ?? Предложить идею
                  </Link>
                </div>
              </div>

              <div className="judge-aside-card judge-aside-quick">
                <h4 className="judge-aside-quick-title">?? Быстрые ссылки</h4>
                <ul className="judge-aside-links">
                  <li>
                    <Link to="/">?? Личный кабинет</Link>
                  </li>
                  <li>
                    <Link to="/archive">?? Породный архив</Link>
                  </li>
                  <li>
                    <Link to="/rating">?? Рейтинг собак</Link>
                  </li>
                  <li>
                    <Link to="/support">?? Техническая поддержка</Link>
                  </li>
                  <li>
                    <Link to="/api">?? API документация</Link>
                  </li>
                  <li>
                    <Link to="/feedback">?? Сообщить об ошибке</Link>
                  </li>
                </ul>
              </div>
            </aside>
          </div>
        </div>
      </main>
    </div>
  );
}
