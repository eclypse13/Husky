import { useEffect, useRef } from "react";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./Events.css";

export default function Events() {
  const pageRef = useRef<HTMLDivElement | null>(null);

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
                <h2 className="events-section-title">Календарь выставок и мероприятий</h2>
                <p className="events-text">
                  Следующие официальные мероприятия, организованные НКП Сибирский Хаски:
                </p>
                <ul className="events-list">
                  <li><strong>25 июля 2025:</strong> Семинар для судей — Москва</li>
                  <li><strong>15 августа 2025:</strong> Специализированная выставка — Санкт-Петербург</li>
                  <li><strong>7 сентября 2025:</strong> День ездового спорта — Казань</li>
                  <li><strong>22 сентября 2025:</strong> Онлайн-вебинар по грумингу хаски</li>
                </ul>
              </section>

              {/* Отчёты (градиентный блок) */}
              <section className="events-section events-section--gradient">
                <div className="events-gradient-inner">
                  <h2 className="events-section-title events-section-title--light">
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
                <h2 className="events-section-title">Породные эксперты и судьи</h2>
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
                <h2 className="events-section-title">Семинары и обучение</h2>
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
                <h3 className="events-sidebar-title">📅 Ближайшие мероприятия</h3>
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
                <h3 className="events-sidebar-title">📸 Фото и видео отчёты</h3>
                <ul className="events-links">
                  <li><a href="#">📷 «Сибирская Красота 2025»</a></li>
                  <li><a href="#">🎥 Чемпионат по драйленду</a></li>
                  <li><a href="#">📷 Семинар хендлеров</a></li>
                </ul>
                <a className="events-pill events-pill--info" href="#">Все отчёты</a>
              </div>

              <div className="sidebar-card">
                <h3 className="events-sidebar-title">👨‍⚖️ Судьи и семинары</h3>
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
