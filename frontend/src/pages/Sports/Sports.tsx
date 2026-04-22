import { Link } from "react-router-dom";
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

type Race = {
  id: string;
  tabLabel: string;
  title: string;
  date: string;
  location: string;
  club: string;
  organizers: string;
  judge: string;
  distances: string;
  rows: RaceRow[];
};

type Season = {
  id: string;
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

const telgurRows: RaceRow[] = [
  { no: 1, discipline: "1SJWJ1", dog: "Альфа", chip: "643115187753596", pedigree: "6379403", owner: "Гмызин А.Н.", athlete: "Гмызина Алиса А.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 2, discipline: "1SJWJ1", dog: "Хася", chip: "643099011338821", pedigree: "6810379R", owner: "Егоров Г.И.", athlete: "Макаровская Анна В.", cact: "CACT", qualified: true },
  { no: 3, discipline: "1SJ(M+W)1+2", dog: "Жан-Поль Джидай Севера", chip: "643093333008290", pedigree: "5207409", owner: "Шабанов Р.", athlete: "Корепанов Алексей В.", qualified: true },
  { no: 4, discipline: "1SJ(M+W)1+2", dog: "Бьянка Снежная Королева", chip: "643099001921959", pedigree: "5512783", owner: "Атаманова О.М.", athlete: "Атаманов Вадим И.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 5, discipline: "SD1", dog: "Goldwind Moonlignt", chip: "900217000565313", pedigree: "6147602", owner: "Мухаметзянова Е.Ю.", athlete: "Мухаметзянова Елена Ю.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 6, discipline: "SD1", dog: "Goldwind Linkor", chip: "643099001792447", pedigree: "6476487", owner: "Мухаметзянова Е.Ю.", athlete: "Мухаметзянова Елена Ю.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 7, discipline: "SD1", dog: "Эвридика", chip: "643093400084365", pedigree: "5208912", owner: "Перевозчиков А.А.", athlete: "Мухаметзянов Михаил Г.", cact: "CACT", qualified: true },
  { no: 8, discipline: "SD1", dog: "Эльба", chip: "992007001002120", pedigree: "5208911", owner: "Перевозчиков А.А.", athlete: "Мухаметзянов Михаил Г.", cact: "CACT", qualified: true },
  { no: 9, discipline: "SD1", dog: "Непогода из Клана Симурана", chip: "643094100511707", pedigree: "5511672", owner: "Дубовцева Е.В.", athlete: "Дубовцева Елена В.", qualified: true },
  { no: 10, discipline: "SD1", dog: "Убывающая Луна из Клана Симурана", chip: "643094100521524", pedigree: "5992742", owner: "Дубовцева Е.В.", athlete: "Дубовцева Елена В.", qualified: true },
  { no: 11, discipline: "SC1+2", dog: "Ник", chip: "900241000001736", pedigree: "7132423R", owner: "Атаманова О.М.", athlete: "Атаманова Ольга М.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 12, discipline: "SC1+2", dog: "Сальма", chip: "643099001921318", pedigree: "6886409", owner: "Атаманова О.М.", athlete: "Атаманова Ольга М.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 13, discipline: "SC1+2", dog: "Сириус ТЭКО", chip: "643099001921444", pedigree: "6886408", owner: "Атаманова О.М.", athlete: "Атаманова Ольга М.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 14, discipline: "SC1+2", dog: "Наоми Снежная Королева", chip: "643099001921760", pedigree: "6569595", owner: "Атаманова О.М.", athlete: "Атаманова Ольга М.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 15, discipline: "SC1+2", dog: "CENT", chip: "900215000527321", pedigree: "5512954", owner: "Бахтина Е.В.", athlete: "Бахтина Елена В.", qualified: true },
  { no: 16, discipline: "SC1+2", dog: "Того", chip: "900215000527334", pedigree: "6708791R", owner: "Бахтина Е.В.", athlete: "Бахтина Елена В.", qualified: true },
  { no: 17, discipline: "SC1+2", dog: "Атика Искрящийся Угалёк", chip: "643093300209830", pedigree: "6701612", owner: "Сергеева П.А.", athlete: "Бахтина Елена В.", qualified: true },
  { no: 18, discipline: "SC1+2", dog: "Осколок Дождя из Клана Симурана", chip: "643093400084368", pedigree: "5627547", owner: "Перевозчиков А.А.", athlete: "Гарипова Нина В.", cact: "CACT", qualified: true },
  { no: 19, discipline: "SB1", dog: "Еловая Волчица из Клана Симурана", chip: "900233000310795", pedigree: "6476417", owner: "Перевозчиков А.А.", athlete: "Гарипова Нина В.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 20, discipline: "SB1", dog: "Грозовой Перевал из Клана Симурана", chip: "900233000310802", pedigree: "6378407", owner: "Перевозчиков А.А.", athlete: "Гарипова Нина В.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 21, discipline: "SB1", dog: "Гостья Ночи из Клана Симурана", chip: "900233000310780", pedigree: "6378408", owner: "Перевозчиков А.А.", athlete: "Гарипова Нина В.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 22, discipline: "SB1", dog: "Главный Герой из Клана Симурана", chip: "900233000310815", pedigree: "6378406", owner: "Перевозчиков А.А.", athlete: "Гарипова Нина В.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 23, discipline: "SB1", dog: "Елементал Файр", chip: "900233000310820", pedigree: "5398777", owner: "Перевозчиков А.А.", athlete: "Гарипова Нина В.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 24, discipline: "SB1", dog: "Шевроле из Клана Симурана", chip: "900233000310813", pedigree: "6210385", owner: "Перевозчиков А.А.", athlete: "Гарипова Нина В.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 25, discipline: "SB1", dog: "ULUN LUNA", chip: "900215010157695", pedigree: "7049190", owner: "Бучилко К.А.", athlete: "Бучилко Ксения А.", cact: "CACT", qualified: true },
  { no: 26, discipline: "SB1", dog: "Сноу Шаде Эланор", chip: "643094100688159", pedigree: "5391600", owner: "Бучилко К.А.", athlete: "Бучилко Ксения А.", cact: "CACT", qualified: true },
  { no: 27, discipline: "SB1", dog: "SNOW SHADE APPA", chip: "900233000270105", pedigree: "5201943", owner: "Бучилко К.А.", athlete: "Бучилко Ксения А.", cact: "CACT", qualified: true },
  { no: 28, discipline: "SB1", dog: "SNOW SHADE VAEMON D", chip: "643099002011039", pedigree: "7043804", owner: "Бучилко К.А.", athlete: "Бучилко Ксения А.", cact: "CACT", qualified: true },
  { no: 29, discipline: "SB1", dog: "SNOW SHADE SUVI", chip: "643099002022465", pedigree: "6475661", owner: "Бучилко К.А.", athlete: "Бучилко Ксения А.", cact: "CACT", qualified: true },
  { no: 30, discipline: "SB1", dog: "SNOW SHADE LARA KROFT", chip: "643094100689614", pedigree: "5994275", owner: "Бучилко К.А.", athlete: "Бучилко Ксения А.", cact: "CACT", qualified: true },
  { no: 31, discipline: "SB1", dog: "Аргентум Стайл Жаным Айно", chip: "900215007878968", pedigree: "6810901", owner: "Сергеева П.А.", athlete: "Корепанова Анна В.", qualified: true },
  { no: 32, discipline: "SB1", dog: "Аргентум Стайл Жомарт Кион", chip: "900263003701895", pedigree: "6810893", owner: "Корепанова А.В.", athlete: "Корепанова Анна В.", qualified: true },
  { no: 33, discipline: "SB1", dog: "Голдвинд Фловер Оф Лов", chip: "643078198003122", pedigree: "6703947", owner: "Меньщикова К.В.", athlete: "Корепанова Анна В.", qualified: true },
  { no: 34, discipline: "SB1", dog: "Carmen KINGDOM NAVJORD", chip: "900001898018581", pedigree: "6214266", owner: "Шефер Ю.В.", athlete: "Корепанова Анна В.", qualified: true },
  { no: 35, discipline: "SB1", dog: "Жоур Де Нейч Орсон", chip: "900215007878967", pedigree: "5203258", owner: "Узунян О.В.", athlete: "Корепанова Анна В.", qualified: true },
];

const silaRows: RaceRow[] = [
  { no: 1, discipline: "SC1", dog: "Ветер Гор Деман", chip: "643078250031963", pedigree: "6479225", owner: "Милых Г.В.", athlete: "Баландина А.Е.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 2, discipline: "SC1", dog: "Ветер Гор Дори", chip: "900233001242354", pedigree: "6479228", owner: "Милых Г.В.", athlete: "Баландина А.Е.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 3, discipline: "SC1", dog: "Ветер Гор Емми", chip: "900241000016994", pedigree: "6812543", owner: "Милых Г.В.", athlete: "Баландина А.Е.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 4, discipline: "SC1", dog: "Ветер Гор Елка", chip: "900241000016991", pedigree: "6812545", owner: "Милых Г.В.", athlete: "Баландина А.Е.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 5, discipline: "SC1", dog: "Ветер Гор Жак", chip: "900263004694875", pedigree: "7253214", owner: "Ермошина Е.Д.", athlete: "Ермошина Е.Д.", cact: "CACT", qualified: true },
  { no: 6, discipline: "SC1", dog: "Ветер Гор Жорик", chip: "900263004694870", pedigree: "7253215", owner: "Ермошина Е.Д.", athlete: "Ермошина Е.Д.", cact: "CACT", qualified: true },
  { no: 7, discipline: "SC1", dog: "Ветер Гор Жасмин", chip: "900263004694861", pedigree: "7253217", owner: "Ермошина Е.Д.", athlete: "Ермошина Е.Д.", cact: "CACT", qualified: true },
  { no: 8, discipline: "SC1", dog: "Ветер Гор Жаклин", chip: "900263004694868", pedigree: "7253216", owner: "Ермошина Е.Д.", athlete: "Ермошина Е.Д.", cact: "CACT", qualified: true },
  { no: 9, discipline: "SC1", dog: "OBIPPO ESCAPE", chip: "643094100507550", pedigree: "4839293", owner: "Костаустов К.С.", athlete: "Костаустов К.С.", qualified: true },
  { no: 10, discipline: "SC1", dog: "ALWAYS WINS ATLANTIC STORM", chip: "643093300093191", pedigree: "5062041", owner: "Гончаренко П.Е.", athlete: "Костаустов К.С.", qualified: true },
  { no: 11, discipline: "SC1", dog: "DEBY DRIVE", chip: "900113001216505", pedigree: "обмен", owner: "Костаустов К.С.", athlete: "Костаустов К.С.", qualified: true },
  { no: 12, discipline: "SC1", dog: "DOCTOR DIZEL", chip: "643099000051135", pedigree: "обмен", owner: "Костаустов К.С.", athlete: "Костаустов К.С.", qualified: true },
  { no: 13, discipline: "1SJM1", dog: "MOGUCHIY VOIN IZ SNEZHNOI SIBIRI", chip: "643148000393201", pedigree: "4837294", owner: "Рудик А.И.", athlete: "Сердюк А.В.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 14, discipline: "1SJM1", dog: "ЧИО РИО-ДЕЖАНЕЙРО", chip: "643099001758095", pedigree: "6815982R", owner: "Суханова Т.", athlete: "Панченко И.", cact: "CACT", qualified: true },
  { no: 15, discipline: "1SJM1", dog: "ДЕРЖЕНА", chip: "643100014489750", pedigree: "6143375", owner: "Алехина Е.С.", athlete: "Буслаев И.В.", qualified: true },
  { no: 16, discipline: "1SJMJ1", dog: "Ветер Гор Еста", chip: "900185000136532", pedigree: "6812544", owner: "Кощеева Г.М.", athlete: "Кощеев Г.С.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 17, discipline: "1SJMJ1", dog: "Ветер Гор Гром", chip: "640999001538477", pedigree: "6374660", owner: "Милых Г.В.", athlete: "Чернов Д.Н.", cact: "CACT", qualified: true },
  { no: 18, discipline: "1SJMJ1", dog: "Ветер Гор Веста", chip: "643100000422741", pedigree: "5513987", owner: "Милых Г.В.", athlete: "Павлов А.", qualified: false },
  { no: 19, discipline: "2SJW1", dog: "ТЕЙП ДОГС ЮРАША", chip: "643099011115609", pedigree: "6568616", owner: "Дмитриева А.", athlete: "Суворкина Е.В.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 20, discipline: "2SJW1", dog: "ТЕЙП ДОГС ЮЖАНКА", chip: "900021000826502", pedigree: "6568617", owner: "Суворкина Е.В.", athlete: "Суворкина Е.В.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 21, discipline: "2SJW1", dog: "KARA BLACK ROSE", chip: "643099001756228", pedigree: "6217986", owner: "Микитина Е.В.", athlete: "Микитина Е.В.", cact: "CACT", qualified: true },
  { no: 22, discipline: "2SJW1", dog: "KLEYA VE STAR OF SAYBERIA", chip: "900241000049698", pedigree: "обмен", owner: "Озерова А.А.", athlete: "Микитина Е.В.", cact: "CACT", qualified: true },
  { no: 23, discipline: "2SJW1", dog: "KITTY THE WHITE SPOT", chip: "900217000119235", pedigree: "6217987", owner: "Радыгина Т.К.", athlete: "Радыгина Т.К.", qualified: true },
  { no: 24, discipline: "2SJW1", dog: "ТРЕЙСИ ЛИНД", chip: "643093300077618", pedigree: "5062770", owner: "Радыгина Т.К.", athlete: "Радыгина Т.К.", qualified: true },
  { no: 25, discipline: "SD1", dog: "Ветер Гор Альф", chip: "643094100597073", pedigree: "4623315", owner: "Милых Г.В.", athlete: "Беседина А.Р.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 26, discipline: "SD1", dog: "УРАЛСТАН КЕННЕЛ КЕНАЙ", chip: "900115002030625", pedigree: "6807345", owner: "Милых Г.В.", athlete: "Беседина А.Р.", cact: "ЧРКФ RegCACT", qualified: true },
  { no: 27, discipline: "SD1", dog: "Ветер Гор Букер", chip: "643094100597074", pedigree: "4830386", owner: "Милых Г.В.", athlete: "Нагирняк И.М.", cact: "CACT", qualified: true },
  { no: 28, discipline: "SD1", dog: "Ветер Гор Бухтай", chip: "643094100558076", pedigree: "обмен", owner: "Милых Г.В.", athlete: "Нагирняк И.М.", cact: "CACT", qualified: true },
  { no: 29, discipline: "SD1", dog: "ЗЛАТОГОРЬЕ ЭЙВЫ ИГРА СВЕТА", chip: "900217000183586", pedigree: "6214600", owner: "Гаевская А.В.", athlete: "Гаевская А.В.", qualified: false },
  { no: 30, discipline: "SD1", dog: "ЕГО ПРЕВОСХОДИТЕЛЬСТВО АЙС ШТОРМ", chip: "643099200026803", pedigree: "5629262", owner: "Гаевская А.В.", athlete: "Гаевская А.В.", qualified: false },
];

const seasons: Season[] = [
  {
    id: "zima2026",
    badge: "Зима 2026",
    title: "Сезон зима 2026",
    meta: ["📅 07–21 февраля 2026", "🐕 65 участников", "📍 Новосибирск · Ижевск"],
    stats: {
      races: "2",
      participants: "65",
      judges: "1",
      disciplines: "9",
      purebred: "100%",
    },
    races: [
      {
        id: "race-telgur",
        tabLabel: "🏁 «Телгур» — 7 февр.",
        title: "«Телгур»",
        date: "07 февраля 2026",
        location: "КАО «Нечкино», Удмуртская Республика, Сарапульский район",
        club: "Ижевская ГОО КЦ «Оружейный Град»",
        organizers: "Корепанова Анна, Сергеева Полина",
        judge: "Серов И.В.",
        distances: "4,2 км · 8,3 км",
        rows: telgurRows,
      },
      {
        id: "race-sila",
        tabLabel: "🏁 «Сила Сибири» — 21 февр.",
        title: "«Сила Сибири»",
        date: "21 февраля 2026",
        location: "п. Степной, Новосибирская область",
        club: "НГОО КЖ «Абсолют» · ЦЕС «Сила сибирских хаски»",
        organizers: "Милых Галина Валерьевна",
        judge: "Серов И.В.",
        distances: "4,2 км · 7,1 км · 30 км",
        rows: silaRows,
      },
    ],
  },
];

const calendarItems = [
  {
    day: "07",
    month: "Февр",
    title: "«Телгур» — Квалификационная гонка",
    text: "КАО «Нечкино», Удмуртская Республика · 4,2 км · 8,3 км",
    status: "Завершена",
    statusClass: "status-closed",
  },
  {
    day: "21",
    month: "Февр",
    title: "«Сила Сибири» — Квалификационная гонка",
    text: "п. Степной, Новосибирская обл. · 4,2 км · 7,1 км · 30 км",
    status: "Завершена",
    statusClass: "status-closed",
  },
  {
    day: "?",
    month: "Весна",
    title: "Квалификационная гонка — весна 2026",
    text: "Место и дата уточняются",
    status: "Планируется",
    statusClass: "status-plan",
    customDateClass: "sports-cal-date--planned",
  },
];

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

export default function Sports() {
  const pageRef = useRef<HTMLDivElement | null>(null);
  const [activeSeasonId, setActiveSeasonId] = useState(seasons[0]?.id ?? "");
  const [activeRaceId, setActiveRaceId] = useState(seasons[0]?.races[0]?.id ?? "");

  const activeSeason = useMemo(
    () => seasons.find((season) => season.id === activeSeasonId) ?? seasons[0],
    [activeSeasonId]
  );

  const activeRace = useMemo(
    () =>
      activeSeason?.races.find((race) => race.id === activeRaceId) ??
      activeSeason?.races[0],
    [activeSeason, activeRaceId]
  );

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

  const handleSeasonClick = (seasonId: string) => {
    if (seasonId === activeSeasonId) return;
    const nextSeason = seasons.find((season) => season.id === seasonId);
    setActiveSeasonId(seasonId);
    setActiveRaceId(nextSeason?.races[0]?.id ?? "");
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

                <div className="sports-season-grid">
                  {seasons.map((season) => {
                    const isActive = season.id === activeSeasonId;

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
                          className={`sports-race-tab ${race.id === activeRaceId ? "active" : ""}`}
                          onClick={() => setActiveRaceId(race.id)}
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
                              {activeRace.rows.map((row) => (
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
                              ))}
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
                  {calendarItems.map((item) => (
                    <li key={`${item.day}-${item.title}`} className="sports-calendar-item">
                      <div
                        className={`sports-cal-date ${item.customDateClass ?? ""}`.trim()}
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
                  ))}
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