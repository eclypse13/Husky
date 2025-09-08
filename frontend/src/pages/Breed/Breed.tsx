import { useEffect, useRef } from "react";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import ClubSidebar from "@/components/Sidebar/ClubSidebar";
import "./Breed.css";

export default function Breed() {
  const pageRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    const targets = root.querySelectorAll<HTMLElement>(
      ".breed-section, .sidebar-card"
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
      <Breadcrumb
        title="О породе"
        items={[{ label: "Главная", to: "/" }, { label: "О породе" }]}
      />

      {/* Контент */}
      <main className="main-content">
        <div className="content-container">
          <div className="content-grid">
            <div className="main-column">
              <section className="history-section">
                <h2 className="section-title">📏 Стандарт породы</h2>
                <p className="section-subtitle">
                  Национальный клуб породы Сибирский Хаски следует официальному стандарту FCI №270. Это рабочая ездовая порода, гармонично сложенная, с умеренным костяком, лёгкой и упругой походкой, типичной для северных пород.
                </p>

                <img
                  className="img-center"
                  alt="Эталонный экстерьер сибирского хаски"
                  src="https://images.squarespace-cdn.com/content/v1/5e0fdcb67e94e335cab5dc5a/8a4cbc04-7b2d-4612-8d01-989f242ecb05/redwhite.jpg?format=2500w"
                />

                <div className="highlight-box">
                  <div className="breed-section-subtitle">
                    <p className="breed-margin"><strong>Высота в холке:</strong> кобели — 53–60 см, суки —
                    51–56см</p>
                    <p className="breed-margin"><strong>Вес:</strong> кобели — 20–27 кг, суки — 16–23 кг</p>
                    <p className="breed-margin"><strong>Окрас:</strong> ддопускаются любые окрасы от чисто белого до чёрного с отметинами</p>
                    <p style={{"margin": 0}}><strong>Глаза:</strong> голубые, карие, янтарные или разного
                    цвета</p>
                  </div>
                </div>
              </section>

              {/* Характер */}
              <section className="history-section">
                <div className="breed-mission-content">
                  <h2 className="section-title">
                    🧠 Характер и особенности
                  </h2>
                  <p className="section-subtitle">
                    Сибирские хаски — дружелюбные, энергичные и умные собаки. Они не охранники, но прекрасно чувствуют себя в активной семье и команде.
                  </p>
                  <div className="highlight-box">
                    <ul className="breed-mission-list">
                      {[
                        "Очень активны, нуждаются в ежедневной физической нагрузке",
                        "Не склонны к агрессии или застенчивости",
                        "Общительны с другими собаками и людьми",
                        "Обожают бег и могут преодолевать большие расстояния",
                      ].map((text, i) => (
                        <li key={`c-${i}`}>
                          {text}
                        </li>
                      ))}
                    </ul>
                  </div>

                </div>
              </section>

              {/* Уход */}
              <section className="history-section">
                <h2 className="section-title">✂️ Уход и груминг</h2>
                <p className="section-subtitle">
                  Хаски имеют густую двойную шерсть, которая требует регулярного вычёсывания, особенно в периоды линьки.
                </p>
                <div className="highlight-box">
                  <ul className="breed-mission-list">
                    <li>2–3 раза в неделю расчёсывание (ежедневно во время линьки)</li>
                    <li>Не требуют частого мытья</li>
                    <li>Не стригутся — это нарушает структуру шерсти</li>
                    <li>Важно следить за когтями и ушами</li>
                  </ul>
                </div>
              </section>

              {/* Кормление */}
              <section className="history-section">
                <h2 className="section-title">🍽️ Кормление</h2>
                <p className="section-subtitle">
                  Метаболизм у сибирских хаски «экономный», поэтому перекармливать их легко. Подходят как качественные промышленные корма, так и натуралка — при грамотном подборе.
                </p>
                <div className="terms-grid">
                  {[
                    "Важно соблюдать режим кормления",
                    "Нельзя перекармливать — склонны к худобе, но при этом легко набирают «пустой» вес",
                    "Вода — всегда в свободном доступе",
                    "Для щенков, беременных и пожилых — отдельный рацион",
                  ].map((t, i) => (
                    <div className="term" key={`f-${i}`}>
                      {t}
                    </div>
                  ))}
                </div>
              </section>

              {/* История */}
              <section className="history-section">
                <h2 className="section-title">📜 История породы</h2>
                <p className="section-subtitle">
                  Сибирские хаски происходят от ездовых собак коренных народов Северо-Восточной Сибири. В начале XX века они были вывезены на Аляску, где проявили себя в гонках и спасательных экспедициях.
                </p>
                <p className="section-subtitle">
                  Порода официально признана в США в 1930 году. С тех пор она распространилась по всему миру, сохранив рабочие качества, интеллект и красоту.
                </p>

                {/* <div className="contact-cta">
                  <h3>Хотите узнать больше?</h3>
                  <p>
                    Посмотрите официальный стандарт FCI и раздел о здоровье
                    породы.
                  </p>
                  <div className="cta-row">
                    <Link to="#" className="contact-cta-btn">
                      Стандарт FCI
                    </Link>
                    <Link to="/health" className="contact-cta-btn contact-cta-btn--ghost">
                      Здоровье породы
                    </Link>
                  </div>
                </div> */}
              </section>
            </div>

            <ClubSidebar stickyTopPx={120} />
          </div>
        </div>
      </main>
    </div>
  );
}
