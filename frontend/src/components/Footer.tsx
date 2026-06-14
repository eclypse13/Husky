import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { getDict, pickValue } from "@/lib/dict";
import "./Footer.css";

export default function Footer() {
  const [footerName, setFooterName] = useState<string>("НКП Сибирский Хаски");
  const [footerEmail, setFooterEmail] = useState<string>("info@example.org");

  useEffect(() => {
    let ignore = false;
    getDict()
      .then((dict) => {
        if (ignore) return;
        const name = pickValue(dict, "FOOTER_FULL_NAME", "ru");
        const email = pickValue(dict, "FOOTER_EMAIL", "ru");
        if (name) setFooterName(name);
        if (email) setFooterEmail(email);
      })
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, []);
  return (
    <footer className="site-footer">
      <div className="site-footer__content">

        <div className="site-footer__section">
          <h3>{footerName}</h3>
          <p style={{ color: "rgba(255,255,255,.8)", marginBottom: "1.5rem", lineHeight: 1.6 }}>
            Ведущая организация России по развитию и сохранению породы сибирский хаски.
            Объединяем профессионалов и любителей породы по всей стране.
          </p>
          <div style={{ display: "flex", gap: "1rem" }}>
            <a href={`mailto:${footerEmail}`} style={{ color: "rgba(255,255,255,.8)", fontSize: "1.5rem" }}>📧</a>
            <a href="#" style={{ color: "rgba(255,255,255,.8)", fontSize: "1.5rem" }}>📱</a>
            <a href="#" style={{ color: "rgba(255,255,255,.8)", fontSize: "1.5rem" }}>🌐</a>
          </div>
        </div>

        <div className="site-footer__section">
          <h3>Архив и данные</h3>
          <ul className="site-footer__list">
            <li><Link to="/archive">Поиск собак</Link></li>
            <li><Link to="/archive">Родословные</Link></li>
            <li><Link to="/health">Здоровье породы</Link></li>
            <li><Link to="/stats">Статистика</Link></li>
            <li><Link to="/rating">Рейтинги</Link></li>
          </ul>
        </div>

        <div className="site-footer__section">
          <h3>Мероприятия</h3>
          <ul className="site-footer__list">
            <li><Link to="/events">Календарь выставок</Link></li>
            <li><Link to="/events/sport">Ездовой спорт</Link></li>
            <li><Link to="/events/seminars">Семинары</Link></li>
            <li><Link to="/events/results">Результаты</Link></li>
            <li><Link to="/events/reports">Фотоотчеты</Link></li>
          </ul>
        </div>

        <div className="site-footer__section">
          <h3>Сообщество</h3>
          <ul className="site-footer__list">
            <li><Link to="/join">Членство в клубе</Link></li>
            <li><Link to="/kennels">Питомники-партнеры</Link></li>
            <li><Link to="/forum">Форум заводчиков</Link></li>
            <li><Link to="/help">Помощь новичкам</Link></li>
            <li><Link to="/contact">Контакты</Link></li>
          </ul>
        </div>

      </div>

      <div className="site-footer__bottom">
        <p>&copy; 2025 НКП Сибирский Хаски. Все права защищены. Интеграция с breedarchive.com</p>
      </div>
    </footer>
  );
}
