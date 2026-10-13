import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { fetchPuppies } from "@/api/puppies";
import { useAuth } from "@/lib/auth";
import PuppyCard from "./PuppyCard";
import "./Puppies.css";

export default function AllPuppies() {
    const { isAuthenticated } = useAuth();
    const [q, setQ] = useState("");
    const [search, setSearch] = useState("");
    const [sex, setSex] = useState("");
    const [status, setStatus] = useState("");
    const [nkp, setNkp] = useState(false);

    const { data, isLoading, isError, error } = useQuery({
        queryKey: ["puppies", search, sex, status, nkp],
        queryFn: () => fetchPuppies({ q: search, sex, status, nkp }),
    });

    const puppies = data?.results ?? [];

    const applySearch = (e: React.FormEvent) => {
        e.preventDefault();
        setSearch(q.trim());
    };

    const reset = () => {
        setQ("");
        setSearch("");
        setSex("");
        setStatus("");
        setNkp(false);
    };

    return (
        <div className="puppies-page">
            <Breadcrumb title="Щенки" items={[{ label: "Главная", to: "/" }, { label: "Щенки" }]} />

            <main className="puppies-main">
                <div className="content-container">
                    <div className="puppies-toolbar">
                        <div className="puppies-toolbar__intro">
                            <h2 className="puppies-toolbar__title">Щенки от заводчиков</h2>
                            <p className="puppies-toolbar__subtitle">
                                Актуальные объявления от владельцев и питомников
                            </p>
                        </div>
                        {isAuthenticated ? (
                            <Link to="/puppies/new" className="puppies-add-btn">＋ Разместить щенка</Link>
                        ) : (
                            <Link to="/login?redirect=/puppies/new" className="puppies-add-btn">
                                Войти и разместить
                            </Link>
                        )}
                    </div>

                    <form className="puppies-filters" onSubmit={applySearch}>
                        <div className="puppies-search">
                            <span aria-hidden>🔍</span>
                            <input
                                type="search"
                                placeholder="Поиск по кличке, питомнику или городу…"
                                value={q}
                                onChange={(e) => setQ(e.target.value)}
                            />
                        </div>

                        <select value={sex} onChange={(e) => setSex(e.target.value)}>
                            <option value="">Любой пол</option>
                            <option value="male">Кобель</option>
                            <option value="female">Сука</option>
                        </select>

                        <select value={status} onChange={(e) => setStatus(e.target.value)}>
                            <option value="">Любой статус</option>
                            <option value="available">Доступен</option>
                            <option value="reserved">Забронирован</option>
                            <option value="sold">Продан</option>
                        </select>

                        <label className="puppies-nkp-toggle">
                            <input type="checkbox" checked={nkp} onChange={(e) => setNkp(e.target.checked)} />
                            Только НКП
                        </label>

                        <button type="submit" className="puppies-filter-btn">Найти</button>
                        <button type="button" className="puppies-filter-btn puppies-filter-btn--soft" onClick={reset}>
                            Сбросить
                        </button>
                    </form>

                    {isLoading && <div className="puppies-state">Загрузка…</div>}
                    {isError && (
                        <div className="puppies-state puppies-state--error">
                            {error instanceof Error ? error.message : "Ошибка загрузки"}
                        </div>
                    )}

                    {!isLoading && !isError && puppies.length === 0 && (
                        <div className="puppies-state">
                            Объявлений пока нет.{" "}
                            {isAuthenticated && <Link to="/puppies/new">Разместите первое →</Link>}
                        </div>
                    )}

                    {puppies.length > 0 && (
                        <div className="puppies-grid">
                            {puppies.map((p) => (
                                <PuppyCard key={p.id} puppy={p} />
                            ))}
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
