import { useEffect, useRef } from "react";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import RatingSidebar from "@/components/Sidebar/RatingSidebar";
import "./Rating.css";

export default function Rating() {
  const pageRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    const prefersReduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const els = root.querySelectorAll<HTMLElement>(
      ".rating-section, .rating-card, .rsb__card"
    );

    if (prefersReduced) {
      els.forEach((el) => el.setAttribute("data-visible", "1"));
      return;
    }

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

  return (
    <div ref={pageRef} className="rating-page">
      <Breadcrumb
        title="Породный рейтинг"
        items={[{ label: "Главная", to: "/" }, { label: "Породный рейтинг" }]}
      />

      <main className="rating-main">
        <div className="rating-container">
          <div className="rating-grid">
            <div className="rating-main-col">
              {/* Топ-Хаски */}
              <section className="rating-section rating-leaders" aria-labelledby="leaders-title">
                <h2 id="leaders-title" className="rating-title">Топ-хаски по рейтингу 2024 года</h2>

                <div className="rating-leaders-grid">
                  {[
                    {
                      img: "https://karnovandakennels.com/albumsh/girlalbums/photosRheannan/files/page203-1001-full.jpg",
                      name: "Ch. Arctic Storm's Thunder King",
                      sub: "♂ Лучший кобель",
                      pts: "💯 340 баллов",
                    },
                    {
                      img: "https://karnovandakennels.com/albumsh/boyalbums/photosRupert/files/page118-1005-full.jpg",
                      name: "Ch. Siberian Dream's Ice Walker",
                      sub: "♀ Лучшая сука",
                      pts: "💯 310 баллов",
                    },
                  ].map((d) => (
                    <article key={d.name} className="rating-card">
                      <img
                        className="rating-card-img"
                        src={d.img}
                        alt={d.name}
                        loading="lazy"
                        decoding="async"
                      />
                      <h3 className="rating-card-name">{d.name}</h3>
                      <p className="rating-card-sub">{d.sub}</p>
                      <p className="rating-card-pts">{d.pts}</p>
                      <a className="rating-btn rating-btn--primary" href="#">Родословная</a>
                    </article>
                  ))}
                </div>
              </section>

              {/* Таблица года */}
              <section className="rating-section" aria-labelledby="table-title">
                <div className="rating-head">
                  <h2 id="table-title" className="rating-title">Подробный рейтинг 2024</h2>
                  <p className="rating-sub">Собаки, участвующие в официальном рейтинге года</p>
                </div>

                <div className="rating-table-wrap" role="region" aria-label="Подробный рейтинг 2024" tabIndex={0}>
                  <table className="rating-table">
                    <caption className="sr-only">Табличный список участников и набранные баллы</caption>
                    <thead>
                      <tr>
                        <th scope="col">#</th>
                        <th scope="col">Имя</th>
                        <th scope="col">Пол</th>
                        <th scope="col">Титулы</th>
                        <th scope="col">Баллы</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        ["1", "Ch. Arctic Storm's Thunder King", "♂", "Int Ch, Ch RKF", "340"],
                        ["2", "Ch. Siberian Dream's Ice Walker", "♀", "Ch RKF", "310"],
                        ["3", "Silver Snow Aurora", "♀", "Ch", "295"],
                        ["4", "Northern Light's Aurora", "♀", "Ch", "284"],
                        ["5", "Polar Star Vanguard", "♂", "Ch", "271"],
                      ].map((r) => (
                        <tr key={r[0]}>
                          {r.map((c, i) => (
                            <td key={i}>{c}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* Архив */}
              <section className="rating-section rating-archive" aria-labelledby="archive-title">
                <h2 id="archive-title" className="rating-title">Архив породного рейтинга</h2>
                <p className="rating-sub">Найдите данные по предыдущим годам, категориям или питомникам</p>

                <form className="rating-filters" onSubmit={(e) => e.preventDefault()}>
                  <label className="sr-only" htmlFor="f-year">Год</label>
                  <select id="f-year" className="rating-select" defaultValue="">
                    <option value="" disabled>Год</option>
                    <option>2024</option><option>2023</option><option>2022</option>
                  </select>

                  <label className="sr-only" htmlFor="f-cat">Категория</label>
                  <select id="f-cat" className="rating-select" defaultValue="">
                    <option value="" disabled>Категория</option>
                    <option>Производители</option><option>Суки</option><option>Питомники</option>
                  </select>

                  <label className="sr-only" htmlFor="f-sex">Пол</label>
                  <select id="f-sex" className="rating-select" defaultValue="">
                    <option value="" disabled>Пол</option>
                    <option>♂</option><option>♀</option>
                  </select>

                  <label className="sr-only" htmlFor="f-kennel">Питомник или приставка</label>
                  <input id="f-kennel" className="rating-input" placeholder="Питомник или приставка…" />

                  <button className="rating-btn rating-btn--ghost" type="button">Скачать архив</button>
                </form>
              </section>
            </div>

            <RatingSidebar />
          </div>
        </div>
      </main>
    </div>
  );
}