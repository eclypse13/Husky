import {useState} from "react";
import "./RatingSidebar.css";
import {ShowsListModal} from "@/components/ShowsListModal/ShowsListModal";

const REGULATION_URL = "/docs/ПОЛОЖЕНИЕ_О_проведении_рейтинга_НКП_СИБИРСКИЙ_ХАСКИ_ФИНАЛ.docx";

export default function RatingSidebar() {
    const [showsListOpen, setShowsListOpen] = useState(false);

    return (
        <aside className="sidebar">
            <div className="sidebar-card">
                <h2 className="section-title">Что такое породный рейтинг?</h2>
                <div className="history-content">
                    <p className="sidebar-paragraph">
                        Породный рейтинг НКП — это ежегодная система оценки лучших представителей
                        породы на основе выставочных результатов, рабочих качеств и генетической информации.
                    </p>
                    <p className="sidebar-paragraph">
                        Рейтинг позволяет определить лучших производителей, молодых собак, питомники и помёты года.
                        В нём участвуют собаки, зарегистрированные членами НКП и обладающие подтверждёнными
                        достижениями.
                    </p>
                </div>
            </div>

            <div className="sidebar-card">
                <h3 className="sidebar-title">📄 Положение о рейтинге</h3>
                <p style={{fontSize: ".95rem", color: "var(--text-light)", marginBottom: "1rem"}}>
                    Подробные критерии, балльная система, правила расчёта.
                </p>
                <a
                    href={REGULATION_URL}
                    style={{
                        background: "var(--gradient-primary)",
                        color: "var(--snow-white)",
                        padding: "1rem",
                        borderRadius: "12px",
                        display: "block",
                        textAlign: "center",
                        fontWeight: 600,
                        textDecoration: "none",
                    }}
                >
                    Скачать PDF
                </a>
            </div>

            <div className="sidebar-card">
                <h3 className="sidebar-title">📥 Подать данные в рейтинг</h3>
                <p style={{fontSize: ".95rem", color: "var(--text-light)", marginBottom: "1rem"}}>
                    Если ваша собака участвует в выставках — пришлите информацию.
                </p>
                <a
                    href="#"
                    style={{
                        background: "var(--ice-blue)",
                        color: "var(--bright-blue)",
                        padding: "1rem",
                        borderRadius: "12px",
                        display: "block",
                        textAlign: "center",
                        fontWeight: 600,
                        textDecoration: "none",
                    }}
                >
                    Заполнить форму
                </a>
            </div>

            <div className="sidebar-card">
                <h3 className="sidebar-title">📋 Список выставок</h3>
                <p style={{fontSize: ".95rem", color: "var(--text-light)", marginBottom: "1rem"}}>
                    Все выставки сезона.
                </p>
                <button
                    onClick={() => setShowsListOpen(true)}
                    style={{
                        background: "var(--ice-blue)",
                        color: "var(--bright-blue)",
                        padding: "1rem",
                        borderRadius: "12px",
                        display: "block",
                        width: "100%",
                        textAlign: "center",
                        font: "inherit",
                        fontWeight: 600,
                        border: "none",
                        cursor: "pointer",
                        appearance: "none",
                        WebkitAppearance: "none",
                    }}
                >
                    Открыть список
                </button>
            </div>

            {/*<div className="sidebar-card">*/}
            {/*  <h3 className="sidebar-title">🏅 История победителей</h3>*/}
            {/*  <ul style={{ listStyle: "none", paddingLeft: 0, fontSize: ".95rem", lineHeight: 1.6 }}>*/}
            {/*    <li><a href="#" style={{ color: "var(--bright-blue)", textDecoration: "none" }}>2024 — Arctic Light’s Shadow</a></li>*/}
            {/*    <li><a href="#" style={{ color: "var(--bright-blue)", textDecoration: "none" }}>2023 — Silver Snow Aurora</a></li>*/}
            {/*    <li><a href="#" style={{ color: "var(--bright-blue)", textDecoration: "none" }}>2022 — Polaris Bright Flame</a></li>*/}
            {/*  </ul>*/}
            {/*</div>*/}

            {showsListOpen && (
                <ShowsListModal onClose={() => setShowsListOpen(false)}/>
            )}
        </aside>
    );
}