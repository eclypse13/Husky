import { Link } from "react-router-dom";
import { useEffect, useRef } from "react";
import "./About.css";

export default function About() {
  const pageRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    const els = root.querySelectorAll<HTMLElement>(
      ".history-section, .mission-section, .leadership-section, .membership-section, .contact-section, .sidebar-card"
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

  return (
    <div ref={pageRef}>
      {/* Хлебные крошки */}
      <section className="breadcrumb">
        <div className="breadcrumb-content">
          <nav className="breadcrumb-nav">
            <Link to="/">Главная</Link>
            <span>→</span>
            <span>О клубе</span>
          </nav>
          <h1 className="breadcrumb-title">О клубе</h1>
        </div>
      </section>

      {/* Контент */}
      <main className="main-content">
        <div className="content-container">
          <div className="content-grid">
            <div className="main-column">
              {/* История */}
              <section className="history-section">
                <h2 className="section-title">История НКП Сибирский Хаски</h2>
                <div className="history-content">
                  <p>
                    Национальный клуб породы "Сибирский хаски" был основан в 2008 году группой
                    энтузиастов и профессиональных кинологов, объединенных общей целью —
                    сохранение и развитие породы сибирский хаски в России.
                  </p>

                  <div className="highlight-box">
                    <h4>Основные вехи развития</h4>
                    <p>
                      За 15+ лет работы клуб стал ведущей организацией в области разведения
                      и популяризации породы, объединив более 1250 членов по всей России.
                    </p>
                  </div>

                  <p>
                    Начиная с небольшой группы заводчиков в Москве, клуб постепенно расширял свою деятельность, открывая
                    региональные представительства. Сегодня НКП СХ — это экосистема, включающая:
                  </p>

                  <ul className="history-ul">
                    <li><span className="check">✓</span>Племенной учёт и архив родословных</li>
                    <li><span className="check">✓</span>Систему генетического тестирования</li>
                    <li><span className="check">✓</span>Образовательные программы</li>
                    <li><span className="check">✓</span>Поддержку ездового спорта</li>
                  </ul>

                  <p>
                    Клуб активно сотрудничает с международными организациями, включая интеграцию с крупнейшей мировой базой данных breedarchive.com, что позволяет российским заводчикам участвовать в глобальных селекционных программах.
                  </p>
                </div>
              </section>

              {/* Миссия */}
              <section className="mission-section">
                <div className="mission-content">
                  <h2 className="section-title section-title--light">Миссия и задачи клуба</h2>
                  <p className="mission-lead">
                    Наша миссия — сохранение породных качеств сибирского хаски, развитие культуры ответственного разведения и создание сильного профессионального сообщества заводчиков и владельцев.
                  </p>

                  <ul className="mission-list">
                    <li>
                      <div className="mission-icon">🧬</div>
                      <div>
                        <strong>Здоровье породы: </strong>Программы генетического тестирования и мониторинга наследственных
                        заболеваний
                      </div>
                    </li>
                    <li>
                      <div className="mission-icon">📚</div>
                      <div>
                        <strong>Образование: </strong>Обучение заводчиков современным методам селекции и ухода за собаками
                      </div>
                    </li>
                    <li>
                      <div className="mission-icon">🌐</div>
                      <div>
                        <strong>Международное сотрудничество: </strong>Обмен опытом с ведущими клубами мира и участие в глобальных проектах
                      </div>
                    </li>
                    <li>
                      <div className="mission-icon">🏆</div>
                      <div>
                        <strong>Выставочная деятельность: </strong>Организация специализированных выставок и поддержка экспертизы
                      </div>
                    </li>
                    <li>
                      <div className="mission-icon">❄️</div>
                      <div>
                        <strong>Ездовой спорт: </strong>Популяризация и развитие традиционного использования породы
                      </div>
                    </li>
                  </ul>
                </div>
              </section>

              {/* Президиум */}
              <section className="leadership-section">
                <h2 className="section-title">Президиум НКП</h2>

                <div className="leader-highlight">
                  <h3 className="leader-highlight-title">Президент НКП Сибирский хаски</h3>
                  <div className="leader-card leader-card--plain">
                    <div className="leader-avatar">👩‍💼</div>
                    <h3 className="leader-name">Татьяна Евграфова</h3>
                    <p className="leader-position">Президент НКП СХ</p>
                    <div className="leader-contact">
                      <p>president@nkp-husky.ru</p>
                      <p>+7 (495) 123-45-67</p>
                    </div>
                  </div>
                </div>

                <h3 className="leader-group-title">Рабочие группы НКП</h3>
                <div className="leadership-grid">
                  {[
                    { icon: "📰", name: "Татьяна Солдатова", role: "СМИ и информационные материалы", extra: "Совместно с Анной Фалуниной", mail: "media@nkp-husky.ru" },
                    { icon: "💻", name: "Влада Кугуракова", role: "Информационные системы", mail: "it@nkp-husky.ru" },
                    { icon: "🌐", name: "Марина Акопова", role: "Международное сотрудничество", mail: "international@nkp-husky.ru" },
                    { icon: "🏆", name: "Татьяна Евграфова", role: "Выставочные мероприятия", extra: "В составе: Алла Проферансова, Татьяна Солдатова", mail: "events@nkp-husky.ru" },
                    { icon: "📐", name: "Татьяна Евграфова", role: "Стандарт породы", extra: "В составе: А.А. Фалунина, Т.А. Солдатова, Е.М. Шепелёва, М.С. Акопова, И.Л. Швец", mail: "standard@nkp-husky.ru" },
                    { icon: "🏃‍♀️", name: "Елена Шепелёва", role: "Ездовой спорт", mail: "sport@nkp-husky.ru" },
                    { icon: "📊", name: "Анна Фалунина", role: "Породный рейтинг", mail: "rating@nkp-husky.ru" },
                  ].map((p) => (
                    <div key={p.mail} className="leader-card">
                      <div className="leader-avatar">{p.icon}</div>
                      <h3 className="leader-name">{p.name}</h3>
                      <p className="leader-position">{p.role}</p>
                      <div className="leader-contact">
                        {p.extra && <p className="leader-note">{p.extra}</p>}
                        <p>{p.mail}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="join-box">
                  <h4>🤝 Присоединение к рабочим группам</h4>
                  <p>
                    Члены НКП Сибирский хаски могут присоединяться к рабочим группам на основании заявления и решения руководителя соответствующей группы. Это отличная возможность внести личный вклад в развитие породы и получить ценный опыт.
                  </p>
                </div>
              </section>

              {/* Членство */}
              <section className="membership-section">
                <h2 className="section-title">Членство в НКП</h2>
                <p className="membership-lead">
                  Присоединение к НКП Сибирский Хаски открывает доступ к уникальным возможностям и привилегиям для заводчиков и владельцев собак.
                </p>

                <div className="membership-types">
                  <div className="membership-card">
                    <h3 className="membership-title">👤 Физические лица</h3>
                    <ul className="membership-benefits">
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
                          <span className="benefit-check">✓</span>
                          {x}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="membership-card">
                    <h3 className="membership-title">🏢 Юридические лица (клубы)</h3>
                    <ul className="membership-benefits">
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
                          <span className="benefit-check">✓</span>
                          {x}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="membership-terms">
                  <h4>💰 Условия членства</h4>
                  <div className="terms-grid">
                    <div>
                      <strong className="terms-accent">Вступительный взнос:</strong>
                      <p className="terms-note">5 000 ₽ (разовый)</p>
                    </div>
                    <div>
                      <strong className="terms-accent">Годовой взнос:</strong>
                      <p className="terms-note">3 000 ₽</p>
                    </div>
                    <div>
                      <strong className="terms-accent">Для юрлиц:</strong>
                      <p className="terms-note">15 000 ₽ / год</p>
                    </div>
                  </div>
                </div>
              </section>

              {/* Контакты */}
              <section className="contact-section">
                <h2 className="section-title">Контактная информация</h2>
                <div className="contact-grid">
                  {[
                    { icon: "📧", title: "Email", text: "info@nkp-husky.ru" },
                    { icon: "📱", title: "Телефон", text: "+7 (495) 123-45-67" },
                    { icon: "🌐", title: "Социальные сети", text: "@nkp_husky" },
                    { icon: "📍", title: "Адрес", text: "Москва, ул. Кинологическая, 15" },
                  ].map((c) => (
                    <div key={c.title} className="contact-method">
                      <div className="contact-icon">{c.icon}</div>
                      <h3 className="contact-title">{c.title}</h3>
                      <p className="contact-info">{c.text}</p>
                    </div>
                  ))}
                </div>

                <div className="contact-cta">
                  <h3>Форма обратной связи</h3>
                  <p>Есть вопросы? Напишите нам — ответим в течение 24 часов.</p>
                  <Link to="/contact" className="contact-cta-btn">Написать сообщение</Link>
                </div>
              </section>
            </div>

            {/* Сайдбар */}
            <aside className="sidebar">
              <div className="sidebar-card">
                <h3 className="sidebar-title">📄 Документы клуба</h3>
                <div className="document-list">
                  {[
                    { icon: "📋", title: "Устав НКП СХ", sub: "PDF, 2.1 МБ" },
                    { icon: "📜", title: "Племенное положение", sub: "PDF, 1.8 МБ" },
                    { icon: "🏆", title: "Выставочное положение", sub: "PDF, 1.5 МБ" },
                    { icon: "📐", title: "Стандарт породы FCI", sub: "PDF, 0.9 МБ" },
                    { icon: "📝", title: "Заявление на членство", sub: "DOC, 0.2 МБ" },
                    { icon: "💰", title: "Реквизиты для оплаты", sub: "PDF, 0.1 МБ" },
                  ].map((d) => (
                    <Link key={d.title} to="#" className="document-item">
                      <div className="document-icon">{d.icon}</div>
                      <div>
                        <div className="document-title">{d.title}</div>
                        <div className="document-sub">{d.sub}</div>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>

              <div className="sidebar-card">
                <h3 className="sidebar-title">📊 Статистика клуба</h3>
                <div className="stats-grid">
                  <div className="stat-box">
                    <div className="stat-number">1,250+</div>
                    <div className="stat-label">Членов</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-number">350+</div>
                    <div className="stat-label">Питомников</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-number">15,000+</div>
                    <div className="stat-label">Собак в архиве</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-number">85</div>
                    <div className="stat-label">Регионов</div>
                  </div>
                </div>
              </div>

              <div className="sidebar-card">
                <h3 className="sidebar-title">🚀 Быстрые действия</h3>
                <div className="quick-actions">
                  <Link to="/join" className="qa-primary">Подать заявление</Link>
                  <Link to="/contact" className="qa-info">Задать вопрос</Link>
                  <Link to="/events" className="qa-neutral">Календарь мероприятий</Link>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </main>
    </div>
  );
}
