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
  initiatives?: unknown;
  sidebar_text?: string | null;
  sidebar_achievements?: unknown;
  kennel_url?: string | null;
  kennel?: string | null;
};

type WorkDirection = {
  title: string;
  desc: string;
  icon?: string | null;
};

type Initiative = {
  title: string;
  desc: string;
  status: string;
  tech: string[];
};

function normalizeStatus(value: string): string {
  const raw = (value || "").toString().trim().toLowerCase();
  if (!raw) return "active";
  if (["active", "активно", "активный"].includes(raw)) return "active";
  if (["in developing", "developing", "development", "в разработке", "разработка"].includes(raw)) return "in developing";
  if (["planning", "plan", "планирование", "в планировании", "план"].includes(raw)) return "planning";
  return raw;
}

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

function parseInitiatives(raw: unknown): Initiative[] {
  const list = parseList(raw);
  const result: Initiative[] = [];
  for (let i = 0; i < list.length; i += 4) {
    const title = list[i] || "";
    const desc = list[i + 1] || "";
    const status = normalizeStatus(list[i + 2] || "active");
    const stackRaw = list[i + 3] || "";
    const parsedStack = parseList(stackRaw);
    const tech =
      parsedStack.length > 0
        ? parsedStack
        : String(stackRaw)
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);

    if (title || desc || status || tech.length) {
      result.push({ title, desc, status, tech });
    }
  }
  return result;
}

export default function Judge() {
  const { id } = useParams();
  const pageRef = useRef<HTMLDivElement | null>(null);
  const sidebarRef = useRef<HTMLDivElement | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [judge, setJudge] = useState<JudgePayload | null>(null);
  const [details, setDetails] = useState<JudgeDetailsPayload | null>(null);
  const [bio, setBio] = useState<string[]>([]);
  const [workDirections, setWorkDirections] = useState<WorkDirection[]>([]);
  const [initiatives, setInitiatives] = useState<Initiative[]>([]);
  const [sidebarAchievements, setSidebarAchievements] = useState<string[]>([]);
  const [isSticky, setIsSticky] = useState(false);
  const stickyTopPx = 120;
  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    // важно: запускать только когда страница уже не в загрузке
    if (loading) return;

    const targets = root.querySelectorAll<HTMLElement>(
      ".judge-section, .judge-aside-card, .judge-hero-card"
    );
    if (!targets.length) return;

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
  }, [
    loading,
    judge,
    details,
    bio.length,
    workDirections.length,
    initiatives.length,
    sidebarAchievements.length,
  ]);


  useEffect(() => {
    const handleScroll = () => {
      if (!sidebarRef.current) return;
      const rect = sidebarRef.current.getBoundingClientRect();
      const shouldStick = rect.top <= stickyTopPx;
      setIsSticky((prev) => (prev !== shouldStick ? shouldStick : prev));
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [stickyTopPx]);

  useEffect(() => {
    let ignore = false;
    if (!id) return;

    const load = async () => {
      setLoading(true);
      setNotFound(false);
      setJudge(null);
      setDetails(null);
      setBio([]);
      setWorkDirections([]);
      setInitiatives([]);
      setSidebarAchievements([]);

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
                setInitiatives(parseInitiatives(det.initiatives));
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
  const projects = initiatives.length ? initiatives : defaultProjects;

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
  if (loading) {
  return (
    <div className="judge-page" ref={pageRef}>
      <Breadcrumb
        title="Эксперт"
        items={[
          { label: "Главная", to: "/" },
          { label: "Судьи", to: "/judges" },
          { label: "Эксперт" },
        ]}
      />
      <main className="judge-main">
        <div className="judge-container">
          <section className="judge-section judge-card" data-visible="1">
            <p className="judge-muted">Загрузка данных...</p>
          </section>
        </div>
      </main>
    </div>
  );
}

if (notFound || !judge) {
  return (
    <div className="judge-page" ref={pageRef}>
      <Breadcrumb
        title="Эксперт"
        items={[
          { label: "Главная", to: "/" },
          { label: "Судьи", to: "/judges" },
          { label: "Эксперт" },
        ]}
      />
      <main className="judge-main">
        <div className="judge-container">
          <section className="judge-section judge-card" data-visible="1">
            <p className="judge-muted">Эксперт не найден.</p>
            <div style={{ marginTop: 12 }}>
              <Link className="judge-pill-link" to="/judges">
                ← К списку судей
              </Link>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

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
                {/*{notFound && !loading && <p className="judge-muted">Эксперт не найден.</p>}*/}
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
                <h2 className="judge-section-title mt-0">Инициативы и проекты</h2>
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

              <section className="judge-section judge-cta">
                <div className="judge-cta-inner">
                  <h2 className="judge-section-title judge-section-title--light mt-0 section-title--no-underline">Присоединяйтесь к работе группы</h2>
                  <p className="judge-cta-text">
                    Мы открыты для IT-специалистов, студентов и энтузиастов, которые хотят внести вклад в развитие породы
                    сибирский хаски. Это возможность применить навыки в реальных проектах, поработать с данными и создать значимые сервисы.
                  </p>
                  <p className="judge-cta-text">
                    Независимо от опыта — найдется задача: веб-разработка, базы данных, машинное обучение, компьютерное зрение
                    или мобильные приложения. Присоединяйтесь к команде и помогайте развивать цифровую экосистему НКП.
                  </p>
                  <div className="judge-cta-actions">
                    <Link className="judge-pill-link" to="/support">
                      🚀 Присоединиться к команде
                    </Link>
                  </div>
                </div>
              </section>
            </div>

            <aside className="judge-sidebar">
              <div className="judge-sidebar__container">
                <div className="judge-sidebar__empty"></div>
                <div
                  className={`judge-sidebar__sticky ${isSticky ? "judge-sidebar__sticky--fixed" : ""}`}
                  ref={sidebarRef}
                >
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
                          📧   Написать письмо
                        </a>
                      )}
                      {details?.kennel_url && (
                        <a
                          className="judge-pill-link judge-pill-link--ghost"
                          href={details.kennel_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          🌐 {details?.kennel || "Питомник"}
                        </a>
                      )}
                    </div>
                  </div>

                  <div className="judge-aside-card judge-aside-quick">
                    <h4 className="judge-aside-quick-title">🔗 Быстрые ссылки</h4>
                    <ul className="judge-aside-links">
                      <li>
                        <Link to="/">🏠 Личный кабинет</Link>
                      </li>
                      <li>
                        <Link to="/archive">📊 Породный архив</Link>
                      </li>
                      <li>
                        <Link to="/rating">📈 Рейтинг собак</Link>
                      </li>
                      <li>
                        <Link to="/support">🔧 Техническая поддержка</Link>
                      </li>
                      <li>
                        <Link to="/api">📘 API документация</Link>
                      </li>
                      <li>
                        <Link to="/feedback">🐛 Сообщить об ошибке</Link>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </main>
    </div>
  );
}
