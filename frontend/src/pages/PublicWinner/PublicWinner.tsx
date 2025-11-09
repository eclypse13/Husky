import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./PublicWinner.css";

export default function PublicWinner() {
  return (
    <div className="public-winner-page">
      <Breadcrumb
        title="Питомник Silver Snow"
        items={[{ label: "Главная", to: "/" }, { label: "Питомники" }]}
      />

      <main className="pw-main">
        <div className="pw-container">
          <section className="pw-card">
            <header className="pw-header">
              <h2 className="pw-title">Питомник Silver Snow — Победитель рейтинга</h2>
              <p className="pw-subtitle">
                Лучшие собаки питомника по итогам года. Итоги рейтинга и достижения —
                согласно официальным результатам клуба.
              </p>
            </header>

            <div className="pw-grid">
              {/* Левая колонка: две карточки с рейтингом */}
              <div className="pw-left">
                <article className="pw-dog-card">
                  <img
                    src="https://karnovandakennels.com/albumsh/boyalbums/photosRupert/files/page118-1005-full.jpg"
                    alt="Siberian Dream's Ice Walker"
                    className="pw-dog-img"
                  />
                  <strong className="pw-dog-name">Siberian Dream&apos;s Ice Walker</strong>
                  <span className="pw-dog-meta">
                    Blizzard ♂ × Snowflake ♀ | д.р. 12.03.2021
                  </span>
                  <span className="pw-rating-badge">Рейтинг: 310 баллов</span>
                </article>

                <article className="pw-dog-card">
                  <img
                    src="https://karnovandakennels.com/albumsh/girlalbums/photosDiDi/files/page40-1000-full.jpg"
                    alt="Silver Snow Aurora"
                    className="pw-dog-img"
                  />
                  <strong className="pw-dog-name">Silver Snow Aurora</strong>
                  <span className="pw-dog-meta">
                    Northwind ♂ × Crystal ♀ | д.р. 05.11.2019
                  </span>
                  <span className="pw-rating-badge">Рейтинг: 295 баллов</span>
                </article>
              </div>

              {/* Правая колонка: победитель года + список достижений */}
              <aside className="pw-right pw-winner">
                <h3 className="pw-winner-title">🏆 Победитель рейтинга 2024</h3>

                <article className="pw-dog-card pw-dog-card--tight">
                  <img
                    src="https://karnovandakennels.com/albumsh/girlalbums/photosRheannan/files/page203-1001-full.jpg"
                    alt="Arctic Storm's Thunder King"
                    className="pw-dog-img"
                  />
                  <strong className="pw-dog-name">Arctic Storm&apos;s Thunder King</strong>
                  <span className="pw-dog-meta">
                    Storm ♂ × Ice Queen ♀ | д.р. 20.06.2020
                  </span>
                  <span className="pw-rating-badge">Рейтинг: 340 баллов</span>
                </article>

                <ul className="pw-winner-list">
                  <li>1 место — Специализированная выставка &laquo;Сибирь 2024&raquo;</li>
                  <li>1 место — Чемпионат клуба НКП</li>
                  <li>CACIB — Международная выставка</li>
                  <li>Лучший кобель на региональном монопороднике</li>
                </ul>
              </aside>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
