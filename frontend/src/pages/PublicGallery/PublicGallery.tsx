import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./PublicGallery.css";

export default function PublicGallery() {
  return (
    <div className="public-page">
      <Breadcrumb
        title="Питомник Silver Snow"
        items={[
          { label: "Главная", to: "/" },
          { label: "Питомники" },
        ]}
      />

      <main className="public-main">
        <div className="public-container">
          <h1 className="public-title">Silver Snow — Иванов Иван Иванович</h1>
          <p className="public-subtitle">
            Люблю сибирских хаски и участвую в выставках по всей России. Основал
            питомник Silver Snow в 2015 году.
          </p>

          <div className="public-gallery-grid">
            <article className="dog-card">
              <img
                src="https://karnovandakennels.com/albumsh/girlalbums/photosRheannan/files/page203-1001-full.jpg"
                alt="Arctic Storm's Thunder King"
              />
              <strong>Arctic Storm&apos;s Thunder King</strong>
              <span className="dog-info">
                Storm ♂ × Ice Queen ♀ | д.р. 20.06.2020
              </span>
            </article>

            <article className="dog-card">
              <img
                src="https://karnovandakennels.com/albumsh/boyalbums/photosRupert/files/page118-1005-full.jpg"
                alt="Siberian Dream's Ice Walker"
              />
              <strong>Siberian Dream&apos;s Ice Walker</strong>
              <span className="dog-info">
                Blizzard ♂ × Snowflake ♀ | д.р. 12.03.2021
              </span>
            </article>

            <article className="dog-card">
              <img
                src="https://karnovandakennels.com/albumsh/girlalbums/photosDiDi/files/page40-1000-full.jpg"
                alt="Silver Snow Aurora"
              />
              <strong>Silver Snow Aurora</strong>
              <span className="dog-info">
                Northwind ♂ × Crystal ♀ | д.р. 05.11.2019
              </span>
            </article>
          </div>

          <p className="public-contacts">
            <strong>Контакты:</strong> telegram: @ivanov | email:
            ivanov@example.com
          </p>
        </div>
      </main>
    </div>
  );
}
