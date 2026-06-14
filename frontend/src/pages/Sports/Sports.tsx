// import { Link } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";

import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import ClubSidebar from "@/components/Sidebar/ClubSidebar";

import "./Sports.css";

type RaceRow = {
  no: number;
  discipline: string;
  dog: string;
  chip: string;
  pedigree: string;
  owner: string;
  athlete: string;
  cact?: string;
  qualified: boolean;
};

type RaceRowJson = {
  number: number;
  discipline: string;
  dog: string;
  chip: string;
  pedigree: string;
  owner: string;
  athlete: string;
  cact?: string;
  qualified: boolean;
};

type RaceResultsResponse = {
  race?: {
    title?: string;
    date?: string;
    location?: string;
    distances?: string;
    judge?: string;
    organizers?: string;
    rows?: RaceRowJson[];
  };
};

type Race = {
  id: string | number;
  tabLabel: string;
  title: string;
  date: string;
  location: string;
  club: string;
  organizers: string;
  judge: string;
  distances: string;
  status: "planned" | "open" | "done";
  status_display: string;
};

type Season = {
  id: string | number;
  badge: string;
  title: string;
  meta: string[];
  races: Race[];
  stats: {
    races: string;
    participants: string;
    judges: string;
    disciplines: string;
    purebred: string;
  };
};


const disciplineGuide = [
  { code: "SC1 / SC1+2", text: "Нарта, 1–2 пары" },
  { code: "SD1", text: "Нарта, 1 собака" },
  { code: "SB1", text: "Буги / байк, 1 собака" },
  { code: "1SJM1", text: "Скиджоринг, мужчины" },
  { code: "1SJMJ1", text: "Скиджоринг, юниоры (муж.)" },
  { code: "1SJWJ1", text: "Скиджоринг, юниоры (жен.)" },
  { code: "2SJW1", text: "Скиджоринг 2 соб., женщины" },
  { code: "1SJ(M+W)1+2", text: "Скиджоринг смешанный" },
];


function formatCalendarDate(dateString: string) {
  if (!dateString) {
    return {
      day: "?",
      month: "—",
    };
  }

  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return {
      day: "?",
      month: "—",
    };
  }

  const months = [
    "Янв",
    "Фев",
    "Мар",
    "Апр",
    "Май",
    "Июн",
    "Июл",
    "Авг",
    "Сен",
    "Окт",
    "Ноя",
    "Дек",
  ];

  return {
    day: String(date.getDate()).padStart(2, "0"),
    month: months[date.getMonth()],
  };
}


export default function Sports() {
  const pageRef = useRef<HTMLDivElement | null>(null);
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [isSeasonsLoading, setIsSeasonsLoading] = useState(true);
  const [activeSeasonId, setActiveSeasonId] = useState("");
  const [activeRaceId, setActiveRaceId] = useState("");
  const [raceResultsMap, setRaceResultsMap] = useState<Record<string, RaceRow[]>>({});
  const [loadingRaceId, setLoadingRaceId] = useState<string | null>(null);
  const activeSeason = useMemo(
    () => seasons.find((season) => String(season.id) === activeSeasonId) ?? null,
    [seasons, activeSeasonId]
  );

  const activeRace = useMemo(
    () =>
      activeSeason?.races.find((race) => String(race.id) === activeRaceId) ??
      activeSeason?.races[0] ??
      null,
    [activeSeason, activeRaceId]
  );

  const activeRaceRows = activeRace ? raceResultsMap[String(activeRace.id)] ?? [] : [];

  const calendarItems = useMemo(() => {
  const items = seasons.flatMap((season) =>
    season.races.map((race) => {
      const { day, month } = formatCalendarDate(race.date);

      let statusClass = "status-closed";

      if (race.status === "planned") {
        statusClass = "status-plan";
      } else if (race.status === "open") {
        statusClass = "status-open";
      } else if (race.status === "done") {
        statusClass = "status-closed";
      }

      return {
        id: String(race.id),
        day,
        month,
        title: `«${race.title}» — Квалификационная гонка`,
        text: `${race.location} · ${race.distances}`,
        status: race.status_display,
        statusClass,
        sortDate: race.date,
      };
    })
  );

  return items.sort((a, b) => a.sortDate.localeCompare(b.sortDate));
}, [seasons]);

  useEffect(() => {
    let ignore = false;

    const loadSeasons = async () => {
      try {
        setIsSeasonsLoading(true);

        const res = await fetch("/api/sports-seasons/");
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const raw = await res.json();

        const data: Season[] = Array.isArray(raw)
          ? raw
          : Array.isArray(raw?.results)
            ? raw.results
            : [];

        if (!ignore) {
          setSeasons(data);

          if (data.length > 0) {
            setActiveSeasonId(String(data[0].id));
            setActiveRaceId(String(data[0].races?.[0]?.id ?? ""));
          }
        }
      } catch (error) {
        console.error("Не удалось загрузить сезоны:", error);
        if (!ignore) {
          setSeasons([]);
        }
      } finally {
        if (!ignore) {
          setIsSeasonsLoading(false);
        }
      }
    };

    loadSeasons();

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!activeRace?.id) return;

    const raceKey = String(activeRace.id);

    if (raceKey in raceResultsMap) return;

    let ignore = false;

    const loadRaceResults = async () => {
      try {
        setLoadingRaceId(raceKey);

        const res = await fetch(`/api/sports-races/${activeRace.id}/results/`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data: RaceResultsResponse = await res.json();

        const mappedRows: RaceRow[] = (data.race?.rows ?? []).map((row) => ({
          no: row.number,
          discipline: row.discipline,
          dog: row.dog,
          chip: row.chip,
          pedigree: row.pedigree,
          owner: row.owner,
          athlete: row.athlete,
          cact: row.cact,
          qualified: row.qualified,
        }));

        if (!ignore) {
          setRaceResultsMap((prev) => ({
            ...prev,
            [raceKey]: mappedRows,
          }));
        }
      } catch (error) {
        console.error(`Не удалось загрузить результаты для ${activeRace.id}:`, error);

        if (!ignore) {
          setRaceResultsMap((prev) => ({
            ...prev,
            [raceKey]: [],
          }));
        }
      } finally {
        if (!ignore) {
          setLoadingRaceId(null);
        }
      }
    };

    loadRaceResults();

    return () => {
      ignore = true;
    };
  }, [activeRace, raceResultsMap]);


  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    const els = root.querySelectorAll<HTMLElement>(
      ".sports-qualifying-section, .sports-calendar-section, .sports-sidebar-card"
    );

    const obs = new IntersectionObserver(
      (entries) =>
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.setAttribute("data-visible", "1");
          }
        }),
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );

    els.forEach((el) => {
      el.setAttribute("data-visible", "0");
      obs.observe(el);
    });

    return () => obs.disconnect();
  }, []);

  const handleSeasonClick = (seasonId: string | number) => {
    if (String(seasonId) === String(activeSeasonId)) return;

    const nextSeason = seasons.find(
      (season) => String(season.id) === String(seasonId)
    );

    setActiveSeasonId(String(seasonId));
    setActiveRaceId(nextSeason?.races[0] ? String(nextSeason.races[0].id) : "");
  };

  return (
    <div ref={pageRef} className="sports-page">
      <div className="sports-animated-bg" aria-hidden="true">
        <div className="sports-floating-shapes">
          <div className="sports-shape sports-shape-1" />
          <div className="sports-shape sports-shape-2" />
          <div className="sports-shape sports-shape-3" />
        </div>
      </div>

      <Breadcrumb
        title="Ездовой спорт"
        items={[{ label: "Главная", to: "/" }, { label: "Ездовой спорт" }]}
      />

      <main className="sports-main-content">
        <div className="sports-content-container">
          <div className="sports-content-grid">
            <div className="sports-main-column">
              <section className="sports-qualifying-section">
                <h2 className="sports-section-title">Квалификационные гонки</h2>
                <p className="sports-section-intro">
                  Официальные квалификационные гонки НКП Сибирский Хаски —
                  только для собак породы сибирский хаски. Результаты
                  подтверждаются судьёй РКФ и засчитываются для получения
                  квалификационных титулов (CACT, RegCACT).
                </p>

                {isSeasonsLoading ? (
                  <p className="sports-section-intro">Загрузка сезонов...</p>
                ) : (
                  <div className="sports-season-grid">
                    {seasons.map((season) => {
                      const isActive = String(season.id) === String(activeSeasonId);

                      return (
                        <button
                          key={season.id}
                          type="button"
                          className={`sports-season-card ${isActive ? "active" : ""}`}
                          onClick={() => handleSeasonClick(season.id)}
                        >
                          <div className="sports-race-count">{season.races.length}</div>
                          <div className="sports-season-badge">{season.badge}</div>
                          <h3>
                            {season.title}
                            <span className="sports-expand-icon">▾</span>
                          </h3>
                          <div className="sports-season-meta">
                            {season.meta.map((item) => (
                              <span key={item}>{item}</span>
                            ))}
                          </div>
                        </button>
                      );
                    })}

                    <div className="sports-season-card sports-season-card--disabled">
                      <div className="sports-season-badge sports-season-badge--muted">
                        Весна 2026
                      </div>
                      <h3>Ожидается</h3>
                      <div className="sports-season-meta">
                        <span>Протоколы будут добавлены</span>
                      </div>
                    </div>
                  </div>
                )}

                {activeSeason && (
                  <div className="sports-protocol-panel visible">
                    <div className="sports-stats-strip">
                      <div className="sports-stat-item">
                        <div className="sports-stat-num">{activeSeason.stats.races}</div>
                        <div className="sports-stat-label">гонки</div>
                      </div>
                      <div className="sports-stat-item">
                        <div className="sports-stat-num">{activeSeason.stats.participants}</div>
                        <div className="sports-stat-label">участников</div>
                      </div>
                      <div className="sports-stat-item">
                        <div className="sports-stat-num">{activeSeason.stats.judges}</div>
                        <div className="sports-stat-label">судья</div>
                      </div>
                      <div className="sports-stat-item">
                        <div className="sports-stat-num">{activeSeason.stats.disciplines}</div>
                        <div className="sports-stat-label">дисциплин</div>
                      </div>
                      <div className="sports-stat-item">
                        <div className="sports-stat-num">{activeSeason.stats.purebred}</div>
                        <div className="sports-stat-label">только хаски</div>
                      </div>
                    </div>

                    <div className="sports-race-tabs">
                      {activeSeason.races.map((race) => (
                        <button
                          key={race.id}
                          type="button"
                          className={`sports-race-tab ${String(race.id) === String(activeRaceId) ? "active" : ""}`}
                            onClick={() => setActiveRaceId(String(race.id))}
                        >
                          {race.tabLabel}
                        </button>
                      ))}
                    </div>

                    {activeRace && (
                      <div className="sports-race-table-wrap visible">
                        <div className="sports-race-header">
                          <div>
                            <h3>{activeRace.title}</h3>
                            <div className="sports-race-details">
                              <span>📅 {activeRace.date}</span>
                              <span>📍 {activeRace.location}</span>
                              <span>🏛 {activeRace.club}</span>
                              <span>👤 Организаторы: {activeRace.organizers}</span>
                              <span>⚖️ Судья: {activeRace.judge}</span>
                            </div>
                          </div>

                          <div className="sports-race-badge">
                            <span className="sports-badge-pill sports-badge-only">
                              Только сибирские хаски!
                            </span>
                            <span className="sports-badge-pill sports-badge-distances">
                              {activeRace.distances}
                            </span>
                          </div>
                        </div>

                        <div className="sports-table-scroll">
                          <table className="sports-protocol-table">
                            <thead>
                              <tr>
                                <th>№</th>
                                <th>Дисциплина</th>
                                <th>Кличка</th>
                                <th>Клеймо / чип</th>
                                <th>Родословная</th>
                                <th>Владелец</th>
                                <th>Спортсмен</th>
                                <th>Квалификация / титулы</th>
                              </tr>
                            </thead>
                            <tbody>
                              {loadingRaceId === String(activeRace?.id) ? (
                                <tr>
                                  <td colSpan={8}>Загрузка результатов...</td>
                                </tr>
                              ) : activeRaceRows.length === 0 ? (
                                <tr>
                                  <td colSpan={8}>Нет данных</td>
                                </tr>
                              ) : (
                                activeRaceRows.map((row) => (
                                  <tr key={`${activeRace.id}-${row.no}-${row.dog}`}>
                                    <td>{row.no}</td>
                                    <td>
                                      <span className="sports-discipline-tag">
                                        {row.discipline}
                                      </span>
                                    </td>
                                    <td>{row.dog}</td>
                                    <td className="sports-chip-code">{row.chip}</td>
                                    <td>{row.pedigree}</td>
                                    <td>{row.owner}</td>
                                    <td>{row.athlete}</td>
                                    <td>
                                      {row.cact && (
                                        <div className="sports-cact-tag">{row.cact}</div>
                                      )}
                                      <span
                                        className={`sports-qual-badge ${
                                          row.qualified ? "sports-qual-yes" : "sports-qual-no"
                                        }`}
                                      >
                                        {row.qualified ? "Квалификация" : "Участие"}
                                      </span>
                                    </td>
                                  </tr>
                                ))
                              )}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </section>

              <section className="sports-calendar-section">
                <h2 className="sports-section-title">Календарь стартов 2026</h2>

                <ul className="sports-calendar-list">
                  {calendarItems.length === 0 ? (
                    <li className="sports-calendar-item">
                      <div className="sports-cal-info">
                        <h4>Пока нет стартов</h4>
                        <p>Календарь будет опубликован позже.</p>
                      </div>
                    </li>
                  ) : (
                    calendarItems.map((item) => (
                      <li key={item.id} className="sports-calendar-item">
                        <div
                          className="sports-cal-date"
                        >
                          <div className="sports-cal-day">{item.day}</div>
                          <div className="sports-cal-month">{item.month}</div>
                        </div>

                        <div className="sports-cal-info">
                          <h4>{item.title}</h4>
                          <p>{item.text}</p>
                          <span className={`sports-cal-status ${item.statusClass}`}>
                            {item.status}
                          </span>
                        </div>
                      </li>
                    ))
                  )}
                </ul>
              </section>
            </div>

            <aside className="sports-sidebar">
              <div className="sports-sidebar-card">
                <div className="sports-sidebar-card-header">
                  <h3>🏅 Рабочая группа</h3>
                </div>
                <div className="sports-sidebar-card-body">
                  <div className="sports-leader-avatar">🛷</div>
                  <div className="sports-leader-name">Елена Шепелева</div>
                  <div className="sports-leader-role">
                    Руководитель направления «Ездовой спорт»
                  </div>

                  <div className="sports-leader-contact">
                    <p>
                      По вопросам проведения гонок, подачи заявок и присвоения
                      квалификаций:
                    </p>
                    <p className="sports-contact-line">
                      <a href="mailto:sport@nkp-husky.ru">sport@nkp-husky.ru</a>
                    </p>
                  </div>
                </div>
              </div>

              <div className="sports-sidebar-card">
                <div className="sports-sidebar-card-header">
                  <h3>ℹ️ Важная информация</h3>
                </div>
                <div className="sports-sidebar-card-body">
                  <ul className="sports-info-list">
                    <li>
                      <span className="sports-info-icon">🐺</span>
                      <span>
                        К участию допускаются исключительно собаки породы{" "}
                        <strong>сибирский хаски</strong>
                      </span>
                    </li>
                    <li>
                      <span className="sports-info-icon">📋</span>
                      <span>
                        Наличие родословной РКФ или документа об обмене обязательно
                      </span>
                    </li>
                    <li>
                      <span className="sports-info-icon">⚖️</span>
                      <span>Судейство по правилам РКФ/ЦЕС</span>
                    </li>
                    <li>
                      <span className="sports-info-icon">🏆</span>
                      <span>
                        CACT и RegCACT засчитываются в титул «Рабочий чемпион»
                      </span>
                    </li>
                  </ul>
                </div>
              </div>

              <div className="sports-sidebar-card">
                <div className="sports-sidebar-card-header">
                  <h3>📖 Расшифровка дисциплин</h3>
                </div>
                <div className="sports-sidebar-card-body">
                  <ul className="sports-discipline-list">
                    {disciplineGuide.map((item) => (
                      <li key={item.code}>
                        <span className="sports-d-code">{item.code}</span>
                        <span>{item.text}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <ClubSidebar stickyTopPx={120} />
            </aside>
          </div>
        </div>
      </main>
    </div>
  );
}