import { useEffect, useRef, useState } from "react";
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
                    <li>
                      <div className="events-mission-icon">📷</div>
                      <div>
                        <strong>Выставка «Сибирская Красота 2025»:</strong>{" "}
                        <a href="#">фотоальбом и видеоотчёт</a>
                      </div>
                    </li>
                    <li>
                      <div className="events-mission-icon">🎓</div>
                      <div>
                        <strong>Семинар по экспертной оценке (май 2025):</strong>{" "}
                        <a href="#">методические материалы</a>
                      </div>
                    </li>
                    <li>
                      <div className="events-mission-icon">❄️</div>
                      <div>
                        <strong>Чемпионат по драйленду:</strong>{" "}
                        <a href="#">результаты и интервью с участниками</a>
                      </div>
                    </li>
                  </ul>
                </div>
              </section>

              {/* Судьи */}
              <section className="events-section events-section--card">
                <h2 className="events-section-title mt-0">Породные эксперты и судьи</h2>
                <p className="events-text" style={{ marginBottom: "2rem" }}>
                  Ниже представлен список судей, имеющих квалификацию по породе сибирский хаски:
                </p>
                <div className="events-leadership-grid">
                  <div className="events-leader-card">
                    <div className="events-leader-avatar">👩‍⚖️</div>
                    <h3 className="events-leader-name">Анна Фалунина</h3>
                    <p className="events-leader-position">Судья РКФ, FCI</p>
                    <div className="events-leader-contact">anna.falunina@nkp-husky.ru</div>
                  </div>
                  <div className="events-leader-card">
                    <div className="events-leader-avatar">👨‍⚖️</div>
                    <h3 className="events-leader-name">Александр Смирнов</h3>
                    <p className="events-leader-position">Судья по ездовым породам</p>
                    <div className="events-leader-contact">smirnov@nkp-husky.ru</div>
                  </div>
                </div>
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
                  <a className="events-pill events-pill--primary" href="#">Посмотреть календарь</a>
                </div>
              </div>

              <div className="sidebar-card">
                <h3 className="events-sidebar-title mt-0">📸 Фото и видео отчёты</h3>
                <ul className="events-links">
                  <li><a href="#">📷 «Сибирская Красота 2025»</a></li>
                  <li><a href="#">🎥 Чемпионат по драйленду</a></li>
                  <li><a href="#">📷 Семинар хендлеров</a></li>
                </ul>
                <a className="events-pill events-pill--info" href="#">Все отчёты</a>
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
    </div>
  );
}
