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
    <section className={`breadcrumb ${className ?? ""}`}>
      <div className="breadcrumb-content">
        <nav className="breadcrumb-nav">
          {items.map((c, i) => (
            <Fragment key={`crumb-${i}-${c.label}`}>
              {c.to && i !== items.length - 1 ? (
                <Link to={c.to}>{c.label}</Link>
              ) : (
                <span>{c.label}</span>
              )}
              {i !== items.length - 1 && <span>→</span>}
            </Fragment>
          ))}
        </nav>
        <h1 className="breadcrumb-title">{title}</h1>
      </div>
    </section>
  );
}
