import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {getDict, pickValue} from "@lib/dict";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";


type MediaItem = string | { url: string; title?: string };

type EventReport = {
  id: number | string;
  event: number | string;
  event_title_key?: string | null;
  event_starts_at?: string | null;
  photos?: MediaItem[];
  videos?: MediaItem[];
  results?: any[];
  created_at?: string;
};

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
  // простая обработка: берём v= или последний сегмент youtu.be
  try {
    const u = new URL(url);
    const v = u.searchParams.get("v");
    if (v) return `https://www.youtube.com/embed/${v}`;
    if (u.hostname.includes("youtu.be")) return `https://www.youtube.com/embed/${u.pathname.replace("/", "")}`;
  } catch {}
  return url;
}

export default function EventReportPage() {
  const { id } = useParams();
  const [report, setReport] = useState<EventReport | null>(null);
  const [dict, setDict] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function load() {
      setLoading(true);
      setErr(null);
      try {

        const res = await fetch(`/api/event-reports/${id}/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!ignore) setReport(data);
      } catch (e: any) {
        if (!ignore) setErr(e?.message || "Ошибка загрузки");
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    if (id) load();
    return () => {
      ignore = true;
    };
  }, [id]);

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


  const photos = useMemo(() => asList<MediaItem>(report?.photos), [report]);
  const videos = useMemo(() => asList<MediaItem>(report?.videos), [report]);
  const results = useMemo(() => asList<any>(report?.results), [report]);

  const title = useMemo(() => {
    const key = report?.event_title_key;
    if (!key) return null;

    const fromDict = dict ? pickValue(dict, key, "ru") : null;

    // если ключ уже “человеческий текст”, как в примере "Test Event"
    return fromDict || key;
  }, [report?.event_title_key, dict]);



  if (loading) return <div style={{ padding: 24 }}>Загрузка…</div>;
  if (err) return <div style={{ padding: 24 }}>Ошибка: {err}</div>;
  if (!report) return <div style={{ padding: 24 }}>Отчёт не найден</div>;

  return (
      <div>

        <div>
          <Breadcrumb
            title={title ?? `Отчёт #${id}`}
            items={[
              { label: "Главная", to: "/" },
              { label: "Мероприятия", to: "/events" },
              { label: "Отчёт" },
            ]}
          />
        </div>

        <div style={{ maxWidth: 1200, margin: "0 auto", padding: 24 }}>



      {photos.length > 0 && (
        <>
          <h2>Фото</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
            {photos.map((p, idx) => {
              const url = getUrl(p);
              if (!url) return null;
              return (
                <a key={idx} href={url} target="_blank" rel="noreferrer">
                  <img
                    src={url}
                    alt=""
                    style={{ width: "100%", height: 160, objectFit: "cover", borderRadius: 12 }}
                  />
                </a>
              );
            })}
          </div>
        </>
      )}

      {videos.length > 0 && (
        <>
          <h2 style={{ marginTop: 24 }}>Видео</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 12 }}>
            {videos.map((v, idx) => {
              const url = getUrl(v);
              if (!url) return null;

              return isYoutube(url) ? (
                <iframe
                  key={idx}
                  src={youtubeEmbed(url)}
                  title={`video-${idx}`}
                  style={{ width: "100%", aspectRatio: "16/9", border: 0, borderRadius: 12 }}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              ) : (
                <video
                  key={idx}
                  controls
                  src={url}
                  style={{ width: "100%", borderRadius: 12 }}
                />
              );
            })}
          </div>
        </>
      )}

      {results.length > 0 && (
        <>
          <h2 style={{ marginTop: 24 }}>Результаты</h2>
          <ul>
            {results.map((r, idx) => (
              <li key={idx}>
                {typeof r === "string" ? r : JSON.stringify(r)}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
      </div>
  );
}
