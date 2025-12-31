import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { getDict, pickValue } from "@/lib/dict";
import "../Events/Events.css";

type JudgeItem = {
  id: string;
  name: string;
  rank?: string | null;
  email?: string | null;
  photo?: string | null;
};

type EventPayload = {
  id: number | string;
  title_key?: string | null;
  description_key?: string | null;
  event_type?: string | null;
  location?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  registration_link?: string | null;
  judges?: any[];
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

  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [event, setEvent] = useState<EventPayload | null>(null);
  const [judgesIndex, setJudgesIndex] = useState<Map<string, JudgeItem>>(new Map());

  useEffect(() => {
    let ignore = false;

    const load = async () => {
      if (!id) return;

      setLoading(true);
      setErr(null);
      setNotFound(false);
      setEvent(null);

      try {
        // 1) грузим событие
        const res = await fetch(`/api/events/${id}/`);
        if (!res.ok) {
          setNotFound(true);
          return;
        }
        const data: EventPayload = await res.json();
        if (ignore) return;
        setEvent(data);

        // 2) грузим справочник судей (на случай если в event.judges прилетают только id)
        const jRes = await fetch("/api/judges/");
        if (jRes.ok) {
          const payload = await jRes.json();
          const list = Array.isArray(payload?.results) ? payload.results : Array.isArray(payload) ? payload : [];
          const m = new Map<string, JudgeItem>();
          list.forEach((j: any, idx: number) => {
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
          if (!ignore) setJudgesIndex(m);
        }
      } catch (e: any) {
        if (!ignore) setErr(e?.message || "Ошибка загрузки");
      } finally {
        if (!ignore) setLoading(false);
      }
    };

    load();
    return () => {
      ignore = true;
    };
  }, [id]);

  const view = useMemo(() => {
    if (!event) return null;

    // переводим title/desc через dict
    // (как в Events.tsx при нормализации списка) :contentReference[oaicite:1]{index=1}
    return (async () => {
      const dict = await getDict();

      const titleKey = event.title_key || "";
      const descKey = event.description_key || "";

      const titleFromDict = titleKey ? pickValue(dict, titleKey, "ru") : null;
      const title = titleFromDict || titleKey || `Мероприятие #${event.id}`;

      const descFromDict = descKey ? pickValue(dict, descKey, "ru") : null;
      const desc = descFromDict || descKey || null;

      return { title, desc };
    })();
  }, [event]);

  const [title, setTitle] = useState<string>("");
  const [desc, setDesc] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    (async () => {
      if (!view) return;
      const v = await view;
      if (ignore) return;
      setTitle(v.title);
      setDesc(v.desc);
    })();
    return () => {
      ignore = true;
    };
  }, [view]);

  if (loading) return <div style={{ padding: 24 }}>Загрузка…</div>;
  if (err) return <div style={{ padding: 24 }}>Ошибка: {err}</div>;
  if (notFound || !event) return <div style={{ padding: 24 }}>Мероприятие не найдено</div>;

  const starts = event.starts_at ? new Date(event.starts_at) : null;
  const ends = event.ends_at ? new Date(event.ends_at) : null;

  // нормализуем judges: либо объекты, либо id
  const judges = (event.judges || [])
  .map((j: any) => {
    if (!j) return null;

    // если API уже вернул объект судьи
    if (typeof j === "object" && j.id != null && typeof j.name === "string") {
      return {
        id: String(j.id),
        name: j.name,
        rank: j.rank ?? null,
        email: j.email ?? null,
        photo: j.photo ?? null,
      };
    }

    // если пришёл только id
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
    {/* Breadcrumb можно оставить как есть, но обернём красиво */}
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
        {/* Блок с инфой о мероприятии */}
        <section className="events-section events-section--card" data-visible="1">

          <h1 className="events-section-title mt-0">Информация о мероприятии</h1>

          {desc && <p className="events-text">{desc}</p>}

          <div className="event-meta">
            <div className="event-meta-item">
              <strong>Тип:</strong> {eventTypeLabel(event.event_type)}
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

        {/* Судьи карточками */}
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

        {/* Регистрация отдельным нижним блоком */}
        {event.registration_link && event.registration_link.trim() !== "" && (
          <div className="event-register">
            <a
              className="events-pill events-pill--primary"
              href={event.registration_link}
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
