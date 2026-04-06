import { useEffect, useMemo, useRef } from "react";
import { useDictList } from "@/generated/content-dictionary/content-dictionary";
import { pickValue } from "@/lib/dict";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import ClubSidebar from "@/components/Sidebar/ClubSidebar";
import "./Breed.css";

export default function Breed() {
  const pageRef = useRef<HTMLDivElement | null>(null);
  const { data: dictResponse } = useDictList();
  const dict = useMemo(() => (dictResponse?.data?.results ?? []) as any[], [dictResponse]);
  const breedTitle = useMemo(() => pickValue(dict, 'BREED_TITLE', 'ru'), [dict]);
  const breedStandard = useMemo(() => pickValue(dict, 'BREED_STANDARD', 'ru'), [dict]);
  const breedCharacter = useMemo(() => pickValue(dict, 'BREED_CHARACTER', 'ru'), [dict]);
  const breedCareTitle = useMemo(() => pickValue(dict, 'BREED_CARE_TITLE', 'ru'), [dict]);
  const breedCare = useMemo(() => pickValue(dict, 'BREED_CARE', 'ru'), [dict]);
  const breedHistory = useMemo(() => pickValue(dict, 'BREED_HISTORY', 'ru'), [dict]);

  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    const targets = root.querySelectorAll<HTMLElement>(".breed-section, .club-sidebar__card");

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
    <div ref={pageRef} className="breed-page">
      <Breadcrumb
        title="О породе"
        items={[{ label: "Главная", to: "/" }, { label: "О породе" }]}
      />

      {/* Контент */}
      <main className="breed-main-content">
        <div className="breed-content-container">
          <div className="breed-content-grid">
            <div className="main-column">
              {/* Стандарт породы */}
              <section className="breed-section breed-history-section">
                <h2 className="breed-section-title">{breedTitle ?? "📏 Стандарт породы"}</h2>
                <p className="breed-section-subtitle">{breedStandard ?? "Национальный клуб породы Сибирский Хаски следует официальному стандарту FCI №270. Это рабочая ездовая порода, гармонично сложенная, с умеренным костяком, лёгкой и упругой походкой, типичной для северных пород."}</p>

                <img
                  className="breed-img-center"
                  alt="Эталонный экстерьер сибирского хаски"
                  src="https://images.squarespace-cdn.com/content/v1/5e0fdcb67e94e335cab5dc5a/8a4cbc04-7b2d-4612-8d01-989f242ecb05/redwhite.jpg?format=2500w"
                />

                <div className="breed-highlight-box">
                  <p className="breed-margin"><strong>Высота в холке:</strong> кобели — 53–60 см, суки — 51–56см</p>
                  <p className="breed-margin"><strong>Вес:</strong> кобели — 20–27 кг, суки — 16–23 кг</p>
                  <p className="breed-margin"><strong>Окрас:</strong> допускаются любые окрасы от чисто белого до чёрного с отметинами</p>
                  <p style={{ margin: 0 }}><strong>Глаза:</strong> голубые, карие, янтарные или разного цвета</p>
                </div>
              </section>

              {/* Характер */}
              <section className="breed-section breed-history-section">
                <div className="breed-mission-content">
                  <h2 className="breed-section-title">🧠 Характер и особенности</h2>
                  <p className="breed-section-subtitle">{breedCharacter ?? "Сибирские хаски — дружелюбные, энергичные и умные собаки. Они не охранники, но прекрасно чувствуют себя в активной семье и команде."}</p>
                  <div className="breed-highlight-box">
                    <ul className="breed-mission-list">
                      {[
                        "Очень активны, нуждаются в ежедневной физической нагрузке",
                        "Не склонны к агрессии или застенчивости",
                        "Общительны с другими собаками и людьми",
                        "Обожают бег и могут преодолевать большие расстояния",
                      ].map((text, i) => (
                        <li key={`c-${i}`}>{text}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </section>

              {/* Уход */}
              <section className="breed-section breed-history-section">
                <h2 className="breed-section-title">{breedCareTitle ?? "✂️ Уход и груминг"}</h2>
                <p className="breed-section-subtitle">{breedCare ?? "Хаски имеют густую двойную шерсть, которая требует регулярного вычёсывания, особенно в периоды линьки."}</p>
                <div className="breed-highlight-box">
                  <ul className="breed-mission-list">
                    <li>2–3 раза в неделю расчёсывание (ежедневно во время линьки)</li>
                    <li>Не требуют частого мытья</li>
                    <li>Не стригутся — это нарушает структуру шерсти</li>
                    <li>Важно следить за когтями и ушами</li>
                  </ul>
                </div>
              </section>

              {/* Кормление */}
              <section className="breed-section breed-history-section">
                <h2 className="breed-section-title">🍽️ Кормление</h2>
                <p className="breed-section-subtitle">
                  Метаболизм у сибирских хаски «экономный», поэтому перекармливать их легко. Подходят как качественные промышленные корма, так и натуралка — при грамотном подборе.
                </p>
                <div className="breed-terms-grid">
                  {[
                    "Важно соблюдать режим кормления",
                    "Нельзя перекармливать — склонны к худобе, но при этом легко набирают «пустой» вес",
                    "Вода — всегда в свободном доступе",
                    "Для щенков, беременных и пожилых — отдельный рацион",
                  ].map((t, i) => (
                    <div className="breed-term" key={`f-${i}`}>{t}</div>
                  ))}
                </div>
              </section>

              {/* История */}
              <section className="breed-section breed-history-section">
                <h2 className="breed-section-title">{breedHistory ?? "📜 История породы"}</h2>
                <p className="breed-section-subtitle">
                  Сибирские хаски происходят от ездовых собак коренных народов Северо-Восточной Сибири. В начале XX века они были вывезены на Аляску, где проявили себя в гонках и спасательных экспедициях.
                </p>
                <p className="breed-section-subtitle">
                  Порода официально признана в США в 1930 году. С тех пор она распространилась по всему миру, сохранив рабочие качества, интеллект и красоту.
                </p>
              </section>
            </div>

            <ClubSidebar stickyTopPx={120} />
          </div>
        </div>
      </main>
    </div>
  );
}
