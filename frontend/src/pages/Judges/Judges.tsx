import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { useJudgesList } from "@/generated/judges/judges";
import "./Judges.css";

type JudgeItem = {
  id: string;
  name: string;
  rank?: string | null;
  email?: string | null;
  photo?: string | null;
  judgeId?: string | null;
};

export default function Judges() {
  const pageRef = useRef<HTMLDivElement | null>(null);
  const [q, setQ] = useState("");

  const { data: judgesData, isLoading: loading } = useJudgesList();

  const judges = useMemo((): JudgeItem[] => {
    const fromApi = judgesData?.data?.results ?? [];
    return fromApi
      .map((judge, index): JudgeItem | null => {
        if (!judge) return null;
        const name = typeof judge.name === "string" ? judge.name : null;
        if (!name) return null;
        return {
          id: String(judge.id ?? index),
          name,
          rank: judge.rank ?? null,
          email: judge.email ?? null,
          photo: judge.photo ?? null,
          judgeId: judge.judge_id != null ? String(judge.judge_id) : null,
        };
      })
      .filter((x): x is JudgeItem => Boolean(x));
  }, [judgesData]);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (!query) return judges;

    return judges.filter((j) => {
      const name = (j.name || "").toLowerCase();
      const rank = (j.rank || "").toLowerCase();
      return name.includes(query) || rank.includes(query);
    });
  }, [judges, q]);

  const getInitial = (name?: string | null) => (name?.trim()?.charAt(0) ? name.trim().charAt(0) : "J");

  return (
    <div className="judges-page" ref={pageRef}>
      <Breadcrumb
        title="Судьи"
        items={[
          { label: "Главная", to: "/" },
          { label: "Мероприятия", to: "/events" },
          { label: "Судьи", to: "/judges" },
        ]}
      />

      <main className="judges-main">
        <div className="judges-container">
          <div className="judges-head">
            <div className="judges-search">
              <input
                className="judges-search-input"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Поиск по имени или должности…"
              />
            </div>
          </div>

          {loading ? (
            <div className="judges-muted">Загрузка…</div>
          ) : filtered.length === 0 ? (
            <div className="judges-muted">Ничего не найдено.</div>
          ) : (
            <div className="judges-grid">
              {filtered.map((j) => (
                <Link key={j.id} to={`/judges/${j.id}`} className="judge-card">
                  <div className="judge-card-avatar">
                    {j.photo ? <img src={j.photo} alt={j.name} /> : <span>{getInitial(j.name)}</span>}
                  </div>

                  <div className="judge-card-name">{j.name}</div>
                  {j.rank && <div className="judge-card-rank">{j.rank}</div>}

                  {j.email && (
                    <div className="judge-card-email" onClick={(e) => e.preventDefault()}>
                      <a href={`mailto:${j.email}`}>{j.email}</a>
                    </div>
                  )}

                  <div className="judge-card-cta">Открыть профиль →</div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
