import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./SmartTools.css";

export default function SmartTools() {
  const pageRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    const els = root.querySelectorAll<HTMLElement>(
      ".smart-history-section, .smart-tools-section, .smart-upcoming-section, .sidebar-card"
    );

    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && e.target.setAttribute("data-visible", "1")),
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );

    els.forEach((el) => {
      el.setAttribute("data-visible", "0");
      obs.observe(el);
    });

    return () => obs.disconnect();
  }, []);

  return (
    <div ref={pageRef} className="smart-page">
      <Breadcrumb
        title="Умные инструменты"
        items={[{ label: "Главная", to: "/" }, { label: "Умные инструменты" }]}
      />

      <main className="smart-main-content">
        <div className="smart-content-container">
          <div className="smart-content-grid">
            {/* Левая колонка */}
            <div className="smart-main-column">
              <section className="smart-history-section">
                <h2 className="smart-section-title">Цифровая помощь заводчику</h2>
                <div className="smart-history-content">
                  <p>
                    В НКП Сибирский Хаски мы развиваем экосистему умных цифровых решений: автоматический
                    анализ ДНК-тестов, инструменты для подбора пар, компьютерное зрение и многое другое —
                    всё для поддержки владельцев и заводчиков.
                  </p>
                </div>
              </section>

              {/* Инструменты */}
              <section className="smart-tools-section">
                <h2 className="smart-section-title">Доступные инструменты</h2>

                <div className="smart-tools-grid">
                  {[
                    { icon: "🧬", name: "Анализ ДНК-тестов", tag: "Clear / Carrier / Affected", desc: "Автоматическое определение статуса по генетическим данным" },
                    { icon: "📈", name: "Предиктивная селекция", tag: "Риски заболеваний", desc: "Прогноз возможных наследственных проблем в помёте" },
                    { icon: "🔁", name: "Калькулятор инбридинга", tag: "По родословной", desc: "Оценка степени родства и рисков при подборе пары" },
                    { icon: "🤖", name: "Компьютерное зрение", tag: "В разработке", desc: "Анализ экстерьера собаки по фотографии" },
                    { icon: "📊", name: "Статистика породы", tag: "Окрасы, титулы, здоровье", desc: "Интерактивные графики и визуализация трендов" },
                    { icon: "🧠", name: "Генератор имён", tag: "AI-помощник", desc: "Создание уникальных кличек для щенков по приставке" },
                  ].map((t) => (
                    <article key={t.name} className="smart-tool-card">
                      <div className="smart-tool-avatar">{t.icon}</div>
                      <h3 className="smart-tool-name">{t.name}</h3>
                      <p className="smart-tool-tag">{t.tag}</p>
                      <p className="smart-tool-desc">{t.desc}</p>
                    </article>
                  ))}
                </div>
              </section>

              {/* Скоро */}
              <section className="smart-upcoming-section">
                <h2 className="smart-section-title">Скоро появятся</h2>

                <div className="smart-upcoming-grid">
                  {[
                    {
                      title: "🔬 Морфометрический анализ",
                      items: ["Сравнение экстерьера с породным стандартом", "Выявление отклонений"],
                    },
                    {
                      title: "🧭 Планировщик вязок",
                      items: ["Подбор пары с учётом генетики", "Предварительная оценка потомства"],
                    },
                    {
                      title: "🔗 Интеграция с breedarchive",
                      items: ["Импорт родословных", "Сравнение линий"],
                    },
                  ].map((b) => (
                    <div key={b.title} className="smart-upcoming-card">
                      <h3 className="smart-upcoming-title">{b.title}</h3>
                      <ul className="smart-upcoming-list">
                        {b.items.map((x) => (
                          <li key={x}>
                            <span className="smart-benefit-check">✓</span>
                            {x}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <aside className="smart-sidebar" aria-label="Боковая панель инструментов">
              <div className="smart-sidebar__container">
                <div className="smart-sidebar__empty"></div>
                <div className="smart-sidebar__sticky">
                  <div className="smart-sidebar-card">
                    <h3 className="smart-sidebar-title">📄 FAQ по инструментам</h3>
                    <ul className="smart-document-list">
                      <li>
                        <Link to="/faq/tools#calc" className="smart-document-item">
                          <div className="smart-document-icon">❓</div>
                          <div>Как использовать калькулятор?</div>
                        </Link>
                      </li>
                      <li>
                        <Link to="/faq/tools#upload" className="smart-document-item">
                          <div className="smart-document-icon">📤</div>
                          <div>Как загрузить данные собаки?</div>
                        </Link>
                      </li>
                      <li>
                        <Link to="/faq/tools#privacy" className="smart-document-item">
                          <div className="smart-document-icon">🔐</div>
                          <div>Конфиденциальность данных</div>
                        </Link>
                      </li>
                    </ul>
                  </div>

                  <div className="smart-sidebar-card">
                    <h3 className="smart-sidebar-title">📥 Загрузка данных</h3>
                    <div className="smart-sidebar-upload">
                      <p className="smart-sidebar-note">Поддерживаются PDF, JPG, DOCX</p>
                      <Link to="/upload" className="smart-sidebar-btn">Загрузить файл</Link>
                    </div>
                  </div>

                  <div className="smart-sidebar-card">
                    <h3 className="smart-sidebar-title">💡 Предложить идею</h3>
                    <p className="smart-sidebar-note">Есть идея нового инструмента? Напишите нам!</p>
                    <Link to="/contact" className="smart-sidebar-btn smart-sidebar-btn--ghost">Отправить предложение</Link>
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </main>
    </div>
  );
}
