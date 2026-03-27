import {useEffect, useMemo, useRef, useState} from "react";
import { useParams} from "react-router-dom";
import {getDict, pickValue} from "@lib/dict";
import { useEventReportsRetrieve } from "@/generated";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./EventReport.css";



type MediaItem = string | { url: string; title?: string };

function asList<T>(value: any): T[] {
  if (Array.isArray(value)) return value;
  if (value && Array.isArray(value.results)) return value.results;
  return [];
}

function getUrl(m: MediaItem): string {
  return typeof m === "string" ? m : m?.url || "";
}

function isYoutube(url: string) {
  return /youtube\.com|youtu\.be/.test(url);
}

function youtubeEmbed(url: string) {
  try {
    const u = new URL(url);
    const v = u.searchParams.get("v");
    if (v) return `https://www.youtube.com/embed/${v}`;
    if (u.hostname.includes("youtu.be")) return `https://www.youtube.com/embed/${u.pathname.replace("/", "")}`;
  } catch {}
  return url;
}

function getFileMeta(url: string | null): string {
  if (!url) return "—";
  try {
    const u = new URL(url, window.location.origin);
    const filename = u.pathname.split("/").pop() || "";
    const extMatch = filename.match(/\.([a-z0-9]+)$/i);
    const ext = extMatch ? extMatch[1].toUpperCase() : "—";
    return `${ext}, файл`;
  } catch {
    return "Файл";
  }
}

function getFileIcon(url: string | null): string {
  if (!url) return "📄";
  const lower = url.toLowerCase();
  if (lower.endsWith(".pdf")) return "📕";
  if (lower.endsWith(".doc") || lower.endsWith(".docx") || lower.endsWith(".rtf")) return "📝";
  if (lower.endsWith(".xls") || lower.endsWith(".xlsx")) return "📊";
  if (lower.endsWith(".ppt") || lower.endsWith(".pptx")) return "📽️";
  return "📄";
}


export default function EventReportPage() {
  const pageRef = useRef<HTMLDivElement | null>(null);
  const { id } = useParams();
  const numId = Number(id);

  const { data: reportData, isLoading: loading, error: fetchError } = useEventReportsRetrieve(numId, {
    query: { enabled: !!id && !isNaN(numId) },
  });

  const report = reportData?.data ?? null;
  const err = fetchError ? String(fetchError) : null;

  const [dict, setDict] = useState<any>(null);

  useEffect(() => {
    let ignore = false;

    (async () => {
      try {
        const d = await getDict();
        if (!ignore) setDict(d);
      } catch {}
    })();

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    const root = pageRef.current;
    if (!root) return;

    if (loading) return;

    const targets = root.querySelectorAll<HTMLElement>(".events-section");
    if (!targets.length) return;

    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.setAttribute("data-visible", "1");
        }),
      { threshold: 0.12, rootMargin: "0px 0px -50px 0px" }
    );

    targets.forEach((el) => {
      el.setAttribute("data-visible", "0");
      io.observe(el);
    });

    return () => io.disconnect();
  }, [loading, report]);



  const photos = useMemo(() => asList<MediaItem>((report as any)?.photos), [report]);
  const videos = useMemo(() => asList<MediaItem>((report as any)?.videos), [report]);
  const resultsFileUrl = useMemo(() => {
    return typeof report?.results === "string" && report.results ? report.results : null;
  }, [report]);

  const paragraphs = useMemo(() => {
    const raw = (report as any)?.result_description ?? (report as any)?.result_paragraphs;
    return asList<string>(raw);
  }, [report]);


  const title = useMemo(() => {
    const key = report?.event_title_key;
    if (!key) return null;

    const fromDict = dict ? pickValue(dict, key, "ru") : null;

    return fromDict || key;
  }, [report?.event_title_key, dict]);



  if (loading) return <div className="event-report-state">Загрузка…</div>;
  if (err) return <div className="event-report-state">Ошибка: {err}</div>;
  if (!report) return <div className="event-report-state">Отчёт не найден</div>;


  return (
    <div className="event-report-page" ref={pageRef}>
      <div className="event-report-breadcrumb-wrap">
        <Breadcrumb
          title={title ?? `Отчёт #${id}`}
          items={[
            { label: "Главная", to: "/" },
            { label: "Мероприятия", to: "/events" },
            { label: "Отчёт" },
          ]}
        />
      </div>

      <main className="events-main">
        <div className="events-container">
          <div className="event-report-content">
            {resultsFileUrl && (
              <section className="events-section events-section--card">
                <h2 className="event-report-section-title">📄 Документ отчёта</h2>

                <a
                  href={resultsFileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="event-report-doc"
                >
                  <div className="event-report-doc-icon">{getFileIcon(resultsFileUrl)}</div>
                  <div className="event-report-doc-body">
                    <div className="event-report-doc-title">Результаты</div>
                    <div className="event-report-doc-sub">{getFileMeta(resultsFileUrl)}</div>
                  </div>
                </a>
              </section>
            )}

            {photos.length > 0 && (
              <section className="events-section events-section--card">
                <h2 className="event-report-section-title">Фото</h2>

                <div className="event-report-photos">
                  {photos.map((p, idx) => {
                    const url = getUrl(p);
                    if (!url) return null;
                    return (
                      <a key={idx} href={url} target="_blank" rel="noreferrer" className="event-report-photoLink">
                        <img src={url} alt="" className="event-report-photo" />
                      </a>
                    );
                  })}
                </div>
              </section>
            )}

            {videos.length > 0 && (
              <section className="events-section events-section--card">
                <h2 className="event-report-section-title">Видео</h2>

                <div className="event-report-videos">
                  {videos.map((v, idx) => {
                    const url = getUrl(v);
                    if (!url) return null;

                    return (
                      <div className="event-report-videoBox" key={idx}>
                        {isYoutube(url) ? (
                          <iframe
                            src={youtubeEmbed(url)}
                            title={`video-${idx}`}
                            className="event-report-video"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                          />
                        ) : (
                          <video
                            controls
                            src={url}
                            className="event-report-video event-report-video--file"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {paragraphs.length > 0 && (
              <section className="events-section events-section--card">
                <h2 className="event-report-section-title">🧾 Содержание</h2>

                <div className="event-report-paragraphs">
                  {paragraphs.map((p, idx) => (
                    <p key={idx} className="event-report-paragraph">
                      {p}
                    </p>
                  ))}
                </div>
              </section>
            )}

          </div>
        </div>
      </main>
    </div>
  );

}
