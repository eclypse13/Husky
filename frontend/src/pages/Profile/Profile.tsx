import { Link } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./Profile.css";

export default function Profile() {
    return (
        <div className="profile-page">
            <Breadcrumb
                title="Личный кабинет"
                items={[{ label: "Главная", to: "/" }, { label: "Личный кабинет" }]}
            />

            <main className="profile-main">
                <div className="profile-container">
                    <section className="search-section">
                        <div className="profile-two-col">
                            <div>
                                {/* Карточка профиля */}
                                <div className="stat-card">
                                    <div className="stat-icon">👤</div>

                                    <div className="stat-number">
                                        Иванов Иван Иванович
                                        <span className="profile-edit" title="Редактировать">✏️</span>
                                    </div>

                                    <div className="stat-label">@huskylover2020</div>
                                    <p className="stat-trend">г. Санкт-Петербург</p>

                                    <div className="profile-details-list">
                                        <p>
                                            Email:{" "}
                                            <a href="mailto:ivanov@example.com">ivanov@example.com</a>
                                        </p>
                                        <p>Дата рождения: 01.01.1985</p>
                                        <p>
                                            Telegram:{" "}
                                            <a href="https://t.me/ivanov" target="_blank" rel="noreferrer">
                                                @ivanov
                                            </a>
                                        </p>
                                        <p>
                                            Instagram:{" "}
                                            <a
                                                href="https://instagram.com/husky_world"
                                                target="_blank"
                                                rel="noreferrer"
                                            >
                                                @husky_world
                                            </a>
                                        </p>
                                        <p>
                                            Facebook:{" "}
                                            <a
                                                href="https://facebook.com/huskyivanov"
                                                target="_blank"
                                                rel="noreferrer"
                                            >
                                                fb.com/huskyivanov
                                            </a>
                                        </p>
                                        <p>🌟 Член НКП</p>
                                        <p>
                                            🌐 Сайт питомника:{" "}
                                            <a
                                                href="https://silversnowhuskies.ru"
                                                target="_blank"
                                                rel="noreferrer"
                                            >
                                                silversnowhuskies.ru
                                            </a>
                                        </p>
                                    </div>
                                </div>

                                {/* Быстрые ссылки */}
                                <div className="sidebar-card" style={{ marginTop: "2rem" }}>
                                    <h3 className="sidebar-title">📎 Быстрые ссылки</h3>
                                    <ul className="quick-links-ul">
                                        <li>
                                            <Link className="quick-link" to="#">
                                                🏆 Мои Чемпионы
                                            </Link>
                                        </li>
                                        <li>
                                            <Link className="quick-link" to="#">
                                                📅 Календарь мероприятий
                                            </Link>
                                        </li>
                                        <li>
                                            <Link className="quick-link" to="#">
                                                📥 Подать заявление
                                            </Link>
                                        </li>
                                        <li>
                                            <Link className="quick-link" to="#">
                                                🧬 Генетика собак
                                            </Link>
                                        </li>
                                    </ul>
                                </div>
                            </div>

                            <div>
                                <h2 className="search-title">Мои собаки</h2>

                                <div className="results-grid">
                                    <article className="dog-card">
                                        <div className="dog-avatar">🐕</div>
                                        <div className="dog-info">
                                            <h3>Arctic Storm&apos;s Thunder King</h3>
                                            <div className="dog-details">
                                                <span className="dog-detail">♂ Кобель</span>
                                                <span className="dog-detail">2020</span>
                                                <span className="dog-detail">Int Ch, Ch RKF</span>
                                            </div>
                                            <div className="dog-badges">
                                                <span className="badge badge-champion">Чемпион</span>
                                                <span className="badge badge-health">PRA Clear</span>
                                            </div>
                                        </div>
                                        <div className="dog-actions">
                                            <a className="action-button btn-primary-small" href="#">
                                                Профиль
                                            </a>
                                            <a className="action-button btn-secondary-small" href="#">
                                                Редактировать
                                            </a>
                                        </div>
                                    </article>

                                    <article className="dog-card">
                                        <div className="dog-avatar">🦮</div>
                                        <div className="dog-info">
                                            <h3>Siberian Dream&apos;s Ice Walker</h3>
                                            <div className="dog-details">
                                                <span className="dog-detail">♀ Сука</span>
                                                <span className="dog-detail">2021</span>
                                                <span className="dog-detail">Ch RKF</span>
                                            </div>
                                            <div className="dog-badges">
                                                <span className="badge badge-health">SHOR Normal</span>
                                            </div>
                                        </div>
                                        <div className="dog-actions">
                                            <a className="action-button btn-primary-small" href="#">
                                                Профиль
                                            </a>
                                            <a className="action-button btn-secondary-small" href="#">
                                                Редактировать
                                            </a>
                                        </div>
                                    </article>
                                </div>

                                <h2 className="search-title" style={{ marginTop: "3rem" }}>
                                    Породный рейтинг
                                </h2>
                                <div className="stat-card">
                                    <div className="stat-number">🏆 2024: 340 баллов</div>
                                    <div className="stat-label">1 место среди кобелей</div>
                                </div>

                                <h2 className="search-title" style={{ marginTop: "3rem" }}>
                                    Моя публичная страница
                                </h2>

                                <div className="form-group">
                                    <label className="form-label">Выберите шаблон:</label>
                                    <select className="form-input" defaultValue="classic">
                                        <option value="classic">Классический</option>
                                        <option value="gallery">Галерея</option>
                                        <option value="centered">Центрированная собака</option>
                                        <option value="text">Текстовая</option>
                                        <option value="minimal">Минимал</option>
                                    </select>
                                </div>

                                <div className="form-group">
                                    <label className="form-label">О себе:</label>
                                    <textarea className="form-input" rows={4} defaultValue="Люблю сибирских хаски и выставки..." />
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Питомник:</label>
                                    <input className="form-input" type="text" defaultValue="Silver Snow" />
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Контакты для связи:</label>
                                    <input className="form-input" type="text" defaultValue="telegram: @ivanov" />
                                </div>

                                <div style={{ textAlign: "right" }}>
                                    <button className="search-button">💾 Сохранить</button>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    );
}
