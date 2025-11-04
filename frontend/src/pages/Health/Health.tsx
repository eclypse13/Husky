import { useEffect, useRef } from "react";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./Health.css";

export default function Health() {
  const pageRef = useRef<HTMLDivElement | null>(null);

  // Reveal-on-scroll
  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    const els = root.querySelectorAll<HTMLElement>(
      ".health-search-section, .health-stats .health-stat, .health-card"
    );

    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => e.isIntersecting && e.target.setAttribute("data-visible", "1")),
      { threshold: 0.12, rootMargin: "0px 0px -50px 0px" }
    );

    els.forEach((el) => {
      el.setAttribute("data-visible", "0");
      io.observe(el);
    });

    return () => io.disconnect();
  }, []);

  // Числовая анимация
  useEffect(() => {
    const nums = pageRef.current?.querySelectorAll<HTMLElement>(".health-stat-number");
    if (!nums) return;

    nums.forEach((node) => {
      const raw = node.dataset.target || node.textContent || "0";
      const target = parseInt(raw.replace(/[^\d]/g, ""), 10);
      let cur = 0;
      const step = Math.max(1, Math.floor(target / 100));
      const t = setInterval(() => {
        cur += step;
        if (cur >= target) {
          cur = target;
          clearInterval(t);
        }
        node.textContent = cur.toLocaleString("ru-RU");
      }, 16);
    });
  }, []);

  return (
    <div ref={pageRef} className="health-page">
      <Breadcrumb
        title="Здоровье породы"
        items={[{ label: "Главная", to: "/" }, { label: "Здоровье породы" }]}
      />

      <main className="health-main">
        <div className="health-container">
          <div className="health-col">
            {/* Поиск ДНК */}
            <section className="health-search-section">
              <div className="health-search-head">
                <h2 className="health-title">Поиск по базе ДНК-тестов</h2>
                <p className="health-sub">
                  Введите кличку, клеймо или регистрационный номер, чтобы найти результаты тестов.
                </p>
              </div>

              <form
                className="health-search-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  // сюда добавишь API-запрос
                }}
              >
                <input
                  className="health-input"
                  placeholder="Например: Arctic Storm's Thunder King…"
                />
                <button type="submit" className="health-btn health-btn--primary">
                  🔍 Найти
                </button>
              </form>

              <div className="health-filters">
                <select className="health-select">
                  <option>Все тесты</option>
                  <option>PRA</option>
                  <option>EIC</option>
                  <option>SHOR</option>
                </select>
                <select className="health-select">
                  <option>Любой статус</option>
                  <option>Clear</option>
                  <option>Carrier</option>
                  <option>Affected</option>
                </select>
                <select className="health-select">
                  <option>Любая лаборатория</option>
                  <option>ЗООГЕН</option>
                  <option>Embark</option>
                  <option>Genomia</option>
                </select>
              </div>
            </section>

            {/* Статистика */}
            <section className="health-stats">
              {[
                { icon: "🧬", num: "8456", label: "Проведено тестов", trend: "+124 за месяц" },
                { icon: "🐾", num: "3210", label: "Собак с результатами", trend: "+55 новых" },
                { icon: "🟢", num: "73", suffix: "%", label: "Clear", trend: "+1.2% за квартал" },
                { icon: "🧪", num: "12", label: "Доступных тестов", trend: "Обновлено в 2025" },
              ].map((s) => (
                <article className="health-stat" key={s.label}>
                  <div className="health-stat-icon">{s.icon}</div>
                  <div
                    className="health-stat-number"
                    data-target={s.num}
                    style={{ fontVariantNumeric: "tabular-nums" }}
                  >
                    {s.suffix ? `${s.num}${s.suffix}` : s.num}
                  </div>
                  <div className="health-stat-label">{s.label}</div>
                  <div className="health-stat-trend">{s.trend}</div>
                </article>
              ))}
            </section>

            {/* Объяснение статусов */}
            <section className="health-card">
              <h3 className="health-card-title">Объяснение статусов</h3>
              <ul className="health-list">
                <li><b>Clear:</b> собака не несёт мутаций по данному заболеванию.</li>
                <li><b>Carrier:</b> носитель — не болен, но может передать мутацию потомству.</li>
                <li><b>Affected:</b> имеет мутацию и может быть подвержен заболеванию.</li>
                <li><b>SHOR Normal:</b> нормальный результат офтальмологического обследования.</li>
              </ul>
            </section>

            {/* Инструкция */}
            <section className="health-card">
              <h3 className="health-card-title">Как сдать ДНК-тест</h3>
              <ul className="health-list">
                <li>1. Выберите лабораторию: ЗООГЕН, Embark, Genomia.</li>
                <li>2. Закажите набор для сбора образца (слюна или мазок).</li>
                <li>3. Отправьте образец и дождитесь результата (обычно 2–3 недели).</li>
                <li>4. Внесите данные в базу НКП (форма «добавить результат»).</li>
              </ul>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
