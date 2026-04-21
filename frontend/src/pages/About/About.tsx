import { Link } from "react-router-dom";

import { useEffect, useRef, useState } from "react";

import { getDict, pickValue } from "@/lib/dict";

import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";

import ClubSidebar from "@/components/Sidebar/ClubSidebar";

import "./About.css";



export default function About() {

  const pageRef = useRef<HTMLDivElement | null>(null);

  const [historyTitle, setHistoryTitle] = useState<string | null>(null);

  const [historyIntro, setHistoryIntro] = useState<string | null>(null);

  const [missionLead, setMissionLead] = useState<string | null>(null);

  type LeaderCard = {
    id: string;

    icon?: string;

    name: string;

    role: string;

    mail?: string;

    phone?: string | null;

    extra?: string;

    working_group_id: number | null;

  };

  const fallbackHighlight: LeaderCard = {
    id: "fallback-president",
    icon: "👤",
    name: "Татьяна Евграфова",
    role: "Президент НКП Сибирский Хаски",
    mail: "president@nkp-husky.ru",
    phone: "+7 (495) 123-45-67",
    working_group_id: null,
  };
  const fallbackLeaders: LeaderCard[] = [
    { id: "board-comm", icon: "📰", name: "Татьяна Солдатова", role: "СМИ и информационные материалы", extra: "Совместно с Анной Фалуниной", mail: "media@nkp-husky.ru", working_group_id: null},
    { id: "board-it", icon: "💻", name: "Влада Кугуракова", role: "Информационные системы", mail: "it@nkp-husky.ru", working_group_id: null },
    { id: "board-int", icon: "🌐", name: "Марина Акопова", role: "Международное сотрудничество", mail: "international@nkp-husky.ru", working_group_id: null },
    { id: "board-events", icon: "🏆", name: "Татьяна Евграфова", role: "Выставочные мероприятия", extra: "В составе: Алла Проферансова, Татьяна Солдатова", mail: "events@nkp-husky.ru", working_group_id: null },
    { id: "board-standard", icon: "📐", name: "Татьяна Евграфова", role: "Стандарт породы", extra: "В составе: А.А. Фалунина, Т.А. Солдатова, Е.М. Шепелёва, М.С. Акопова, И.Л. Швец", mail: "standard@nkp-husky.ru", working_group_id: null },
    { id: "board-sport", icon: "🏃‍♀️", name: "Елена Шепелёва", role: "Ездовой спорт", mail: "sport@nkp-husky.ru", working_group_id: null },
    { id: "board-rating", icon: "📊", name: "Анна Фалунина", role: "Породный рейтинг", mail: "rating@nkp-husky.ru", working_group_id: null },
  ];
  const [highlightLeader, setHighlightLeader] = useState<LeaderCard>(fallbackHighlight);
  const [boardLeaders, setBoardLeaders] = useState<LeaderCard[]>(fallbackLeaders);

  type ContactCard = {
    id: string;
    icon?: string;
    title: string;
    text?: string;
    type?: "email" | "phone" | "social" | "address";
    href?: string | null;

    links?: { label: string; url: string }[];
  };

  const fallbackContacts: ContactCard[] = [
    {
      id: "contact-phone",
      icon: "📱",
      title: "Телефон",
      text: "+7 925 272-56-57",
      type: "phone",
      href: "tel:+79252725657",
    },
    {
      id: "contact-email",
      icon: "📧",
      title: "Email",
      text: "sesnkp@mail.ru",
      type: "email",
      href: "mailto:sesnkp@mail.ru",
    },
    {
      id: "contact-address",
      icon: "📍",
      title: "Адрес",
      text: "109507, Москва, Самаркандский б-р, 137А-11-258",
      type: "address",
    },
    {
      id: "contact-social",
      icon: "🌐",
      title: "Социальные сети",
      type: "social",
      links: [
        { label: "Telegram", url: "https://t.me/nbc_husky" },
        { label: "VK", url: "https://vk.com/husky_nbc?ysclid=mn7cve1mnp641027105" },
      ],
    },
  ];
  const [contacts, setContacts] = useState<ContactCard[]>(fallbackContacts);


  useEffect(() => {

    const root = pageRef.current;

    if (!root) return;



    const els = root.querySelectorAll<HTMLElement>(

      ".about-history-section, .about-mission-section, .about-leadership-section, .about-membership-section, .about-contact-section, .club-sidebar__card"

    );



    const obs = new IntersectionObserver(

      (entries) =>

        entries.forEach((e) => {

          if (e.isIntersecting) {

            e.target.setAttribute("data-visible", "1");

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



  useEffect(() => {

    const nums = pageRef.current?.querySelectorAll<HTMLElement>(".stat-number");

    if (!nums) return;



    nums.forEach((node) => {

      const raw = node.textContent || "";

      const target = parseInt(raw.replace(/[^\d]/g, ""), 10);

      const hasPlus = /\+$/.test(raw);

      let cur = 0;

      const step = Math.max(1, Math.floor(target / 100));

      const t = setInterval(() => {

        cur += step;

        if (cur >= target) {

          cur = target;

          clearInterval(t);

        }

        node.textContent = cur.toLocaleString("ru-RU") + (hasPlus ? "+" : "");

      }, 16);

    });

  }, []);



  // Load About page content from dictionary API (deduped)

  useEffect(() => {

    let ignore = false;

    getDict()

      .then((dict) => {

        if (ignore) return;

        const ht = pickValue(dict, 'CLUB_HISTORY_TITLE', 'ru');

        const hi = pickValue(dict, 'CLUB_HISTORY', 'ru');

        const mm = pickValue(dict, 'CLUB_MISSION', 'ru');

        if (ht) setHistoryTitle(ht);

        if (hi) setHistoryIntro(hi);

        if (mm) setMissionLead(mm);

      })

      .catch(() => { });

    return () => { ignore = true; };

  }, []);



  // Load presidium members from API

  useEffect(() => {

    let ignore = false;

    const fetchBoard = async () => {

      try {

        const res = await fetch("/api/club/board/");

        if (!res.ok) return;

        const data = await res.json();

        const results: any[] = Array.isArray(data?.results) ? data.results : [];

        if (!results.length) return;

        const president = results.find(

          (member) => typeof member?.position === "string" && member.position.toLowerCase().includes("президент")

        );

        const others = results

          .filter((member) => member !== president)

          .sort((a, b) => (a?.order ?? 0) - (b?.order ?? 0));

        const toCard = (member: any): LeaderCard => ({

          id: String(member?.id ?? member?.email ?? crypto.randomUUID?.() ?? Math.random()),

          icon: member?.name ? member.name.trim().charAt(0).toUpperCase() : "👤",

          name: member?.name ?? "Член президиума",

          role: member?.position ?? "",

          mail: member?.email ?? undefined,

          phone: member?.phone ?? undefined,

          working_group_id: member?.working_group_id ?? null,

        });

        if (president && !ignore) setHighlightLeader(toCard(president));

        if (others.length && !ignore) setBoardLeaders(others.map(toCard));

      } catch {

        // leave fallbacks on failure

      }

    };

    fetchBoard();

    return () => {

      ignore = true;

    };

  }, []);

  useEffect(() => {
    let ignore = false;

    const fetchContacts = async () => {
      try {
        const res = await fetch("/api/contacts/");
        if (!res.ok) return;

        const data = await res.json();
        const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];

        if (!results.length || ignore) return;

        const mapped: ContactCard[] = results.map((item: any, index: number) => ({
          id: String(item?.id ?? `contact-${index}`),
          icon: item?.icon ?? "📌",
          title: item?.title ?? "Контакт",
          text: item?.text ?? "",
          type: item?.type ?? undefined,
          href: item?.href ?? null,

          links: Array.isArray(item?.links)
            ? item.links.map((l: any) => ({
                label: l.label ?? "link",
                url: l.url ?? "#",
              }))
            : undefined,
        }));

        setContacts(mapped);
      } catch {
        // остаются fallback-контакты
      }
    };

    fetchContacts();

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    const normalizedTarget = "президент нкп";
    const presidentCard = boardLeaders.find(
      (member) =>
        typeof member?.role === "string" &&
        member.role.trim().toLowerCase() === normalizedTarget
    );
    if (!presidentCard) return;
    setHighlightLeader(presidentCard);
    setBoardLeaders((members) =>
      members.filter((member) => member.id !== presidentCard.id)
    );
  }, [boardLeaders]);



  return (

    <div ref={pageRef} className="about-page">

      <Breadcrumb

        title="О клубе"

        items={[{ label: "Главная", to: "/" }, { label: "О клубе" }]}

      />



      {/* Контент */}

      <main className="about-main-content">

        <div className="about-content-container">

          <div className="about-content-grid">

            <div className="about-main-column">

              {/* История */}

              <section className="about-history-section">

                <h2 className="about-section-title">{historyTitle}</h2>

                <div className="about-history-content">

                  <p>{historyIntro}</p>



                  <div className="about-highlight-box">

                    <h4 className="about-highlight-title">Основные вехи развития</h4>

                    <p>

                      За 15+ лет работы клуб стал ведущей организацией в области разведения

                      и популяризации породы, объединив более 1250 членов по всей России.

                    </p>

                  </div>



                  <p>

                    Начиная с небольшой группы заводчиков в Москве, клуб постепенно расширял свою деятельность, открывая

                    региональные представительства. Сегодня НКП СХ — это экосистема, включающая:

                  </p>



                  <ul className="about-history-ul">

                    <li><span className="about-check">✓</span>Племенной учёт и архив родословных</li>

                    <li><span className="about-check">✓</span>Систему генетического тестирования</li>

                    <li><span className="about-check">✓</span>Образовательные программы</li>

                    <li><span className="about-check">✓</span>Поддержку ездового спорта</li>

                  </ul>



                  <p>

                    Клуб активно сотрудничает с международными организациями, включая интеграцию с крупнейшей мировой базой данных breedarchive.com, что позволяет российским заводчикам участвовать в глобальных селекционных программах.

                  </p>

                </div>

              </section>



              {/* Миссия */}

              <section className="about-mission-section">

                <div className="about-mission-content">

                  <h2 className="about-section-title about-section-title--light section-title--no-underline">Миссия и задачи клуба</h2>

                  <p className="about-mission-lead">{missionLead}</p>



                  <ul className="about-mission-list">

                    <li>

                      <div className="about-mission-icon">🧬</div>

                      <div>

                        <strong>Здоровье породы: </strong>Программы генетического тестирования и мониторинга наследственных

                        заболеваний

                      </div>

                    </li>

                    <li>

                      <div className="about-mission-icon">📚</div>

                      <div>

                        <strong>Образование: </strong>Обучение заводчиков современным методам селекции и ухода за собаками

                      </div>

                    </li>

                    <li>

                      <div className="about-mission-icon">🌐</div>

                      <div>

                        <strong>Международное сотрудничество: </strong>Обмен опытом с ведущими клубами мира и участие в глобальных проектах

                      </div>

                    </li>

                    <li>

                      <div className="about-mission-icon">🏆</div>

                      <div>

                        <strong>Выставочная деятельность: </strong>Организация специализированных выставок и поддержка экспертизы

                      </div>

                    </li>

                    <li>

                      <div className="about-mission-icon">❄️</div>

                      <div>

                        <strong>Ездовой спорт: </strong>Популяризация и развитие традиционного использования породы

                      </div>

                    </li>

                  </ul>

                </div>

              </section>



              {/* Президиум */}

              <section className="about-leadership-section">
                <h2 className="about-section-title">Руководство клуба</h2>

                <div className="about-leader-highlight">
                  <h3 className="about-leader-highlight-title">
                    {highlightLeader.role}
                  </h3>
                  <div className="about-leader-card about-leader-card--plain">
                    <div className="about-leader-avatar">{highlightLeader.icon ?? "👤"}</div>
                    <h3 className="about-leader-name">{highlightLeader.name}</h3>
                    <p className="about-leader-position">
                      <Link
                            to={`/president`}
                            className="about-leader-position about-leader-position-link"
                    >
                    {highlightLeader.role}
                    </Link>
                    </p>
                    {(highlightLeader.mail || highlightLeader.phone) && (
                      <div className="about-leader-contact">
                        {highlightLeader.mail && <p>{highlightLeader.mail}</p>}
                        {highlightLeader.phone && <p>{highlightLeader.phone}</p>}
                      </div>
                    )}
                  </div>
                </div>

                <h3 className="about-leader-group-title">Рабочие группы НКП</h3>
                <div className="about-leadership-grid">
                  {boardLeaders.map((p) => (
                    <div key={p.id} className="about-leader-card">
                      <div className="about-leader-avatar">{p.icon ?? "👤"}</div>
                      <h3 className="about-leader-name">{p.name}</h3>
                      <p className="about-leader-position">
                        {p.working_group_id ? (
                          <Link
                            to={`/working-groups/${p.working_group_id}`}
                            className="about-leader-position about-leader-position-link"
                          >
                            {p.role}
                          </Link>
                        ) : (
                          <span className="about-leader-position">{p.role}</span>
                        )}
                      </p>
                      <div className="about-leader-contact">
                        {p.extra && <p className="about-leader-note">{p.extra}</p>}
                        {p.mail && <p>{p.mail}</p>}
                        {p.phone && <p>{p.phone}</p>}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="about-join-box">
                  <h4 className="about-highlight-title">Хотите присоединиться к работе клуба?</h4>
                  <p>
                    Напишите нам — мы всегда открыты к сотрудничеству и инициативам, которые помогают развивать породу.
                    Укажите регион, направление и опыт, и мы обязательно свяжемся с вами.
                  </p>
                </div>
              </section>

              <section className="about-membership-section">

                <h2 className="about-section-title">Членство в НКП</h2>

                <p className="about-membership-lead">

                  Присоединение к НКП Сибирский Хаски открывает доступ к уникальным возможностям и привилегиям для заводчиков и владельцев собак.

                </p>



                <div className="about-membership-types">

                  <div className="about-membership-card">

                    <h3 className="about-membership-title">👤 Физические лица</h3>

                    <ul className="about-membership-benefits">

                      {[

                        "Приоритетная техническая поддержка сайта НКП",

                        "Консультации по разведению и документообороту",

                        "Полный доступ к видео-курсам и обучающим материалам",

                        "Бесплатный доступ к онлайн-библиотеке НКП",

                        "Скидка 25% в Центре ветеринарной генетики ЗООГЕН",

                        "Льготная регистрация на монопородные мероприятия",

                        "Приоритетное информирование о мероприятиях",

                        "Бесплатное размещение информации о Чемпионах",

                        "Доступ к закрытым разделам сайта",

                      ].map((x) => (

                        <li key={x}>

                          <span className="about-benefit-check">✓</span>

                          {x}

                        </li>

                      ))}

                    </ul>

                  </div>



                  <div className="about-membership-card">

                    <h3 className="about-membership-title">🏢 Юридические лица (клубы)</h3>

                    <ul className="about-membership-benefits">

                      {[

                        "Методическая помощь в организации мероприятий",

                        "Предоставление типовых документов и регламентов",

                        "Бесплатное размещение анонсов мероприятий",

                        "Освещение мероприятий в официальных изданиях",

                        "Продвижение в социальных сетях НКП",

                        "Содействие в подаче ходатайств в РКФ",

                        "Поддержка в вопросах повышения ранга мероприятий",

                        "Помощь в согласовании кандидатур судей",

                        "Привлечение спонсорской поддержки от партнеров",

                      ].map((x) => (

                        <li key={x}>

                          <span className="about-benefit-check">✓</span>

                          {x}

                        </li>

                      ))}

                    </ul>

                  </div>

                </div>



                {/*<div className="about-membership-terms">*/}

                {/*  <h4 className="about-highlight-title">💰 Условия членства</h4>*/}

                {/*  <div className="about-terms-grid">*/}

                {/*    <div>*/}

                {/*      <strong className="about-terms-accent">Вступительный взнос:</strong>*/}

                {/*      <p className="about-terms-note">5 000 ₽ (разовый)</p>*/}

                {/*    </div>*/}

                {/*    <div>*/}

                {/*      <strong className="about-terms-accent">Годовой взнос:</strong>*/}

                {/*      <p className="about-terms-note">3 000 ₽</p>*/}

                {/*    </div>*/}

                {/*    <div>*/}

                {/*      <strong className="about-terms-accent">Для юрлиц:</strong>*/}

                {/*      <p className="about-terms-note">15 000 ₽ / год</p>*/}

                {/*    </div>*/}

                {/*  </div>*/}

                {/*</div>*/}

              </section>



              {/* Контакты */}

              <section className="about-contact-section">

                <h2 className="about-section-title">Контактная информация</h2>

                <div className="about-contact-grid">
                  {contacts.map((c) => (
                    <div key={c.id} className="about-contact-method">
                      <div className="about-contact-icon">{c.icon}</div>
                      <h3 className="about-contact-title">{c.title}</h3>

                      {c.links ? (
                        <div className="about-contact-links">
                          {c.links.map((link) => (
                            <a
                              key={link.url}
                              href={link.url}
                              target="_blank"
                              rel="noreferrer"
                              className="about-contact-info"
                            >
                              {link.label}
                            </a>
                          ))}
                        </div>
                      ) : c.href ? (
                        <a href={c.href} className="about-contact-info">
                          {c.text}
                        </a>
                      ) : (
                        <p className="about-contact-info">{c.text}</p>
                      )}
                    </div>
                  ))}
                </div>



                <div className="about-contact-cta">

                  <h3 className="about-highlight-title">Форма обратной связи</h3>

                  <p>Есть вопросы? Напишите нам — ответим в течение 24 часов.</p>

                  <Link to="/contact" className="about-contact-cta-btn">Написать сообщение</Link>

                </div>

              </section>

            </div>



            <ClubSidebar stickyTopPx={120} />

          </div>

        </div>

      </main>

    </div>

  );

}



