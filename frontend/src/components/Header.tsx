import { Link, NavLink } from "react-router-dom";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { getDict, pickValue } from "@/lib/dict";
import "./Header.css";
import logo from "@/assets/logo.png";

export default function Header() {
  const [open, setOpen] = useState(false);
  const headerRef = useRef<HTMLElement | null>(null);
  const [h, setH] = useState(0);
  const [logoText, setLogoText] = useState<string>("НКП Сибирский Хаски");

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

  // Fetch logo text from dictionary API (deduped)
  useEffect(() => {
    let ignore = false;
    getDict()
      .then((dict) => {
        if (ignore) return;
        const v = pickValue(dict, "LOGO_TEXT", "ru");
        if (v) setLogoText(v);
      })
      .catch(() => { });
    return () => {
      ignore = true;
    };
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
            <div className="v3-logo-wrapper">
              <div className="v3-logo-backdrop"></div>
              <NavLink to="/" className="v3-logo">
                <img src={logo} alt="Логотип Национального клуба породы Сибирский Хаски" className="site-header__logo" />
              </NavLink>
            </div>
            <div className="site-header__club-info">
              <h1>{logoText}</h1>
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
