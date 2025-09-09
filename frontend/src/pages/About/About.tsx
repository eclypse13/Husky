import { Link } from "react-router-dom";
import { useEffect, useRef } from "react";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import ClubSidebar from "@/components/Sidebar/ClubSidebar";
import "./About.css";

export default function About() {
  const pageRef = useRef<HTMLDivElement | null>(null);

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
                <h2 className="about-section-title">История НКП Сибирский Хаски</h2>
                <div className="about-history-content">
                  <p>
                    Национальный клуб породы "Сибирский хаски" был основан в 2008 году группой
                    энтузиастов и профессиональных кинологов, объединенных общей целью —
                    сохранение и развитие породы сибирский хаски в России.
                  </p>

                  <div className="about-highlight-box">
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
                  <p className="about-mission-lead">
                    Наша миссия — сохранение породных качеств сибирского хаски, развитие культуры ответственного разведения и создание сильного профессионального сообщества заводчиков и владельцев.
                  </p>

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
                <h2 className="about-section-title">Президиум НКП</h2>

                <div className="about-leader-highlight">
                  <h3 className="about-leader-highlight-title">Президент НКП Сибирский хаски</h3>
                  <div className="about-leader-card about-leader-card--plain">
                    <div className="about-leader-avatar">👩‍💼</div>
                    <h3 className="about-leader-name">Татьяна Евграфова</h3>
                    <p className="about-leader-position">Президент НКП СХ</p>
                    <div className="about-leader-contact">
                      <p>president@nkp-husky.ru</p>
                      <p>+7 (495) 123-45-67</p>
                    </div>
                  </div>
                </div>

                <h3 className="about-leader-group-title">Рабочие группы НКП</h3>
                <div className="about-leadership-grid">
                  {[
                    { icon: "📰", name: "Татьяна Солдатова", role: "СМИ и информационные материалы", extra: "Совместно с Анной Фалуниной", mail: "media@nkp-husky.ru" },
                    { icon: "💻", name: "Влада Кугуракова", role: "Информационные системы", mail: "it@nkp-husky.ru" },
                    { icon: "🌐", name: "Марина Акопова", role: "Международное сотрудничество", mail: "international@nkp-husky.ru" },
                    { icon: "🏆", name: "Татьяна Евграфова", role: "Выставочные мероприятия", extra: "В составе: Алла Проферансова, Татьяна Солдатова", mail: "events@nkp-husky.ru" },
                    { icon: "📐", name: "Татьяна Евграфова", role: "Стандарт породы", extra: "В составе: А.А. Фалунина, Т.А. Солдатова, Е.М. Шепелёва, М.С. Акопова, И.Л. Швец", mail: "standard@nkp-husky.ru" },
                    { icon: "🏃‍♀️", name: "Елена Шепелёва", role: "Ездовой спорт", mail: "sport@nkp-husky.ru" },
                    { icon: "📊", name: "Анна Фалунина", role: "Породный рейтинг", mail: "rating@nkp-husky.ru" },
                  ].map((p) => (
                    <div key={p.mail} className="about-leader-card">
                      <div className="about-leader-avatar">{p.icon}</div>
                      <h3 className="about-leader-name">{p.name}</h3>
                      <p className="about-leader-position">{p.role}</p>
                      <div className="about-leader-contact">
                        {p.extra && <p className="about-leader-note">{p.extra}</p>}
                        <p>{p.mail}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="about-join-box">
                  <h4>🤝 Присоединение к рабочим группам</h4>
                  <p>
                    Члены НКП Сибирский хаски могут присоединяться к рабочим группам на основании заявления и решения руководителя соответствующей группы. Это отличная возможность внести личный вклад в развитие породы и получить ценный опыт.
                  </p>
                </div>
              </section>

              {/* Членство */}
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

                <div className="about-membership-terms">
                  <h4>💰 Условия членства</h4>
                  <div className="about-terms-grid">
                    <div>
                      <strong className="about-terms-accent">Вступительный взнос:</strong>
                      <p className="about-terms-note">5 000 ₽ (разовый)</p>
                    </div>
                    <div>
                      <strong className="about-terms-accent">Годовой взнос:</strong>
                      <p className="about-terms-note">3 000 ₽</p>
                    </div>
                    <div>
                      <strong className="about-terms-accent">Для юрлиц:</strong>
                      <p className="about-terms-note">15 000 ₽ / год</p>
                    </div>
                  </div>
                </div>
              </section>

              {/* Контакты */}
              <section className="about-contact-section">
                <h2 className="about-section-title">Контактная информация</h2>
                <div className="about-contact-grid">
                  {[
                    { icon: "📧", title: "Email", text: "info@nkp-husky.ru" },
                    { icon: "📱", title: "Телефон", text: "+7 (495) 123-45-67" },
                    { icon: "🌐", title: "Социальные сети", text: "@nkp_husky" },
                    { icon: "📍", title: "Адрес", text: "Москва, ул. Кинологическая, 15" },
                  ].map((c) => (
                    <div key={c.title} className="about-contact-method">
                      <div className="about-contact-icon">{c.icon}</div>
                      <h3 className="about-contact-title">{c.title}</h3>
                      <p className="about-contact-info">{c.text}</p>
                    </div>
                  ))}
                </div>

                <div className="about-contact-cta">
                  <h3>Форма обратной связи</h3>
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
