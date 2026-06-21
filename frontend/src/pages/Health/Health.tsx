import {useEffect, useRef, useState} from "react";
import {Link} from "react-router-dom";
import {useQuery} from "@tanstack/react-query";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./Health.css";

interface HealthRecord {
    id: number;
    dog_id: number;
    dog_name: string;
    registry: string;
    conclusion: string | null;
    test_date: string | null;
    ofa_number: string | null;
}

interface HealthResponse {
    count: number;
    page: number;
    per_page: number;
    results: HealthRecord[];
}


function Pagination({page, totalPages, onChange}: {
    page: number;
    totalPages: number;
    onChange: (p: number) => void;
}) {
    if (totalPages <= 1) return null;

    const pages: (number | "...")[] = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
        pages.push(1);
        if (page > 3) pages.push("...");
        for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) pages.push(i);
        if (page < totalPages - 2) pages.push("...");
        pages.push(totalPages);
    }

    return (
        <div className="archive-pagination">
            <button
                className="archive-page-btn"
                disabled={page === 1}
                onClick={() => onChange(page - 1)}
            >
                « Пред
            </button>
            {pages.map((p, i) =>
                p === "..." ? (
                    <span key={`e${i}`} className="archive-page-ellipsis">…</span>
                ) : (
                    <button
                        key={p}
                        className={`archive-page-btn${p === page ? " is-active" : ""}`}
                        onClick={() => onChange(p as number)}
                    >
                        {p}
                    </button>
                )
            )}
            <button
                className="archive-page-btn"
                disabled={page === totalPages}
                onClick={() => onChange(page + 1)}
            >
                След »
            </button>
        </div>
    );
}

export default function Health() {
    const pageRef = useRef<HTMLDivElement | null>(null);

    const [query, setQuery] = useState("");
    const [registry, setRegistry] = useState("");
    const [conclusion, setConclusion] = useState("");
    const [activeQuery, setActiveQuery] = useState("");
    const [activeRegistry, setActiveRegistry] = useState("");
    const [activeConclusion, setActiveConclusion] = useState("");
    const [activePage, setActivePage] = useState(1);
    const [searched, setSearched] = useState(false);

    const {data: stats} = useQuery({
        queryKey: ["health-stats"],
        queryFn: () => fetch("/api/dogs/health/stats/").then(r => r.json()),
        staleTime: 3600_000,
    });

    const {data: registries = []} = useQuery<string[]>({
        queryKey: ["health-registries"],
        queryFn: () => fetch("/api/dogs/health/registries/").then(r => r.json()),
        staleTime: 3600_000,
    });

    const {data, isFetching} = useQuery<HealthResponse>({
        queryKey: ["health-search", activeQuery, activeRegistry, activeConclusion, activePage],
        queryFn: () => {
            const sp = new URLSearchParams();
            if (activeQuery) sp.set("q", activeQuery);
            if (activeRegistry) sp.set("registry", activeRegistry);
            if (activeConclusion) sp.set("conclusion", activeConclusion);
            sp.set("page", String(activePage));
            sp.set("per_page", "20");
            return fetch(`/api/dogs/health/search/?${sp}`).then(r => r.json());
        },
        enabled: searched,
        staleTime: 30_000,
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setActivePage(1);
        setActiveQuery(query);
        setActiveRegistry(registry);
        setActiveConclusion(conclusion);
        setSearched(true);
    };

    const totalPages = data?.count && data?.per_page ? Math.ceil(data.count / data.per_page) : 0;
    useEffect(() => {
        const root = pageRef.current;
        if (!root) return;
        const els = root.querySelectorAll<HTMLElement>(
            ".health-search-section, .health-stats .health-stat, .health-card"
        );
        const io = new IntersectionObserver(
            (entries) => entries.forEach((e) => e.isIntersecting && e.target.setAttribute("data-visible", "1")),
            {threshold: 0.12, rootMargin: "0px 0px -50px 0px"}
        );
        els.forEach((el) => {
            el.setAttribute("data-visible", "0");
            io.observe(el);
        });
        return () => io.disconnect();
    }, [searched]);

    useEffect(() => {
        const nums = pageRef.current?.querySelectorAll<HTMLElement>(".health-stat-number");
        if (!nums) return;
        nums.forEach((node) => {
            const raw = node.dataset.target || node.textContent || "0";
            const target = parseInt(raw.replace(/[^\d]/g, ""), 10);
            let cur = 0;
            const step = Math.max(1, Math.floor(target / 100));
            const t = setInterval(() => {
                cur += step;
                if (cur >= target) {
                    cur = target;
                    clearInterval(t);
                }
                node.textContent = cur.toLocaleString("ru-RU");
            }, 16);
        });
    }, []);

    const pctNormal = (() => {
        if (!stats?.by_group) return 0;
        const groups = Object.values(stats.by_group) as Array<{ total: number; normal: number }>;
        const totalNormal = groups.reduce((s, g) => s + (g.normal ?? 0), 0);
        const totalAll = groups.reduce((s, g) => s + (g.total ?? 0), 0);
        return totalAll ? Math.round(totalNormal / totalAll * 100) : 0;
    })();

    return (
        <div ref={pageRef} className="health-page">
            <Breadcrumb
                title="Здоровье породы"
                items={[{label: "Главная", to: "/"}, {label: "Здоровье породы"}]}
            />

            <main className="health-main">
                <div className="health-container">
                    <div className="health-col">

                        <section className="health-search-section">
                            <div className="health-search-head">
                                <h2 className="health-title">Поиск по медицинским тестам</h2>
                                <p className="health-sub">
                                    Введите кличку, клеймо или регистрационный номер, чтобы найти результаты тестов.
                                </p>
                            </div>

                            <form className="health-search-form" onSubmit={handleSubmit}>
                                <input
                                    className="health-input"
                                    placeholder="Например: Arctic Storm's Thunder King…"
                                    value={query}
                                    onChange={e => setQuery(e.target.value)}
                                />
                                <button type="submit" className="health-btn health-btn--primary">
                                    🔍 Найти
                                </button>
                            </form>

                            <div className="health-filters">
                                <select className="health-select" value={registry}
                                        onChange={e => setRegistry(e.target.value)}>
                                    <option value="">Все тесты</option>
                                    {registries.map(r => (
                                        <option key={r} value={r}>{r}</option>
                                    ))}
                                </select>
                                <select className="health-select" value={conclusion}
                                        onChange={e => setConclusion(e.target.value)}>
                                    <option value="">Любой статус</option>
                                    <option value="EXCELLENT">Excellent</option>
                                    <option value="GOOD">Good</option>
                                    <option value="FAIR">Fair</option>
                                    <option value="NORMAL">Normal</option>
                                    <option value="CLEAR">Clear</option>
                                    <option value="CARRIER">Carrier</option>
                                    <option value="AFFECTED">Affected</option>
                                </select>
                            </div>
                        </section>

                        {searched && (
                            <section className="health-card">
                                <div className="health-results-head">
                                    <h3 className="health-card-title" style={{margin: 0}}>Результаты</h3>
                                    {!isFetching && data?.count != null && (
                                        <span className="health-results-count">
                                            {data.count.toLocaleString("ru-RU")} записей
                                        </span>
                                    )}
                                </div>

                                {isFetching && <div className="health-results-empty">Загрузка…</div>}

                                {!isFetching && data?.results?.length === 0 && (
                                    <div className="health-results-empty">Ничего не найдено</div>
                                )}

                                {!isFetching && data?.results && data.results.length > 0 && (
                                    <>
                                        <div className="health-table-wrap">
                                            <table className="health-table">
                                                <thead>
                                                <tr>
                                                    <th>Собака</th>
                                                    <th>Тест</th>
                                                    <th>Результат</th>
                                                    <th>Дата теста</th>
                                                    <th>OFA №</th>
                                                </tr>
                                                </thead>
                                                <tbody>
                                                {data.results.map(r => (
                                                    <tr key={r.id}>
                                                        <td>
                                                            <Link to={`/archive/dog/${r.dog_id}`}
                                                                  className="health-table-link">
                                                                {r.dog_name}
                                                            </Link>
                                                        </td>
                                                        <td>{r.registry}</td>
                                                        <td style={{fontWeight: 600}}>
                                                            {r.conclusion || "—"}
                                                        </td>
                                                        <td className="health-table-muted">{r.test_date || "—"}</td>
                                                        <td className="health-table-muted">{r.ofa_number || "—"}</td>
                                                    </tr>
                                                ))}
                                                </tbody>
                                            </table>
                                        </div>

                                        <Pagination
                                            page={activePage}
                                            totalPages={totalPages}
                                            onChange={setActivePage}
                                        />
                                    </>
                                )}
                            </section>
                        )}

                        <section className="health-stats">
                            {[
                                {icon: "🧬", num: String(stats?.total_records ?? 0), label: "Проведено тестов"},
                                {icon: "🐾", num: String(stats?.dogs_tested ?? 0), label: "Собак с результатами"},
                                {icon: "🟢", num: String(pctNormal), suffix: "%", label: "Норм. результаты"},
                                {
                                    icon: "🧪",
                                    num: String(Object.keys(stats?.by_group ?? {}).length),
                                    label: "Типов тестов"
                                },
                            ].map((s) => (
                                <article className="health-stat" key={s.label}>
                                    <div className="health-stat-icon">{s.icon}</div>
                                    <div className="health-stat-number" data-target={s.num}
                                         style={{fontVariantNumeric: "tabular-nums"}}>
                                        {s.suffix ? `${s.num}${s.suffix}` : s.num}
                                    </div>
                                    <div className="health-stat-label">{s.label}</div>
                                    {/*<div className="health-stat-trend">{s.trend}</div>*/}
                                </article>
                            ))}
                        </section>

                        <section className="health-card">
                            <h3 className="health-card-title">Объяснение статусов</h3>
                            <ul className="health-list">
                                <li><b>Clear:</b> собака не несёт мутаций по данному заболеванию.</li>
                                <li><b>Carrier:</b> носитель — не болен, но может передать мутацию потомству.</li>
                                <li><b>Affected:</b> имеет мутацию и может быть подвержен заболеванию.</li>
                                <li><b>SHOR Normal:</b> нормальный результат офтальмологического обследования.</li>
                            </ul>
                        </section>

                        <section className="health-card">
                            <h3 className="health-card-title">Как сдать ДНК-тест</h3>
                            <ul className="health-list">
                                <li>1. Выберите лабораторию: ЗООГЕН, Embark, Genomia.</li>
                                <li>2. Закажите набор для сбора образца (слюна или мазок).</li>
                                <li>3. Отправьте образец и дождитесь результата (обычно 2–3 недели).</li>
                                <li>4. Внесите данные в базу НКП (форма «добавить результат»).</li>
                            </ul>
                        </section>

                    </div>
                </div>
            </main>
        </div>
    );
}
