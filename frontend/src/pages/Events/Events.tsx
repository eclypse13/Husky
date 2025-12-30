import {useEffect, useMemo, useRef, useState} from "react";
import { Link } from "react-router-dom";
import { getDict, pickValue } from "@/lib/dict";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./Events.css";

const eventDateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
});

function formatEventDate(dateString?: string | null): string | null {
  if (!dateString) return null;
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return null;
  return eventDateFormatter.format(date);
}

export default function Events() {
  const pageRef = useRef<HTMLDivElement | null>(null);
  const [eventsTitle, setEventsTitle] = useState<string | null>(null);
  const [eventsIntro, setEventsIntro] = useState<string | null>(null);
  type EventItem = {
    id: string;
    title: string;
    desc?: string | null;
    dateLabel?: string | null;
    location?: string | null;
    startsAt?: string | null;
    eventType?: string | null;
  };
  const [events, setEvents] = useState<EventItem[]>([]);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1); // 1-е число текущего месяца
  });
  const [selectedDayKey, setSelectedDayKey] = useState<string | null>(null);


  type JudgeItem = {
    id: string;
    name: string;
    rank?: string | null;
    email?: string | null;
    photo?: string | null;
    judgeId?: string | null;
  };
  // ОТЧЕТ
  type EventReportItem = {
    id: string;
    event: string | number;
    title?: string | null;            // готовое название для UI
    event_title_key?: string | null;  // ключ из API (на всякий)
    created_at?: string | null;
    photosCount?: number;
    videosCount?: number;
  };

  const [reports, setReports] = useState<EventReportItem[]>([]);

  const [judges, setJudges] = useState<JudgeItem[]>([]);
  const getJudgeInitial = (name?: string | null) => {
    if (!name) return "J";
    const letter = name.trim().charAt(0);
    return letter || "J";
  };
  // Плавное появление секций/карточек
  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    const targets = root.querySelectorAll<HTMLElement>(
      ".events-section, .sidebar-card"
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
  }, []);

  // Load Events page title, intro, and list of events from API/dict
  useEffect(() => {
    let ignore = false;

    const loadPage = async () => {
      try {
        const dict = await getDict();
        if (ignore) return;

        const t = pickValue(dict, "EVENTS_TITLE", "ru");
        const i = pickValue(dict, "EVENTS_INTRO", "ru");
        if (t) setEventsTitle(t);
        if (i) setEventsIntro(i);

        let eventsPayload: unknown = [];
        try {
          const res = await fetch("/api/events/");
          if (res.ok) {
            eventsPayload = await res.json();
          }
        } catch {
          eventsPayload = [];
        }
        if (ignore) return;

        const fromApi = Array.isArray((eventsPayload as any)?.results)
          ? (eventsPayload as any).results
          : Array.isArray(eventsPayload)
          ? eventsPayload
          : [];

        const normalized: EventItem[] = fromApi
          .map((event: any, index: number): EventItem | null => {
            if (!event) return null;
            const titleKey = typeof event.title_key === "string" ? event.title_key : "";
            const descKey = typeof event.description_key === "string" ? event.description_key : "";
            const titleFromDict = titleKey ? pickValue(dict, titleKey, "ru") : null;
            const title = titleFromDict || titleKey || `event-${index}`;
            if (!title) return null;
            const desc = descKey ? pickValue(dict, descKey, "ru") || descKey : null;
            const startsAt = typeof event.starts_at === "string" ? event.starts_at : null;
            const dateLabel = formatEventDate(startsAt);
            const location = typeof event.location === "string" ? event.location : null;
            const eventType = typeof event.event_type === "string" ? event.event_type : null;
            return {
              id: String(event.id ?? titleKey ?? index),
              title,
              desc,
              location,
              startsAt,
              dateLabel,
              eventType,
            };
          })
          .filter((item: EventItem | null): item is EventItem => Boolean(item));

        normalized.sort((a, b) => {
          const aTime = a.startsAt ? new Date(a.startsAt).getTime() : 0;
          const bTime = b.startsAt ? new Date(b.startsAt).getTime() : 0;
          return aTime - bTime;
        });

        setEvents(normalized);
      } catch {
        // leave fallbacks when API fails
      }
    };

    loadPage();
    return () => {
      ignore = true;
    };
  }, []);

  // Load judges from API
  useEffect(() => {
    let ignore = false;

    const loadJudges = async () => {
      try {
        const res = await fetch("/api/judges/");
        if (!res.ok) return;
        const payload = await res.json();
        if (ignore) return;

        const fromApi = Array.isArray((payload as any)?.results)
          ? (payload as any).results
          : Array.isArray(payload)
          ? payload
          : [];

        const normalized: JudgeItem[] = fromApi
          .map((judge: any, index: number): JudgeItem | null => {
            if (!judge) return null;
            const name = typeof judge.name === "string" ? judge.name : null;
            if (!name) return null;
            const rank = typeof judge.rank === "string" ? judge.rank : null;
            const email = typeof judge.email === "string" ? judge.email : null;
            const photo = typeof judge.photo === "string" ? judge.photo : null;
            const judgeId = judge.judge_id != null ? String(judge.judge_id) : null;
            return {
              id: String(judge.id ?? index),
              name,
              rank,
              email,
              photo,
              judgeId,
            };
          })
          .filter((item: JudgeItem | null): item is JudgeItem => Boolean(item));

        setJudges(normalized);
      } catch {
        // ignore judges errors silently
      }
    };

    loadJudges();
    return () => {
      ignore = true;
    };
  }, []);

  // загрузка ОТЧЕТА из API
  useEffect(() => {
    let ignore = false;

    const loadReports = async () => {
      try {
        const res = await fetch("/api/event-reports/");
        if (!res.ok) return;
        const payload = await res.json();
        if (ignore) return;

        const dict = await getDict();
        if (ignore) return;

        const fromApi = Array.isArray((payload as any)?.results)
          ? (payload as any).results
          : Array.isArray(payload)
          ? payload
          : [];

        const normalized: EventReportItem[] = fromApi
          .map((r: any, idx: number): EventReportItem => {
            const titleKey =
              typeof r?.event_title_key === "string" ? r.event_title_key : "";

            const titleFromDict = titleKey ? pickValue(dict, titleKey, "ru") : null;
            const title = titleFromDict || titleKey || null;
            const photos = Array.isArray(r?.photos) ? r.photos : [];
            const videos = Array.isArray(r?.videos) ? r.videos : [];

            return {
              id: String(r?.id ?? idx),
              event: r?.event,
              event_title_key: titleKey || null,
              title,
              created_at: typeof r?.created_at === "string" ? r.created_at : null,
              photosCount: photos.length,
              videosCount: videos.length,
            };
          })
          .filter((x: EventReportItem) => Boolean(x.id));

        normalized.sort((a, b) => {
          const aTimeRaw = a.created_at ? new Date(a.created_at).getTime() : 0;
          const bTimeRaw = b.created_at ? new Date(b.created_at).getTime() : 0;

          const aTime = Number.isNaN(aTimeRaw) ? 0 : aTimeRaw;
          const bTime = Number.isNaN(bTimeRaw) ? 0 : bTimeRaw;

          return bTime - aTime; // САМЫЕ СВЕЖИЕ СНАЧАЛА
        });

        setReports(normalized);
      } catch {
        // игнор
      }
    };

    loadReports();
    return () => {
      ignore = true;
    };
  }, []);



  // Inject first 3 events into sidebar stack and remove extra card if present
  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;
    // Replace notes inside the first sidebar stack
    const stack = root.querySelector<HTMLDivElement>(".events-sidebar .sidebar-card .events-side-stack");
    if (stack && events.length > 0) {
      const pill = stack.querySelector<HTMLElement>(".events-pill");
      stack.innerHTML = "";
      const colors = ["events-side-note--blue", "events-side-note--green", "events-side-note--orange"];
      events.slice(0, 3).forEach((e, i) => {
        const div = document.createElement("div");
        div.className = `events-side-note ${colors[i % colors.length]}`;
        const detail = e.location ?? e.desc ?? "";
        const dateText = e.dateLabel ? `<span>${e.dateLabel}</span> ` : "";
        div.innerHTML = `${dateText}<strong>${e.title}</strong>${detail ? ` — ${detail}` : ""}`;
        stack.appendChild(div);
      });
      if (pill) stack.appendChild(pill);
    }

    // Remove the extra "Ближайшие события" card if it exists
    const aside = root.querySelector<HTMLElement>(".events-sidebar");
    const firstCard = aside?.querySelector<HTMLElement>(".sidebar-card");
    const heading = firstCard?.querySelector<HTMLElement>(".events-sidebar-title");
    if (heading && /Ближайшие события/i.test(heading.textContent || "")) {
      firstCard?.remove();
    }
  }, [events]);

    const monthNames = [
    "Январь","Февраль","Март","Апрель","Май","Июнь",
    "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь",
  ];
  const weekNames = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"];

  const toDateKey = (d: Date) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  };

  const eventDays = useMemo(() => {
    const s = new Set<string>();
    events.forEach((e) => {
      if (!e.startsAt) return;
      const d = new Date(e.startsAt);
      if (Number.isNaN(d.getTime())) return;
      s.add(toDateKey(d));
    });
    return s;
  }, [events]);

  const calendarCells = useMemo(() => {
    const y = calendarMonth.getFullYear();
    const m = calendarMonth.getMonth();

    const first = new Date(y, m, 1);
    const last = new Date(y, m + 1, 0);

    // хотим Пн..Вс, поэтому сдвиг: (Вс=0) -> 6, (Пн=1) -> 0 ...
    const startOffset = (first.getDay() + 6) % 7;

    const cells: Array<{ date: Date; inMonth: boolean; key: string }> = [];
    const start = new Date(y, m, 1 - startOffset);

    for (let i = 0; i < 42; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);

      cells.push({
        date: d,
        inMonth: d.getMonth() === m,
        key: toDateKey(d),
      });
    }

    return { first, last, cells };
  }, [calendarMonth]);

  const fullDateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
      }),
    []
  );

  const timeFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat("ru-RU", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    []
  );

  const selectedDayDate = useMemo(() => {
    if (!selectedDayKey) return null;
    const [y, m, d] = selectedDayKey.split("-").map(Number);
    if (!y || !m || !d) return null;
    return new Date(y, m - 1, d);
  }, [selectedDayKey]);

  const selectedDayEvents = useMemo(() => {
    if (!selectedDayKey) return [];
    return events
      .filter((e) => e.startsAt && toDateKey(new Date(e.startsAt)) === selectedDayKey)
      .sort((a, b) => {
        const at = a.startsAt ? new Date(a.startsAt).getTime() : 0;
        const bt = b.startsAt ? new Date(b.startsAt).getTime() : 0;
        return at - bt;
      });
  }, [events, selectedDayKey]);


  useEffect(() => {
    if (!calendarOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setCalendarOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [calendarOpen]);


  return (
    <div className="events-page" ref={pageRef}>
      <Breadcrumb
        title="Мероприятия"
        items={[{ label: "Главная", to: "/" }, { label: "Мероприятия" }]}
        className="events-breadcrumb"
      />

      <main className="events-main">
        <div className="events-container">
          <div className="events-grid">
            <div className="events-col">
              {/* Календарь */}
              <section className="events-section events-section--card">
                <h2 className="events-section-title mt-0">{eventsTitle ?? 'Календарь выставок и мероприятий'}</h2>
                <p className="events-text">
                  {eventsIntro ?? 'Следующие официальные мероприятия, организованные НКП Сибирский Хаски:'}
                </p>
                {events.length > 0 && (
                  <ul className="events-list">
                    {events.map((e) => (
                      <li key={e.id}>
                        {e.dateLabel ? (
                          <>
                            <strong>{e.dateLabel}:</strong>{" "}
                            {e.title}
                          </>
                        ) : (
                          <strong>{e.title}</strong>
                        )}
                        {e.location ? ` — ${e.location}` : e.desc ? ` — ${e.desc}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
                {events.length === 0 && (
                <ul className="events-list">
                  <li><strong>25 июля 2025:</strong> Семинар для судей — Москва</li>
                  <li><strong>15 августа 2025:</strong> Специализированная выставка — Санкт-Петербург</li>
                  <li><strong>7 сентября 2025:</strong> День ездового спорта — Казань</li>
                  <li><strong>22 сентября 2025:</strong> Онлайн-вебинар по грумингу хаски</li>
                </ul>
                )}
              </section>

              {/* Отчёты (градиентный блок) */}
              <section className="events-section events-section--gradient">
                <div className="events-gradient-inner">
                  <h2 className="events-section-title events-section-title--light mt-0">
                    Отчёты о прошедших мероприятиях
                  </h2>
                  <ul className="events-mission-list">
                    {(reports.length > 0 ? reports.slice(0, 3) : []).map((r, i) => (
                      <li key={r.id}>
                        <div className="events-mission-icon">{i === 0 ? "📷" : i === 1 ? "🎓" : "❄️"}</div>
                        <div>
                          {/*<strong>{r.event_title ?? `Отчёт #${r.id}`}:</strong>*/}
                          <strong>{r.title ?? `Отчёт #${r.id}`}:</strong>
                          {" "}
                          <Link to={`/event-report/${r.id}`}>фотоальбом и видеоотчёт</Link>
                        </div>
                      </li>
                    ))}

                    {reports.length === 0 && (
                      <li>
                        <div className="events-mission-icon">📷</div>
                        <div>
                          <strong>Пока нет отчётов</strong>
                        </div>
                      </li>
                    )}


                    {/*<li>*/}
                    {/*  <div className="events-mission-icon">📷</div>*/}
                    {/*  <div>*/}
                    {/*    <strong>Выставка «Сибирская Красота 2025»:</strong>{" "}*/}
                    {/*    <a href="#">фотоальбом и видеоотчёт</a>*/}
                    {/*  </div>*/}
                    {/*</li>*/}
                    {/*<li>*/}
                    {/*  <div className="events-mission-icon">🎓</div>*/}
                    {/*  <div>*/}
                    {/*    <strong>Семинар по экспертной оценке (май 2025):</strong>{" "}*/}
                    {/*    <a href="#">методические материалы</a>*/}
                    {/*  </div>*/}
                    {/*</li>*/}
                    {/*<li>*/}
                    {/*  <div className="events-mission-icon">❄️</div>*/}
                    {/*  <div>*/}
                    {/*    <strong>Чемпионат по драйленду:</strong>{" "}*/}
                    {/*    <a href="#">результаты и интервью с участниками</a>*/}
                    {/*  </div>*/}
                    {/*</li>*/}
                  </ul>
                </div>
              </section>

              {/* Судьи */}
              <section className="events-section events-section--card">
                <h2 className="events-section-title mt-0">Породные эксперты</h2>
                <p className="events-text" style={{ marginBottom: "2rem" }}>
                  Ниже представлен список экспертов, заявленных на Национальных выставках по породе сибирский хаски:
                </p>
                {judges.length > 0 ? (
                  <div className="events-leadership-grid">
                    {judges.map((judge) => (
                      <article className="events-leader-card" key={judge.id}>
                        <div className="events-leader-avatar">
                          {judge.photo ? (
                            <img src={judge.photo} alt={judge.name} />
                          ) : (
                            <span aria-hidden="true">{getJudgeInitial(judge.name)}</span>
                          )}
                        </div>
                        <h3 className="events-leader-name">{judge.name}</h3>
                        {judge.rank && judge.judgeId ? (
                          <Link className="events-leader-position" to={`/judges/${judge.id}`}>
                            {judge.rank}
                          </Link>
                        ) : (
                          judge.rank && <span className="events-leader-position">{judge.rank}</span>
                        )}
                        {judge.email && (
                          <div className="events-leader-contact">
                            <a href={`mailto:${judge.email}`}>{judge.email}</a>
                          </div>
                        )}
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="events-judges-placeholder">
                    Список экспертов скоро появится.
                  </div>
                )}
              </section>

              {/* Семинары */}
              <section className="events-section events-section--panel">
                <h2 className="events-section-title mt-0">Семинары и обучение</h2>
                <p className="events-text">
                  Образовательные мероприятия для судей, хендлеров и заводчиков:
                </p>
                <div className="events-cards-grid">
                  <article className="events-card">
                    <h3 className="events-card-title">🎓 Основы судейства</h3>
                    <ul className="events-benefits">
                      <li><span className="events-check">✓</span> Стандарты породы и типы экстерьера</li>
                      <li><span className="events-check">✓</span> Ошибки в оценке и методики работы</li>
                      <li><span className="events-check">✓</span> Работа на крупных выставках</li>
                    </ul>
                  </article>
                  <article className="events-card">
                    <h3 className="events-card-title">🐾 Подготовка хендлеров</h3>
                    <ul className="events-benefits">
                      <li><span className="events-check">✓</span> Поведение в ринге</li>
                      <li><span className="events-check">✓</span> Демонстрация движений и стойки</li>
                      <li><span className="events-check">✓</span> Работа с молодой собакой</li>
                    </ul>
                  </article>
                </div>
              </section>
            </div>

            {/* Сайдбар (локальный, с теми же карточками) */}
            <aside className="events-sidebar">
              <div className="sidebar-card">
                <h3 className="events-sidebar-title mt-0">Ближайшие события</h3>
                <ul className="events-links">
                  {(events.length > 0 ? events.slice(0, 3) : [
                    { id: 1, title: 'Монопородная выставка НКП СХ' },
                    { id: 2, title: 'Семинар по хендлингу' },
                    { id: 3, title: 'Встреча владельцев хаски' },
                  ]).map((e) => (
                    <li key={e.id}><a href="#">{e.title}</a></li>
                  ))}
                </ul>
              </div>
              <div className="sidebar-card">
                <h3 className="events-sidebar-title mt-0">📅 Ближайшие мероприятия</h3>
                <div className="events-side-stack">
                  <div className="events-side-note events-side-note--blue">
                    <strong>🏆 15 авг:</strong> Спец. выставка — СПб
                  </div>
                  <div className="events-side-note events-side-note--green">
                    <strong>🎓 25 июл:</strong> Семинар судей — Москва
                  </div>
                  <div className="events-side-note events-side-note--orange">
                    <strong>❄️ 7 сен:</strong> Ездовой спорт — Казань
                  </div>
                  <a
                    className="events-pill events-pill--primary"
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      setCalendarOpen(true);
                    }}
                  >
                    Посмотреть календарь
                  </a>


                </div>
              </div>

              <div className="sidebar-card">
                <h3 className="events-sidebar-title mt-0">📸 Фото и видео отчёты</h3>
                <ul className="events-links">
                  {(reports.length > 0 ? reports.slice(0, 3) : []).map((r) => {
                    const icon = (r.videosCount ?? 0) > 0 ? "🎥" : "📷";
                    const label = r.title ?? `Отчёт #${r.id}`;

                    return (
                      <li key={r.id}>
                        <Link to={`/event-report/${r.id}`}>{icon} {label}</Link>
                      </li>
                    );
                  })}

                  {reports.length === 0 && (
                    <li>Пока нет отчётов</li>
                  )}
                  {/*<li><a href="#">📷 «Сибирская Красота 2025»</a></li>*/}
                  {/*<li><a href="#">🎥 Чемпионат по драйленду</a></li>*/}
                  {/*<li><a href="#">📷 Семинар хендлеров</a></li>*/}
                </ul>
                <a className="events-pill events-pill--info" href="/event-reports">Все отчёты</a>
              </div>

              <div className="sidebar-card">
                <h3 className="events-sidebar-title mt-0">👨‍⚖️ Судьи и семинары</h3>
                <ul className="events-links">
                  <li><a href="#">📋 Методички для судей</a></li>
                  <li><a href="#">🎓 Программа обучения</a></li>
                  <li><a href="#">📧 Заявка на семинар</a></li>
                </ul>
                <a className="events-pill events-pill--secondary" href="#">Судейский раздел</a>
              </div>
            </aside>
          </div>
        </div>
      </main>
            {calendarOpen && (
        <div
          className="events-calendar-overlay"
          role="dialog"
          aria-modal="true"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setCalendarOpen(false);
          }}
        >
          <div className="events-calendar-modal">
            <div className="events-calendar-head">
              <div className="events-calendar-title">
                {monthNames[calendarMonth.getMonth()]} {calendarMonth.getFullYear()}
              </div>

              <div className="events-calendar-actions">
                <button
                  type="button"
                  className="events-calendar-nav"
                  onClick={() =>
                    setCalendarMonth(
                      new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() - 1, 1)
                    )
                  }
                >
                  ←
                </button>
                <button
                  type="button"
                  className="events-calendar-nav"
                  onClick={() =>
                    setCalendarMonth(
                      new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 1)
                    )
                  }
                >
                  →
                </button>
                <button
                  type="button"
                  className="events-calendar-close"
                  onClick={() => setCalendarOpen(false)}
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="events-calendar-week">
              {weekNames.map((w) => (
                <div key={w} className="events-calendar-weekday">{w}</div>
              ))}
            </div>

            <div className="events-calendar-grid">
              {calendarCells.cells.map((c) => {
                const hasEvent = eventDays.has(c.key);
                return (
                  <div
                    key={c.key}
                    className={[
                      "events-calendar-cell",
                      c.inMonth ? "in-month" : "out-month",
                      hasEvent ? "has-event" : "",
                      selectedDayKey === c.key ? "is-selected" : "",
                    ].join(" ")}
                    title={hasEvent ? "Есть мероприятие" : ""}
                    role="button"
                    tabIndex={0}
                    onClick={() => setSelectedDayKey(c.key)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") setSelectedDayKey(c.key);
                    }}
                  >
                    <div className="events-calendar-day">{c.date.getDate()}</div>
                    {hasEvent && <div className="events-calendar-dot" />}
                  </div>

                );
              })}
            </div>

            <div className="events-calendar-daypanel">
              <div className="events-calendar-daypanel-title">
                {selectedDayDate
                  ? `Мероприятия — ${fullDateFormatter.format(selectedDayDate)}`
                  : "Выберите дату в календаре"}
              </div>

              {selectedDayKey && (
                selectedDayEvents.length > 0 ? (
                  <ul className="events-calendar-daypanel-list">
                    {selectedDayEvents.map((e) => (
                      <li key={e.id} className="events-calendar-daypanel-item">
                        <div className="events-calendar-daypanel-line">
                          <strong>
                            {e.startsAt ? timeFormatter.format(new Date(e.startsAt)) : ""}
                          </strong>
                          {" "}
                          {e.title}
                        </div>
                        {(e.location || e.desc) && (
                          <div className="events-calendar-daypanel-sub">
                            {e.location ?? e.desc}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="events-calendar-daypanel-empty">
                    В этот день мероприятий нет.
                  </div>
                )
              )}
            </div>


            <div className="events-calendar-hint">
              Подсвечены даты, в которые запланированы мероприятия.
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
