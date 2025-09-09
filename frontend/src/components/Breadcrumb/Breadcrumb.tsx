import { Fragment } from "react";
import { Link } from "react-router-dom";
import "./Breadcrumb.css";

export type Crumb = { label: string; to?: string };

type Props = {
  title: string;
  items: Crumb[];
  className?: string;
};

export default function Breadcrumb({ title, items, className }: Props) {
  return (
    <section className={`page-breadcrumb ${className ?? ""}`}>
      <div className="page-breadcrumb__content">
        <nav className="page-breadcrumb__nav" aria-label="Хлебные крошки">
          {items.map((c, i) => {
            const isLast = i === items.length - 1;
            return (
              <Fragment key={`crumb-${i}-${c.label}`}>
                {c.to && !isLast ? (
                  <Link to={c.to} className="page-breadcrumb__link">{c.label}</Link>
                ) : (
                  <span
                    className="page-breadcrumb__current"
                    aria-current={isLast ? "page" : undefined}
                  >
                    {c.label}
                  </span>
                )}
                {!isLast && <span className="page-breadcrumb__sep">→</span>}
              </Fragment>
            );
          })}
        </nav>
        <h1 className="page-breadcrumb__title">{title}</h1>
      </div>
    </section>
  );
}
