import { Link } from "react-router-dom";
import { useEffect, useRef, useState, type MouseEvent } from "react";
import { useEffect, useMemo, useRef, useState, MouseEvent} from "react";
import { getDict, pickValue } from "@/lib/dict";
import { useClubDocumentsList } from "@/generated/club-documents/club-documents";
import "./ClubSidebar.css";

type DocumentType = 'charter' | 'standard' | 'form' | 'regulation';
const DOCUMENT_TYPE_ORDER: DocumentType[] = [
  'charter',
  'standard',
  'form',
  'regulation',
];

const CACHE_KEY = "club-documents-v1";
const CACHE_EXPIRY_MS = 30 * 60 * 1000; // 30 минут

export type Doc = { id: string; icon: string; title: string; sub?: string; to?: string; documentType?: DocumentType; order?: number;};
export type Stat = { id: string; value: string; label: string };
export type Action = { id: string; label: string; to: string; kind?: "primary" | "info" | "neutral" };

type Props = {
  stats?: Stat[];
  actions?: Action[];
  stickyTopPx?: number;
};

const formatFileSize = (bytes?: number | null) => {
  if (!bytes || bytes <= 0) return '';
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} КБ`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
};

const formatStatValue = (value: number | null | undefined) => {
  if (value == null) return "0+";

  // форматируем с пробелами: 15000 → 15 000
  const formatted = value.toLocaleString("ru-RU");

  return `${formatted}+`;
};

const defaultStats: Stat[] = [
  { id: "s1", value: "1,250+", label: "Членов" },
  { id: "s2", value: "350+", label: "Питомников" },
  { id: "s3", value: "15,000+", label: "Собак в архиве" },
  { id: "s4", value: "85", label: "Регионов" },
];

const defaultActions: Action[] = [
  { id: "a1", label: "Подать заявление", to: "/join", kind: "primary" },
  { id: "a2", label: "Задать вопрос", to: "/contact", kind: "info" },
  { id: "a3", label: "Календарь мероприятий", to: "/events", kind: "neutral" },
];

const getIconByType = (type: string): string => {
  switch (type) {
    case "standard": return "📐";
    case "charter": return "📋";
    case "regulation": return "📜";
    case "exhibition": return "🏆";
    case "form": return "📝";
    case "payment": return "💰";
    default: return "📄";
  }
};

const getFileMeta = (url: string | null, sizeBytes?: number | null, fallbackDesc?: string): string => {
  if (!url) return fallbackDesc || "–";
  try {
    const u = new URL(url, window.location.origin);
    const path = u.pathname;
    const parts = path.split('/');
    const filename = parts[parts.length - 1];
    const extMatch = filename.match(/\.([a-z0-9]+)$/i);
    const ext = extMatch ? extMatch[1].toUpperCase() : "–";
    const size = formatFileSize(sizeBytes);
    return size ? `${ext}, ${size}` : `${ext},  файл`;
  } catch {
    return fallbackDesc || "Файл";
  }
};

export default function ClubSidebar({
  stats = defaultStats,
  actions = defaultActions,
  stickyTopPx = 120,
}: Props) {
  const sidebarRef = useRef<HTMLDivElement>(null);
  const [isSticky, setIsSticky] = useState(false);
  const [docsState, setDocsState] = useState<Doc[]>([]);
  const [statsState, setStatsState] = useState<Stat[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isDocModalOpen, setIsDocModalOpen] = useState(false);
  const [currentDoc, setCurrentDoc] = useState<{
    title: string;
    url: string;
    size?: string;
    icon: string;
  } | null>(null);
  const [isDocLoading, setIsDocLoading] = useState(false);

  const openDocumentModal = (e: MouseEvent<HTMLAnchorElement>, doc: Doc) => {
    e.preventDefault();
    e.stopPropagation();

    const url = doc.to && doc.to !== "#" ? doc.to : "";
    if (!url) return;

    setCurrentDoc({
      title: doc.title,
      url,
      size: doc.sub,
      icon: doc.icon,
    });

    setIsDocLoading(true);
    setIsDocModalOpen(true);
  };


  const closeDocumentModal = () => {
    setIsDocModalOpen(false);
    setIsDocLoading(false);
    setCurrentDoc(null);
    document.body.style.overflow = "auto";
  };

  const downloadDocument = () => {
    if (!currentDoc?.url) return;
    const link = document.createElement("a");
    link.href = currentDoc.url;
    link.download = currentDoc.url.split("/").pop() || "document";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };


  // Скролл-логика — без изменений
  useEffect(() => {
    const handleScroll = () => {
      if (sidebarRef.current) {
        const sidebarRect = sidebarRef.current.getBoundingClientRect();
        const shouldSticky = sidebarRect.top <= stickyTopPx;
        if (shouldSticky !== isSticky) {
          setIsSticky(shouldSticky);
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isSticky, stickyTopPx]);


  // UI effects + document modal behavior (React version of the inline <script>)
  useEffect(() => {
    const onScrollHeader = () => {
      const header = document.getElementById("header");
      if (!header) return;
      if (window.scrollY > 100) header.classList.add("scrolled");
      else header.classList.remove("scrolled");
    };

    const onScrollParallax = () => {
      const scrolled = window.pageYOffset;
      document.querySelectorAll<HTMLElement>(".shape").forEach((shape, i) => {
        const speed = 0.3 + i * 0.1;
        shape.style.transform = `translateY(${scrolled * speed}px)`;
      });
    };

    // Intersection Observer for animations
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const el = entry.target as HTMLElement;
            el.style.opacity = "1";
            el.style.transform = "translateY(0)";
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );

    // Observe elements for animation
    document
      .querySelectorAll<HTMLElement>(
        ".history-section, .mission-section, .leadership-section, .membership-section, .contact-section, .sidebar-card"
      )
      .forEach((el) => {
        el.style.opacity = "0";
        el.style.transform = "translateY(30px)";
        el.style.transition = "opacity 0.6s ease, transform 0.6s ease";
        observer.observe(el);
      });

    // Close modal on ESC
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isDocModalOpen) {
        closeDocumentModal();
      }
    };

    window.addEventListener("scroll", onScrollHeader);
    window.addEventListener("scroll", onScrollParallax);
    document.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("scroll", onScrollHeader);
      window.removeEventListener("scroll", onScrollParallax);
      document.removeEventListener("keydown", onKeyDown);
      observer.disconnect();
    };
  }, [isDocModalOpen]);



  // Load documents via generated hook + dict for title translations
  const { data: docsApiData, isLoading: docsLoading, error: docsError } = useClubDocumentsList();
  const [dict, setDict] = useState<any>(null);

  useEffect(() => {
    let ignore = false;
    getDict().then((d) => { if (!ignore) setDict(d); }).catch(() => {});
    return () => { ignore = true; };
  }, []);

  useEffect(() => {
    if (!docsApiData || !dict) return;
    const results: any[] = docsApiData?.data?.results ?? [];
    const mappedDocs: Doc[] = results.map((entry) => ({
      id: String(entry.id),
      icon: getIconByType(entry.document_type),
      title: entry.title_key
        ? pickValue(dict, entry.title_key, "ru") || entry.title_key
        : "Без названия",
      sub: getFileMeta(entry.file, entry.file_size, entry.description_key),
      to: entry.file ?? "#",
      documentType: entry.document_type ?? 'regular',
      order:
        typeof entry.order === 'number' ? entry.order
        : typeof entry.sort_order === 'number' ? entry.sort_order
        : typeof entry.position === 'number' ? entry.position
        : undefined,
    }));
    setDocsState(mappedDocs);
    setLoading(false);
  }, [docsApiData, dict]);

  useEffect(() => {
    if (docsLoading) { setLoading(true); setError(null); }
    if (docsError) { setError(docsError instanceof Error ? docsError.message : "Ошибка загрузки"); setLoading(false); }
  }, [docsLoading, docsError]);

  useEffect(() => {
    let ignore = false;

    const loadStats = async () => {
      try {
        const res = await fetch("/api/club/stats/");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // ожидаем объект вида:
        // { members_count, kennels_count, dogs_in_archive_count, regions_count }
        const mapped: Stat[] = [
          { id: "s1", value: String(data.members_count ?? 0), label: "Владельцев сибирских хаски" },
          { id: "s2", value: String(data.kennels_count ?? 0), label: "Питомников" },
          { id: "s3", value: String(data.dogs_in_archive_count ?? 0), label: "Собак в архиве" },
          { id: "s4", value: String(data.regions_count ?? 0), label: "Регионов" },
        ];

        if (!ignore) setStatsState(mapped);
      } catch (e) {
        // если API недоступен — просто остаёмся на defaultStats
        if (!ignore) setStatsState(null);
      }
    };

    loadStats();
    return () => {
      ignore = true;
    };
  }, []);


  const sortedDocs = [...docsState].sort((a, b) => {
    // 1. по типу документа
    const typeA = DOCUMENT_TYPE_ORDER.indexOf(a.documentType ?? 'regular');
    const typeB = DOCUMENT_TYPE_ORDER.indexOf(b.documentType ?? 'regular');

    if (typeA !== typeB) {
      return typeA - typeB;
    }

    // 2. внутри типа — по order
    if (a.order != null && b.order != null) {
      return a.order - b.order;
    }

    if (a.order != null) return -1;
    if (b.order != null) return 1;

    // 3. запасной вариант — по названию
    return a.title.localeCompare(b.title);
  });

  const shownStats = statsState ?? stats; // stats всё ещё может прийти пропсом (и дефолтится defaultStats)



  return (
    <aside className="club-sidebar" ref={sidebarRef}>
      <div className="club-sidebar__container">
        <div className="club-sidebar__empty"></div>
        <div
          className={`club-sidebar__sticky ${isSticky ? 'club-sidebar__sticky--fixed' : ''}`}
        >
          <div className="club-sidebar__card sidebar-card">
            <h3 className="club-sidebar__title">📄 Документы клуба</h3>
            <div className="club-sidQebar__documents">
              {loading ? (
                <div className="club-sidebar__document-placeholder">Загрузка…</div>
              ) : error ? (
                <div className="club-sidebar__document-error">❌ {error}</div>
              ) : docsState.length === 0 ? (
                <div className="club-sidebar__document-empty">Нет документов</div>
              ) : (
                sortedDocs.map((d, index) => {
                  const prevType = sortedDocs[index - 1]?.documentType;
                  const showDivider = index > 0 && prevType !== d.documentType;

                  return (
                    <div key={d.id}>
                      {showDivider && (
                        <div className="club-sidebar__document-divider" />
                      )}

                      <Link
                        to={d.to ?? "#"}
                        onClick={(e) => openDocumentModal(e, d)}
                        className="club-sidebar__document"
                      >
                        <div className="club-sidebar__document-icon">{d.icon}</div>
                        <div>
                          <div className="club-sidebar__document-title">{d.title}</div>
                          {d.sub && <div className="club-sidebar__document-sub">{d.sub}</div>}
                        </div>
                      </Link>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="club-sidebar__card sidebar-card">
            <h3 className="club-sidebar__title">📊 Статистика клуба</h3>
            <div className="club-sidebar__stats">
              {shownStats.map((s) => (
                <div className="club-sidebar__stat" key={s.id}>
                  <div className="club-sidebar__stat-number">{s.value}</div>
                  <div className="club-sidebar__stat-label">{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="club-sidebar__card sidebar-card">
            <h3 className="club-sidebar__title">🚀 Быстрые действия</h3>
            <div className="club-sidebar__quick">
              {actions.map((a) => (
                <Link
                  key={a.id}
                  to={a.to}
                  className={
                    "club-sidebar__qa " +
                    (a.kind === "info"
                      ? "club-sidebar__qa--info"
                      : a.kind === "neutral"
                        ? "club-sidebar__qa--neutral"
                        : "club-sidebar__qa--primary")
                  }
                >
                  {a.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
      {isDocModalOpen && currentDoc && (
        <div
          id="documentModal"
          className="modal-overlay active"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeDocumentModal();
          }}
        >
          <div className="modal-container" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <div className="modal-icon" id="modalIcon">{currentDoc.icon}</div>
                <span id="modalDocTitle">{currentDoc.title}</span>
              </div>

              <div className="modal-actions">
                <button className="modal-button" type="button" onClick={downloadDocument}>
                  <span>⬇️</span>
                  <span>Скачать</span>
                </button>
                <button className="modal-close" type="button" onClick={closeDocumentModal}>✕</button>
              </div>
            </div>

            <div className="modal-body">
              {isDocLoading && <div className="loading-spinner" id="loadingSpinner" />}
              <iframe
                id="documentFrame"
                className="document-preview"
                title={currentDoc.title}
                src={
                  currentDoc.url.toLowerCase().endsWith(".pdf")
                    ? `${currentDoc.url}#view=FitH`
                    : currentDoc.url
                }
                onLoad={() => setIsDocLoading(false)}
              />
            </div>

            <div className="modal-footer">
              <div className="document-info">
                <span>Размер файла:</span>
                <span className="file-size" id="modalDocSize">{currentDoc.size}</span>
              </div>

              <div className="modal-hint">
                Используйте колесико мыши или жесты для навигации по документу
              </div>
            </div>
          </div>
        </div>
      )}


    </aside>
  );
}