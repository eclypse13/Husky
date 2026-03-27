import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { getDict, pickValue } from "@/lib/dict";
import { useEventsRetrieve, useJudgesList } from "@/generated";
import "../Events/Events.css";

type JudgeItem = {
  id: string;
  name: string;
  rank?: string | null;
  email?: string | null;
  photo?: string | null;
};

const dateTime = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function eventTypeLabel(t?: string | null) {
  const v = (t || "").toLowerCase();
  if (v === "seminar") return "Семинар";
  if (v === "meeting") return "Встреча";
  if (v === "show" || v === "exhibition") return "Выставка";
  return t || "—";
}

export default function EventPage() {
  const { id } = useParams();
  const numId = Number(id);

  const { data: eventData, isLoading: eventLoading, error: eventError } = useEventsRetrieve(numId, {
    query: { enabled: !!id && !isNaN(numId) },
  });
  const { data: judgesData } = useJudgesList();

  const event = eventData?.data ?? null;
  const loading = eventLoading;
  const notFound = !eventLoading && !event;
  const err = eventError ? String(eventError) : null;

  const judgesIndex = useMemo(() => {
    const m = new Map<string, JudgeItem>();
    const list = judgesData?.data?.results ?? [];
    list.forEach((j, idx) => {
      if (!j) return;
      const name = typeof j.name === "string" ? j.name : null;
      if (!name) return;
      const jid = String(j.id ?? idx);
      m.set(jid, {
        id: jid,
        name,
        rank: typeof j.rank === "string" ? j.rank : null,
        email: typeof j.email === "string" ? j.email : null,
        photo: typeof j.photo === "string" ? j.photo : null,
      });
    });
    return m;
  }, [judgesData]);

  const [title, setTitle] = useState<string>("");
  const [desc, setDesc] = useState<string | null>(null);

  useEffect(() => {
    if (!event) return;
    let ignore = false;
    (async () => {
      const dict = await getDict();
      if (ignore) return;
      const titleKey = event.title_key || "";
      const descKey = (event as any).description_key || "";
      const titleFromDict = titleKey ? pickValue(dict, titleKey, "ru") : null;
      setTitle(titleFromDict || titleKey || `Мероприятие #${event.id}`);
      const descFromDict = descKey ? pickValue(dict, descKey, "ru") : null;
      setDesc(descFromDict || descKey || null);
    })();
    return () => { ignore = true; };
  }, [event]);

  if (loading) return <div style={{ padding: 24 }}>Загрузка…</div>;
  if (err) return <div style={{ padding: 24 }}>Ошибка: {err}</div>;
  if (notFound || !event) return <div style={{ padding: 24 }}>Мероприятие не найдено</div>;

  const starts = event.starts_at ? new Date(event.starts_at) : null;
  const ends = event.ends_at ? new Date(event.ends_at) : null;

  const judges = (event.judges || [])
  .map((j: any) => {
    if (!j) return null;
    if (typeof j === "object" && j.id != null && typeof j.name === "string") {
      return {
        id: String(j.id),
        name: j.name,
        rank: j.rank ?? null,
        email: j.email ?? null,
        photo: j.photo ?? null,
      };
    }
    const jid = String(j);
    const fromIndex = judgesIndex.get(jid);
    return fromIndex
      ? {
          id: fromIndex.id,
          name: fromIndex.name,
          rank: fromIndex.rank ?? null,
          email: fromIndex.email ?? null,
          photo: fromIndex.photo ?? null,
        }
      : { id: jid, name: `Судья #${jid}`, rank: null, email: null, photo: null };
  })
  .filter(Boolean) as Array<{ id: string; name: string; rank?: string | null; email?: string | null; photo?: string | null }>;


  return (
  <div className="events-page">
    <div >
      <div>
        <Breadcrumb
          title={title || "Мероприятие"}
          items={[
            { label: "Главная", to: "/" },
            { label: "Мероприятия", to: "/events" },
            { label: title || "Мероприятие" },
          ]}
        />
      </div>
    </div>

    <main className="events-main">
      <div className="events-container">
        <section className="events-section events-section--card" data-visible="1">

          <h1 className="events-section-title mt-0">Информация о мероприятии</h1>

          {desc && <p className="events-text">{desc}</p>}

          <div className="event-meta">
            <div className="event-meta-item">
              <strong>Тип:</strong> {eventTypeLabel(event.event_type as string)}
            </div>

            <div className="event-meta-item">
              <strong>Локация:</strong> {event.location || "—"}
            </div>

            <div className="event-meta-item">
              <strong>Начало:</strong>{" "}
              {starts && !Number.isNaN(starts.getTime()) ? dateTime.format(starts) : "—"}
            </div>

            <div className="event-meta-item">
              <strong>Конец:</strong>{" "}
              {ends && !Number.isNaN(ends.getTime()) ? dateTime.format(ends) : "—"}
            </div>
          </div>
        </section>

        <section className="events-section events-section--panel" data-visible="1">
          <h2 className="events-section-title mt-0">Судьи</h2>

          {judges.length > 0 ? (
            <div className="events-leadership-grid">
              {judges.map((j) => (
                <Link
                  key={j.id}
                  to={`/judges/${j.id}`}
                  className="events-leader-card events-leader-card--link"
                >
                  <div className="events-leader-avatar">
                    {j.photo ? <img src={j.photo} alt={j.name} /> : <span>{j.name?.[0] ?? "J"}</span>}
                  </div>

                  <div className="events-leader-name">{j.name}</div>

                  {j.rank && <div className="events-leader-position">{j.rank}</div>}
                  {j.email && <div className="events-leader-contact">{j.email}</div>}

                  <div className="judge-card-cta-like">Открыть профиль →</div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="events-text">Судьи пока не указаны.</div>
          )}
        </section>

        {event.registration_link && (event.registration_link as string).trim() !== "" && (
          <div className="event-register">
            <a
              className="events-pill events-pill--primary"
              href={event.registration_link as string}
              target="_blank"
              rel="noreferrer"
            >
              Перейти к регистрации →
            </a>
          </div>
        )}
      </div>
    </main>
  </div>
);
}
