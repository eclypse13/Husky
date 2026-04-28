import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./President.css";



    type PresidentBadge = {
        icon: string;
        text: string;
        is_primary: boolean;
        sort_order: number;
    };

    type PresidentAchievement = {
        year: string;
        title: string;
        text: string;
        sort_order: number;
    };

    type PresidentData = {
        id: number;
        full_name: string;
        position: string;
        subtitle: string;
        main_text: string;
        highlight_text: string;
        quote: string;
        email: string;
        phone: string;
        reception_days: string;
        socials: string;
        badges: PresidentBadge[];
        achievements: PresidentAchievement[];
    };


export default function President() {
    const renderTextParagraphs = (text?: string) => {
        if (!text) return null;

        return text
            .split(/\n\s*\n/)
            .filter(Boolean)
            .map((paragraph, index) => (
                <p key={index}>{paragraph}</p>
            ));
    };

    const pageRef = useRef<HTMLDivElement | null>(null);
    const [president, setPresident] = useState<PresidentData | null>(null);
    // const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const root = pageRef.current;
        if (!root) return;

        const targets = root.querySelectorAll<HTMLElement>(
            ".president-section, .president-sidebar-card, .president-timeline-item"
        );

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
    }, [president]);

    useEffect(() => {
        const nums = pageRef.current?.querySelectorAll<HTMLElement>(".president-stat-number");
        if (!nums) return;
        nums.forEach((node) => {
            const raw = node.textContent || "";
            const target = parseInt(raw.replace(/[^\d]/g, ""), 10);
            const hasPlus = /\+$/.test(raw);
            let cur = 0;
            const step = Math.max(1, Math.floor(target / 90));
            const timer = setInterval(() => {
                cur += step;
                if (cur >= target) {
                    cur = target;
                    clearInterval(timer);
                }
                node.textContent = cur.toLocaleString("ru-RU") + (hasPlus ? "+" : "");
            }, 16);
        });
    }, []);

    useEffect(() => {
        let ignore = false;

        fetch("/api/president/active/")
            .then((res) => {
                if (!res.ok) throw new Error("President not found");
                return res.json();
            })
            .then((data: PresidentData) => {
                if (!ignore) setPresident(data);
            })
            .catch(() => {
                if (!ignore) setPresident(null);
            })
            .finally(() => {
                if (!ignore) setIsLoading(false);
            });

        return () => {
            ignore = true;
        };
    }, []);

    return (
        <div ref={pageRef} className="president-page">
            <Breadcrumb
                title="Президент НКП"
                items={[
                    { label: "Главная", to: "/" },
                    { label: "О клубе", to: "/about" },
                    { label: "Президиум НКП", to: "/about#board" },
                    { label: "Татьяна Евграфова" },
                ]}
            />

            <main className="president-main">
                <div className="president-container">
                    {/* Hero */}
                    <section className="president-section president-profile">
                        <div className="president-profile-hero">
                            <div className="president-avatar">
                                <div className="president-avatar-ring" />
                                <span role="img" aria-label="avatar">👩‍💼</span>
                            </div>

                            <div className="president-profile-info">
                                <h1 className="president-name">
                                    {president?.full_name || "Татьяна Евграфова"}
                                </h1>

                                <div className="president-title">
                                    {president?.position || "Президент НКП Сибирский Хаски"}
                                </div>

                                <p className="president-subtitle">
                                    {president?.subtitle || "Ведущий эксперт по породе сибирский хаски..."}
                                </p>
                                <div className="president-badges">
                                    {(president?.badges || [
                                        { icon: "👑", text: "Президент НКП", is_primary: true, sort_order: 0 },
                                        { icon: "📅", text: "15+ лет опыта", is_primary: false, sort_order: 1 },
                                    ]).map((badge) => (
                                        <span
                                            key={`${badge.icon}-${badge.text}`}
                                            className={
                                                badge.is_primary
                                                    ? "president-badge president-badge--primary"
                                                    : "president-badge president-badge--light"
                                            }
                                        >
                                            {badge.icon} {badge.text}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            <div className="president-actions">
                                <Link to="/contact" className="president-btn president-btn--primary">📧 Написать письмо</Link>
                                <Link to="/contact" className="president-btn">📋 Задать вопрос</Link>
                                <Link to="/contact" className="president-btn">🗓️ Записаться на консультацию</Link>
                            </div>
                        </div>
                    </section>

                    <div className="president-grid">
                        {/* Левая колонка */}
                        <div className="president-col">
                            {/* Биография */}
                            <section className="president-section president-bio">
                                <h2 className="president-section-title">О президенте</h2>
                                <div className="president-bio-content">
                                    {renderTextParagraphs(
                                        president?.main_text || "Татьяна Евграфова — признанный эксперт..."
                                    )}

                                    {president?.highlight_text && (
                                        <div className="president-highlight-box">
                                            <h4 className="president-highlight-title">
                                                Профессиональные достижения
                                            </h4>
                                            <p>{president.highlight_text}</p>
                                        </div>
                                    )}
                                </div>
                            </section>

                            {/* Области ответственности */}
                            <section className="president-section president-resp">
                                <h2 className="president-section-title">Области ответственности</h2>
                                <div className="president-resp-grid">
                                    {[
                                        {
                                            icon: "👑",
                                            title: "Общее руководство НКП",
                                            text:
                                                "Стратегическое планирование, координация работы всех подразделений, представление клуба на международном уровне, принятие ключевых решений по развитию организации.",
                                        },
                                        {
                                            icon: "🏆",
                                            title: "Выставочные мероприятия",
                                            text:
                                                "Руководство рабочей группой по организации выставок, координация с РКФ, работа с судьями, развитие выставочной деятельности и повышение качества экспертизы.",
                                        },
                                        {
                                            icon: "📐",
                                            title: "Стандарт породы",
                                            text:
                                                "Руководство рабочей группой по стандарту, работа с FCI, обновление породных требований, методическая работа с экспертами и развитие критериев оценки.",
                                        },
                                        {
                                            icon: "🎓",
                                            title: "Образовательная деятельность",
                                            text:
                                                "Проведение семинаров для заводчиков и экспертов, разработка обучающих материалов, менторство молодых специалистов, создание образовательных программ.",
                                        },
                                    ].map((r) => (
                                        <article key={r.title} className="president-resp-card">
                                            <h3 className="president-resp-title">
                                                <span className="president-resp-icon">{r.icon}</span>
                                                {r.title}
                                            </h3>
                                            <p className="president-resp-text">{r.text}</p>
                                        </article>
                                    ))}
                                </div>
                            </section>

                            {/* Рабочие группы */}
                            <section className="president-section president-groups">
                                <div className="president-groups-inner">
                                    <h2 className="president-section-title president-section-title--light">
                                        Руководство рабочими группами
                                    </h2>
                                    <p className="president-groups-lead">
                                        Татьяна возглавляет ключевые направления деятельности НКП, координируя работу специалистов в различных областях
                                    </p>

                                    <div className="president-groups-list">
                                        {[
                                            { icon: "🏆", title: "Выставочные мероприятия", members: "В составе: Алла Проферансова, Татьяна Солдатова" },
                                            { icon: "📐", title: "Стандарт породы", members: "В составе: А.А. Фалунина, Т.А. Солдатова, Е.М. Шепелёва, М.С. Акопова, И.Л. Швец" },
                                            { icon: "🌐", title: "Международное сотрудничество", members: "Координация с FCI, партнерство с breedarchive.com" },
                                            { icon: "📚", title: "Методическая работа", members: "Разработка обучающих материалов, проведение семинаров" },
                                        ].map((g) => (
                                            <div key={g.title} className="president-group-item">
                                                <div className="president-group-title"><span>{g.icon}</span>{g.title}</div>
                                                <div className="president-group-members">{g.members}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </section>

                            {/* Достижения */}
                            {(president?.achievements?.length ?? 0) > 0 && (
                                <section className="president-section president-achievements">
                                    <h2 className="president-section-title">Основные достижения</h2>
                                    <div className="president-timeline">
                                        <div className="president-timeline-line" />

                                        {president!.achievements.map((t) => (
                                            <div key={`${t.year}-${t.title}`} className="president-timeline-item">
                                                <div className="president-timeline-dot" />
                                                <div className="president-timeline-year">{t.year}</div>
                                                <div className="president-timeline-title">{t.title}</div>
                                                <div className="president-timeline-text">{t.text}</div>
                                            </div>
                                        ))}
                                    </div>
                                </section>
                            )}

                            {/* Цитата */}
                            {president?.quote && (
                                <section className="president-quote president-section">
                                    <div className="president-quote-text">
                                        "{president.quote}"
                                    </div>
                                    <div className="president-quote-author">
                                        — {president.full_name}
                                    </div>
                                </section>
                            )}
                        </div>

                        {/* Сайдбар */}
                        <aside className="president-sidebar">
                            <div className="president-sidebar-card">
                                <h3 className="president-sidebar-title">📞 Контактная информация</h3>
                                <div className="president-contact-list">
                                    {[
                                        { icon: "📧", label: "Email", value: president?.email },
                                        { icon: "📱", label: "Телефон", value: president?.phone },
                                        { icon: "🏢", label: "Приёмные дни", value: president?.reception_days },
                                        { icon: "🌐", label: "Соцсети", value: president?.socials },
                                    ]
                                        .filter((c) => c.value)
                                        .map((c) => (
                                            <div key={c.label} className="president-contact-item">
                                                <div className="president-contact-icon">{c.icon}</div>
                                                <div className="president-contact-details">
                                                    <div className="president-contact-label">{c.label}</div>
                                                    <div className="president-contact-value">{c.value}</div>
                                                </div>
                                            </div>
                                        ))}
                                </div>
                            </div>

                            <div className="president-sidebar-card">
                                <h3 className="president-sidebar-title">📊 Статистика руководства</h3>
                                <div className="president-stats-grid">
                                    {[
                                        { n: "15+", l: "Лет в НКП" },
                                        { n: "45+", l: "Выставок организовано" },
                                        { n: "200+", l: "Семинаров проведено" },
                                        { n: "1 250", l: "Членов в клубе" },
                                    ].map((s) => (
                                        <div key={s.l} className="president-stat">
                                            <div className="president-stat-number">{s.n}</div>
                                            <div className="president-stat-label">{s.l}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="president-sidebar-card">
                                <h3 className="president-sidebar-title">📅 Ближайшие мероприятия</h3>
                                <div className="president-side-stack">
                                    <div className="president-side-note president-side-note--green">
                                        <strong>🎓 Семинар для судей</strong>
                                        <div className="president-side-sub">25 июля 2025, Москва</div>
                                    </div>
                                    <div className="president-side-note president-side-note--orange">
                                        <strong>🏆 Специализированная выставка</strong>
                                        <div className="president-side-sub">15 августа 2025, СПб</div>
                                    </div>
                                    <div className="president-side-note president-side-note--blue">
                                        <strong>📋 Заседание Президиума</strong>
                                        <div className="president-side-sub">30 июля 2025, Online</div>
                                    </div>
                                    <Link to="/events" className="president-pill">Посмотреть календарь</Link>
                                </div>
                            </div>

                            <div className="president-sidebar-card">
                                <h3 className="president-sidebar-title">🔗 Полезные ссылки</h3>
                                <div className="president-links">
                                    <Link to="/profile" className="president-link">📊 Личный профиль эксперта</Link>
                                    <Link to="/publications" className="president-link">📚 Публикации и статьи</Link>
                                    <Link to="/videos" className="president-link">🎥 Видеолекции</Link>
                                    <Link to="/reports" className="president-link">📋 Отчёты о работе</Link>
                                </div>
                            </div>
                        </aside>
                    </div>
                </div>
            </main>
        </div>
    );
}
