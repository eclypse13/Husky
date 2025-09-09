import { Link, NavLink } from "react-router-dom";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import "./Header.css";

export default function Header() {
  const [open, setOpen] = useState(false);
  const headerRef = useRef<HTMLElement | null>(null);
  const [h, setH] = useState(0);

  useLayoutEffect(() => {
    const measure = () => setH(headerRef.current?.offsetHeight ?? 0);
    measure();
    const ro = new ResizeObserver(measure);
    if (headerRef.current) ro.observe(headerRef.current);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  useEffect(() => {
    document.documentElement.style.setProperty("--header-h", `${h}px`);
  }, [h]);

  useEffect(() => {
    const onScroll = () => {
      const el = headerRef.current;
      if (!el) return;
      if (window.scrollY > 100) el.classList.add("scrolled");
      else el.classList.remove("scrolled");
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth > 1210) setOpen(false);
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return (
    <>
      <header
        className={`site-header${open ? " is-open" : ""}`}
        id="header"
        ref={headerRef}
      >
        <div className="site-header__content">
          <div className="site-header__logo-section">
            <div className="site-header__logo" aria-hidden>🐺</div>
            <div className="site-header__club-info">
              <h1>НКП Сибирский Хаски</h1>
              <p className="site-header__club-subtitle">Национальный клуб породы</p>
            </div>
          </div>

          {/* Burger */}
          <button
            className="site-header__burger"
            aria-label={open ? "Закрыть меню" : "Открыть меню"}
            aria-expanded={open}
            onClick={() => setOpen(v => !v)}
          >
            <span /><span /><span />
          </button>

          <nav aria-label="Главное меню" onClick={() => setOpen(false)}>
            <ul className="site-header__nav-menu">
              <li><NavLink to="/about" className="site-header__nav-link">О клубе</NavLink></li>
              <li><NavLink to="/breed" className="site-header__nav-link">О породе</NavLink></li>
              <li><NavLink to="/events" className="site-header__nav-link">Мероприятия</NavLink></li>
              <li><NavLink to="/archive" className="site-header__nav-link">Архив</NavLink></li>
              <li><Link to="/join" className="site-header__cta-button">Стать членом</Link></li>
            </ul>
          </nav>

          <div className="site-header__backdrop" onClick={() => setOpen(false)} />
        </div>
      </header>

      <div className="site-header__spacer" style={{ height: h }} aria-hidden />
    </>
  );
}
