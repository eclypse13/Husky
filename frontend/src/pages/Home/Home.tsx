import { Link } from "react-router-dom";
import { useEffect, useMemo, useState, useRef } from "react";
import { getDict, pickValue } from "@/lib/dict";
import "./Home.css";
import * as d3 from "d3";

const news = [
  { id: 1, tag: "Выставки", date: "18 июля 2025", title: "«Сибирская красота 2025» — рекордное участие", excerpt: "В Москве прошла крупнейшая специализированная выставка с участием более 200 собак из 15 стран.", featured: true, link: "Читать полный отчет", icon: "🏆", to: "/news/1" },
  { id: 2, tag: "Здоровье", date: "15 июля 2025", title: "Новые генетические тесты", excerpt: "Расширена панель доступных тестов для породы...", link: "Подробнее", icon: "🧬", to: "/news/2" },
  { id: 3, tag: "Спорт", date: "12 июля 2025", title: "Чемпионат по драйленду", excerpt: "Старт летнего сезона ездового спорта...", link: "Результаты", icon: "❄️", to: "/news/3" },
  { id: 4, tag: "Образование", date: "10 июля 2025", title: "Семинар для судей", excerpt: "Обучающий семинар по породе...", link: "Регистрация", icon: "🎓", to: "/news/4" },
  { id: 5, tag: "Достижения", date: "8 июля 2025", title: "Новые чемпионы", excerpt: "Поздравляем владельцев собак...", link: "Список", icon: "🌟", to: "/news/5" },
];

const puppies = [
  { id: "p1", icon: "🐶", name: "Arctic Jewel", sex: "♀", dob: "20.06.2025", sire: "Storm ♂", dam: "Ice Queen ♀" },
  { id: "p2", icon: "🐕", name: "Northern Fire", sex: "♂", dob: "22.06.2025", sire: "Blaze ♂", dam: "Aurora ♀" },
  { id: "p3", icon: "🐾", name: "Blue Snowflake", sex: "♀", dob: "18.06.2025", sire: "Polar ♂", dam: "Elsa ♀" },
];


type HomeNewsItem = {
  id: string; tag: string; date: string; title: string;
  excerpt: string; link: string; icon: string; to: string;
};

type HeroDog = {
  id: number;
  display_name: string;
  photo_url: string | null;
  prefix_titles: string | null;
  suffix_titles: string | null;
  year_of_birth: number | null;
  color: string | null;
};

const homeNewsDateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric", month: "long", year: "numeric",
});

function formatNewsDate(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return homeNewsDateFormatter.format(d);
}

function capitalizeTag(tag: string): string {
  if (!tag) return tag;
  const trimmed = tag.trim();
  if (!trimmed) return trimmed;
  return `${trimmed[0].toLocaleUpperCase("ru-RU")}${trimmed.slice(1)}`;
}

/* UTILS */
function useCounter(target: number, duration = 1600) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    let start: number | null = null;
    const step = (ts: number) => {
      if (start === null) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setValue(Math.floor(target * p));
      if (p < 1) requestAnimationFrame(step);
    };
    const id = requestAnimationFrame(step);
    return () => cancelAnimationFrame(id);
  }, [target, duration]);
  return value;
}

function StatCard({ label, value, plus }: { label: string; value: number; plus?: boolean }) {
  const n = useCounter(value);
  return (
    <div className="home-stat-item">
      <div className="home-stat-number">{n}{plus ? "+" : ""}</div>
      <div className="home-stat-label">{label}</div>
    </div>
  );
}

function NewsCard({ item, featured }: { item: (typeof news)[number] | HomeNewsItem; featured?: boolean }) {
  return (
    <article className={`home-news-card ${featured ? "home-featured" : ""}`}>
      <div className="home-news-image">{item.icon}</div>
      <div className="home-news-inner">
        <div className="home-news-meta">
          <span className="home-news-tag">{capitalizeTag(item.tag)}</span>
          <span className="home-news-date">{item.date}</span>
        </div>
        <h3 className="home-news-title">{item.title}</h3>
        <p className="home-news-excerpt">{item.excerpt}</p>
        <Link to={item.to} className="home-feature-link">{item.link} →</Link>
      </div>
    </article>
  );
}

type Activity = {
  id: string;
  icon: string;
  text: string;
  time: string;
};

const fallbackActivity: Activity[] = [
  { id: "1", icon: "📊", text: "Статистика здоровья породы обновлена", time: "11 часа назад" },
  { id: "2", icon: "📊", text: "Статистика здоровья породы обновлена", time: "10 часа назад" },
  { id: "3", icon: "📊", text: "Статистика здоровья породы обновлена", time: "18 часа назад" },
  { id: "4", icon: "🌟", text: "Новый член клуба: питомник «Aurora Borealis»", time: "12 часов назад" },
];

function plural(n: number, one: string, few: string, many: string) {
  const mod100 = n % 100;
  const mod10 = n % 10;

  if (mod100 >= 11 && mod100 <= 14) return many;
  if (mod10 === 1) return one;
  if (mod10 >= 2 && mod10 <= 4) return few;
  return many;
}

function formatTimeAgo(value: string): string {
  if (!value) return "";

  if (value === "только что" || value.includes("назад")) {
    return value;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 1000 / 60);

  if (diffMinutes < 1) {
    return "только что";
  }

  if (diffMinutes < 60) {
    return `${diffMinutes} ${plural(diffMinutes, "минуту", "минуты", "минут")} назад`;
  }

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours} ${plural(diffHours, "час", "часа", "часов")} назад`;
  }

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) {
    return `${diffDays} ${plural(diffDays, "день", "дня", "дней")} назад`;
  }

  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths < 12) {
    return `${diffMonths} ${plural(diffMonths, "месяц", "месяца", "месяцев")} назад`;
  }

  const diffYears = Math.floor(diffMonths / 12);
  return `${diffYears} ${plural(diffYears, "год", "года", "лет")} назад`;
}

function ActivityFeed() {
  const [items, setItems] = useState<Activity[]>(fallbackActivity);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let ignore = false;

    const loadActivity = async () => {
      try {
        const res = await fetch("/api/activity-feed/");
        if (!res.ok) throw new Error("Ошибка загрузки activity feed");

        const payload = await res.json();
        if (ignore) return;

        const results = Array.isArray(payload?.results)
          ? payload.results
          : Array.isArray(payload)
          ? payload
          : [];

        const mapped: Activity[] = results
          .map((entry: any, index: number) => {
            const text =
              typeof entry.text === "string"
                ? entry.text
                : typeof entry.message === "string"
                ? entry.message
                : "";

            if (!text.trim()) return null;

            return {
              id: String(entry.id ?? index),
              icon: typeof entry.icon === "string" ? entry.icon : "📢",
              text,
              time: formatTimeAgo(
                typeof entry.time_ago === "string"
                  ? entry.time_ago
                  : typeof entry.time === "string"
                  ? entry.time
                  : ""
              ),
            };
          })
          .filter((item: Activity | null): item is Activity => Boolean(item));

        if (!ignore && mapped.length) {
          setItems(mapped.slice(0, 10));
        }
      } catch {
        if (!ignore) {
          setItems(fallbackActivity);
        }
      } finally {
        if (!ignore) setLoading(false);
      }
    };

    loadActivity();

    const intervalId = setInterval(loadActivity, 60000); // обновление раз в минуту
    return () => {
      ignore = true;
      clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    const nodes = document.querySelectorAll<HTMLElement>(".home-page .home-activity-item");
    nodes.forEach((el, i) => {
      requestAnimationFrame(() => {
        setTimeout(() => el.classList.add("home-activity-item--visible"), i * 120);
      });
    });
  }, [items]);

  return (
    <div className="home-activity-feed">
      {items.map((a) => (
        <div key={a.id} className="home-activity-item">
          <div className="home-activity-avatar">{a.icon}</div>
          <div className="home-activity-text">
            <strong className="home-activity-message">{a.text}</strong>
            <div className="home-activity-time">{a.time}</div>
          </div>
        </div>
      ))}

      <div className="home-typing-indicator" style={{ marginTop: ".5rem" }}>
        <div className="home-typing-dot" />
        <div className="home-typing-dot" />
        <div className="home-typing-dot" />
        <span>{loading ? "Загрузка обновлений…" : "Обновления поступают…"}</span>
      </div>
    </div>
  );
}

// ---------- Код из ветки feature/add-coi-fix-pedigree-add-dna-logic ----------
const PLACEHOLDER_URLS = ["https://zooportal.pro/images/logo1.png"];
const DEFAULT_DOG_IMG = "/no-image-dog.png";
const dogPhoto = (url: string | null | undefined): string =>
  url && !PLACEHOLDER_URLS.includes(url) ? url : DEFAULT_DOG_IMG;

// ---------- Код из ветки dev (компонент карты) ----------
type KennelItem = {
  name_rus?: string;
  FCIname?: string;
  FCInumber?: string;
  breederName?: string;
  website?: string;
  vkGroup?: string;
  telegramGroup?: string;
  email?: string;
  phone?: string;
  location?: string;
  displayLocation?: string;
  coords?: [number, number];
  isMember?: boolean;
};

type KennelsData = Record<string, KennelItem[]>;

type CityStats = Record<
  string,
  {
    count: number;
    members: number;
    coords: [number, number];
    kennels: KennelItem[];
  }
>;

type CityEntry = [string, CityStats[string]];

const cityCoordinates: Record<string, [number, number]> = {
  "Алтайский край": [83.769948, 52.693224],
  "Анапа": [37.316425, 44.894603],
  "Апшеронск": [39.415171, 44.46477],
  "Архангельск": [40.515762, 64.539911],
  "Барнаул": [83.769948, 53.347996],
  "Брянск": [34.363881, 53.2434],
  "Владивосток": [131.885485, 43.115536],
  "Владимир": [40.396805, 56.129057],
  "Волгоград": [44.501846, 48.707103],
  "Воронеж": [39.200269, 51.660781],
  "Горно-Алтайск": [85.957192, 51.95811],
  "Дмитров": [37.521744, 56.346932],
  "Дмитровский округ": [37.521744, 56.346932],
  "Домодедово": [37.761039, 55.436896],
  "Екатеринбург": [60.598296, 56.838011],
  "Зеленоград": [37.181363, 55.9825],
  "Ижевск": [53.204843, 56.852775],
  "Йошкар-Ола": [47.890781, 56.634019],
  "Казань": [49.106414, 55.796127],
  "Калужская область": [36.261155, 54.513845],
  "Карелия": [33.492076, 63.15587],
  "Кемерово": [86.087314, 55.354968],
  "Киров": [49.668014, 58.603532],
  "Клин": [36.733333, 56.333333],
  "Кострома": [40.926858, 57.767683],
  "Краснодар": [38.975313, 45.035566],
  "Красноярск": [92.893247, 56.010563],
  "Липецк": [39.57006, 52.60882],
  "Ленинградская область": [31.033333, 59.95],
  "Люберцы": [37.893222, 55.678457],
  "Малоярославец": [36.463276, 55.011807],
  "Можайск": [36.027279, 55.507577],
  "Москва": [37.617298, 55.755819],
  "Московская область": [37.617298, 55.755819],
  "Нижний Новгород": [44.00209, 56.326887],
  "Новороссийск": [37.777977, 44.723489],
  "Новосибирск": [82.93544, 55.030204],
  "Новосиньково": [37.268889, 55.413611],
  "Омск": [73.368212, 54.989342],
  "Оренбург": [55.098749, 51.768205],
  "Переславль": [38.856389, 56.738056],
  "Пенза": [45, 53.2],
  "Пермь": [56.229398, 58.010374],
  "Петропавловск-Камчатский": [158.650307, 53.037961],
  "Подмосковье": [37.617298, 55.755819],
  "пос. Заветы Ильича": [37.916667, 55.7],
  "пос. им. Тельмана": [37.85, 55.583333],
  "Пушкино": [37.845476, 56.017349],
  "Ростов-на-Дону": [39.701505, 47.235713],
  "Рузский район": [36.19507, 55.698889],
  "Рязань": [39.746018, 54.629216],
  "Самара": [50.101783, 53.195042],
  "Самарская область": [50.101783, 53.195042],
  "Санкт-Петербург": [30.335099, 59.93428],
  "Севастополь": [33.5224, 44.58883],
  "Сергиев Посад": [38.134277, 56.310039],
  "Сортавала, Карелия": [30.692222, 61.705278],
  "Лемболово": [30.55, 60.366667],
  "Ставрополь": [41.97337, 45.044502],
  "Сургут": [73.396221, 61.254035],
  "Сыктывкар": [50.836498, 61.668789],
  "Тверь": [35.911896, 56.858721],
  "Томск": [84.948397, 56.48464],
  "Тула": [37.618423, 54.193033],
  "Тюмень": [65.534328, 57.153033],
  "Уфа": [55.958727, 54.735147],
  "Хабаровск": [135.071917, 48.480223],
  "Химки": [37.438556, 55.888611],
  "Челябинск": [61.402554, 55.159897],
  "Южно-Сахалинск": [142.738067, 46.959118],
  "Ярославская область": [39.874444, 57.626389],
};

function normalizeCityName(city?: string | null) {
  if (!city) return "";
  let normalized = city.trim();
  if (normalized === "СПб") normalized = "Санкт-Петербург";
  if (normalized === "Ростов") normalized = "Ростов-на-Дону";
  normalized = normalized.replace(/\s*\(.*\)/, "");
  return normalized;
}

function addCoordinatesToKennels(originalData: KennelsData): KennelsData {
  const processedData: KennelsData = {};

  Object.entries(originalData).forEach(([letter, group]) => {
    processedData[letter] = [];

    group.forEach((kennel) => {
      const kennelCopy = { ...kennel };

      if (!kennel.location?.trim()) {
        processedData[letter].push(kennelCopy);
        return;
      }

      const locations = kennel.location
        .split(",")
        .map((loc) => loc.trim())
        .filter(Boolean);

      if (!locations.length) {
        processedData[letter].push(kennelCopy);
        return;
      }

      locations.forEach((loc) => {
        const item: KennelItem = { ...kennelCopy };
        const normalizedLoc = normalizeCityName(loc);

        let coords: [number, number] | undefined;

        if (cityCoordinates[loc]) {
          coords = cityCoordinates[loc];
        } else if (cityCoordinates[normalizedLoc]) {
          coords = cityCoordinates[normalizedLoc];
        } else {
          for (const [city, cityCoords] of Object.entries(cityCoordinates)) {
            if (loc.includes(city) || city.includes(loc)) {
              coords = cityCoords;
              break;
            }
          }
        }

        if (coords) {
          item.coords = coords;
          item.displayLocation = loc;
        }

        processedData[letter].push(item);
      });
    });
  });

  return processedData;
}

function processKennelsData(kennelsData: KennelsData): CityStats {
  const cityStats: CityStats = {};

  Object.values(kennelsData).forEach((letterGroup) => {
    letterGroup.forEach((kennel) => {
      if (!kennel.coords) return;

      const city = kennel.displayLocation || kennel.location || "Не указан";

      if (!cityStats[city]) {
        cityStats[city] = {
          count: 0,
          members: 0,
          coords: kennel.coords,
          kennels: [],
        };
      }

      cityStats[city].count += 1;
      cityStats[city].kennels.push(kennel);
      if (kennel.isMember) cityStats[city].members += 1;
    });
  });

  return cityStats;
}

function applyCityOffset(city: string, lon: number, lat: number): [number, number] {
  const shifted = new Set([
    "Московская область",
    "Подмосковье",
    "Ленинградская область",
    "Ярославская область",
    "Калужская область",
    "Самарская область",
    "Алтайский край",
    "Карелия",
    "Владимирская область",
  ]);

  return shifted.has(city) ? [lon + 0.2, lat + 0.1] : [lon, lat];
}

function formatContactPhone(phone: string) {
  return phone.replace(/\D/g, "");
}

function KennelsMap() {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const mapRef = useRef<HTMLDivElement | null>(null);
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  const [cityStats, setCityStats] = useState<CityStats>({});
  const [selectedCity, setSelectedCity] = useState<string>("");
  const [selectedStats, setSelectedStats] = useState<CityStats[string] | null>(null);
  const [tooltip, setTooltip] = useState({
    html: "",
    x: 0,
    y: 0,
    visible: false,
  });
  const [mapError, setMapError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [kennelsRes, geoRes] = await Promise.all([
          fetch("/data/kennels-data.json"),
          fetch("/data/russia.geojson"),
        ]);

        if (!kennelsRes.ok) throw new Error("Не найден /assets/data/kennels-data.json");
        if (!geoRes.ok) throw new Error("Не найден /assets/data/russia.geojson");

        const kennelsJson = (await kennelsRes.json()) as KennelsData;
        const geo = await geoRes.json();

        if (cancelled || !svgRef.current || !mapRef.current) return;

        const processed = addCoordinatesToKennels(kennelsJson);
        const nextCityStats = processKennelsData(processed);
        setCityStats(nextCityStats);

        const svg = d3.select(svgRef.current);
        svg.selectAll("*").remove();

        const width = 1200;
        const height = 700;

        const gRoot = svg.append("g").attr("id", "root");
        const gGraticule = gRoot.append("g").attr("id", "graticule-layer");
        const gMap = gRoot.append("g").attr("id", "map-layer");
        const gCities = gRoot.append("g").attr("id", "cities-layer");
        const gKennels = gRoot.append("g").attr("id", "kennels-layer");
        const gTop = gRoot.append("g").attr("id", "top-layer");

        const projection = d3.geoMercator()
          .center([100, 60])
          .scale(2000)
          .translate([600, 450]);

        const geoPath = d3.geoPath(projection);
        const graticule = d3.geoGraticule().step([10, 10]);

        const fitProjectionToGeoJSON = (geojson: any, size: [number, number], paddingScale = 0.95) => {
          const [w, h] = size;
          const path = d3.geoPath(projection);
          const b = path.bounds(geojson);
          const dx = b[1][0] - b[0][0];
          const dy = b[1][1] - b[0][1];
          const x = (b[0][0] + b[1][0]) / 2;
          const y = (b[0][1] + b[1][1]) / 2;
          const scale = paddingScale / Math.max(dx / w, dy / h);
          const translate = [w / 2 - scale * x, h / 2 - scale * y] as const;

          projection
            .scale(projection.scale() * scale * 3)
            .translate([
              projection.translate()[0] + translate[0],
              projection.translate()[1] + translate[1],
            ]);
        };

        const recenterOn = (lon: number, lat: number, size: [number, number]) => {
          const [w, h] = size;
          const target = projection([lon, lat]);
          if (!target) return;
          const t = projection.translate();
          const dx = w / 2 - target[0];
          const dy = h / 2 - target[1];
          projection.translate([t[0] + dx, t[1] + dy]);
        };

        fitProjectionToGeoJSON(geo, [width, height], 0.98);
        recenterOn(94.7, 66.4, [width, 300]);

        gGraticule.append("path")
          .datum(graticule())
          .attr("class", "home-map-graticule")
          .attr("d", geoPath as any);

        const hideTooltip = () => {
          setTooltip((prev) => ({ ...prev, visible: false }));
        };

        const showTooltip = (html: string, x: number, y: number) => {
          setTooltip({ html, x, y, visible: true });
        };

        const zoom = d3.zoom<SVGSVGElement, unknown>()
          .scaleExtent([0.6, 100])
          .wheelDelta((event: any) => -event.deltaY * (event.deltaMode ? 120 : 1) / 500)
          .on("zoom", (event) => {
            const { x, y, k } = event.transform;
            const inv = 1 / k;

            gRoot.attr("transform", `translate(${x},${y}) scale(${k})`);

            gMap.selectAll<SVGPathElement, unknown>("path.home-region")
              .attr("stroke-width", function () {
                const s = Number(this.getAttribute("data-original-stroke") || 1.1);
                return s * inv;
              });

            gKennels.selectAll<SVGCircleElement, unknown>("circle")
              .attr("r", function () {
                const r = Number(this.getAttribute("data-original-radius") || 12);
                return r * inv;
              });

            gKennels.selectAll<SVGCircleElement, unknown>("circle")
              .attr("stroke-width", function () {
                const s = Number(this.getAttribute("data-original-stroke") || 2);
                return s * inv;
              });

            gKennels.selectAll<SVGTextElement, unknown>("text")
              .style("font-size", function () {
                const s = Number(this.getAttribute("data-original-size") || 14);
                return `${s * inv}px`;
              });

            gRoot.selectAll<SVGTextElement, unknown>("g.city-kennel-pin text")
              .style("font-size", function () {
                const s = Number(this.getAttribute("data-original-size") || 20);
                return `${s * inv}px`;
              })
              .attr("x", 28 * inv)
              .attr("y", 0);
          });

        zoomBehaviorRef.current = zoom;

        svg.call(zoom as any)
          .call((zoom as any).transform, d3.zoomIdentity)
          .on("dblclick.zoom", null);

        const zoomToFeature = (feature: any) => {
          const path = d3.geoPath(projection);
          const b = path.bounds(feature);
          const [[x0, y0], [x1, y1]] = b;
          const dx = x1 - x0;
          const dy = y1 - y0;
          const cx = (x0 + x1) / 2;
          const cy = (y0 + y1) / 2;
          const scale = Math.max(1, Math.min(12, 0.9 / Math.max(dx / width, dy / height)));
          const transform = d3.zoomIdentity
            .translate(width / 2, height / 2)
            .scale(scale)
            .translate(-cx, -cy);

          svg.transition().duration(600).ease(d3.easeCubicOut).call((zoom as any).transform, transform);
        };

        gMap.selectAll("path.region")
          .data(geo.features, (d: any) => d.properties?.name || d.properties?.NAME || d.id)
          .enter()
          .append("path")
          .attr("class", "home-region")
          .attr("d", geoPath as any)
          .attr("data-original-stroke", 1.1)
          .on("mousemove", function (event: MouseEvent, d: any) {
            const name = d.properties?.name || d.properties?.NAME || d.id || "Регион";
            const [x, y] = d3.pointer(event, mapRef.current);
            showTooltip(`<strong>${name}</strong>`, x, y);
          })
          .on("mouseout", hideTooltip)
          .on("click", function (_event: MouseEvent, d: any) {
            const isActive = d3.select(this).classed("home-region--active");
            gMap.selectAll(".home-region").classed("home-region--active", false);
            d3.select(this).classed("home-region--active", !isActive);
            if (!isActive) zoomToFeature(d);
          });

        Object.entries(nextCityStats).forEach(([city, statsItem]) => {
          let [lon, lat] = applyCityOffset(city, statsItem.coords[0], statsItem.coords[1]);
          const projected = projection([lon, lat]);
          if (!projected) return;

          const [x, y] = projected;
          const showNumber = statsItem.count <= 9;
          const hasMember = statsItem.members > 0;

          const group = gKennels.append("g")
            .attr("class", `home-kennel-marker ${hasMember ? "member" : ""}`)
            .attr("transform", `translate(${x},${y})`)
            .on("mouseover", function (event: MouseEvent) {
              let content = `<div class="tooltip-city">${city}</div>`;
              content += `<div class="tooltip-kennels">Питомников: ${statsItem.count}`;
              if (statsItem.members > 0) content += ` • Членов НКП: ${statsItem.members}`;
              content += `</div>`;
              const [tooltipX, tooltipY] = d3.pointer(event, mapRef.current);
              showTooltip(content, tooltipX, tooltipY);
            })
            .on("mouseout", hideTooltip)
            .on("click", (event: MouseEvent) => {
              event.stopPropagation();
              setSelectedCity(city);
              setSelectedStats(statsItem);
            });

          group.append("circle")
            .attr("r", 12)
            .attr("data-original-radius", 12)
              .attr("data-original-stroke", 2)
            .attr("fill", hasMember ? "#f5a623" : "#2f80ed")
            .attr("stroke", "#fff")
            .attr("stroke-width", 2);

          if (showNumber) {
            group.append("text")
              .attr("class", "home-kennel-count")
              .attr("dy", "0.35em")
              .attr("data-original-size", 14)
              .style("font-size", "14px")
              .style("pointer-events", "none")
              .style("fill", "white")
              .style("font-weight", "bold")
              .text(statsItem.count);
          }
        });

        const drawCityLabel = (
          selection: d3.Selection<SVGGElement, CityEntry, SVGGElement, unknown>
        ) => {
          selection.selectAll("text").remove();

          selection.append("text")
            .attr("x", 28)
            .attr("y", 0)
            .attr("data-original-size", 20)
            .attr("text-anchor", "start")
            .attr("alignment-baseline", "middle")
            .style("font-size", "20px")
            .style("font-weight", "600")
            .style("fill", "#2c3e50")
            .style("pointer-events", "none")
            .style(
              "text-shadow",
              "2px 2px 4px white, -2px -2px 4px white, 2px -2px 4px white, -2px 2px 4px white"
            )
            .text((d) => d[0]);
        };

        const entries = Object.entries(nextCityStats) as CityEntry[];

        gCities
          .selectAll<SVGGElement, CityEntry>("g.city-kennel-pin")
          .data(
            entries.filter(([city]) => !["Москва", "Санкт-Петербург", "Казань"].includes(city)),
            (d) => d[0]
          )
          .join("g")
          .attr("class", "city-kennel-pin")
          .attr("transform", (d) => {
            const [city, statsItem] = d;
            const [lon, lat] = applyCityOffset(city, statsItem.coords[0], statsItem.coords[1]);
            const p = projection([lon, lat]);
            return p ? `translate(${p[0]},${p[1]})` : null;
          })
          .call(drawCityLabel);

        gTop
          .selectAll<SVGGElement, CityEntry>("g.city-kennel-pin")
          .data(
            entries.filter(([city]) => ["Москва", "Санкт-Петербург", "Казань"].includes(city)),
            (d) => d[0]
          )
          .join("g")
          .attr("class", "city-kennel-pin home-priority-city")
          .attr("transform", (d) => {
            const [city, statsItem] = d;
            const [lon, lat] = applyCityOffset(city, statsItem.coords[0], statsItem.coords[1]);
            const p = projection([lon, lat]);
            return p ? `translate(${p[0]},${p[1]})` : null;
          })
          .call(drawCityLabel);

        svg.on("click", () => {
          setSelectedCity("");
          setSelectedStats(null);
        });

        svg.on("dblclick", () => {
          svg.transition().duration(500).call((zoom as any).transform, d3.zoomIdentity);
          gMap.selectAll(".home-region").classed("home-region--active", false);
        });
      } catch (e) {
        if (!cancelled) {
          setMapError(e instanceof Error ? e.message : "Ошибка загрузки карты");
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleZoomIn = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomBehaviorRef.current.scaleBy as any, 1.5);
  };

  const handleZoomOut = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomBehaviorRef.current.scaleBy as any, 0.75);
  };

  const handleZoomReset = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current).transition().duration(500).call(zoomBehaviorRef.current.transform as any, d3.zoomIdentity);
  };

  return (
    <div className="home-map-shell">
    <div className={`home-map-container ${selectedStats ? "sidebar-open" : ""}`}>
      <div className="home-russia-map" ref={mapRef}>
        <div
          className="home-map-tooltip"
          aria-hidden={!tooltip.visible}
          style={{
            left: tooltip.x,
            top: tooltip.y,
            opacity: tooltip.visible ? 1 : 0,
          }}
          dangerouslySetInnerHTML={{ __html: tooltip.html }}
        />

        <div className="home-map-zoom-controls">
          <button type="button" onClick={handleZoomIn}>+</button>
          <button type="button" onClick={handleZoomOut}>−</button>
          <button type="button" onClick={handleZoomReset}>⌂</button>
        </div>

        <div className="home-map-legend">
          <span className="home-map-legend-item">
            <span className="home-map-legend-dot home-map-legend-region" />
            Регион
          </span>
          <span className="home-map-legend-item">
            <span className="home-map-legend-dot home-map-legend-kennel" />
            Питомник
          </span>
          <span className="home-map-legend-item">
            <span className="home-map-legend-dot home-map-legend-member" />
            Член НКП
          </span>
        </div>

        {mapError ? (
          <div className="home-map-error">{mapError}</div>
        ) : (
          <svg
            ref={svgRef}
            viewBox="0 0 1200 700"
            className="home-map-svg"
            preserveAspectRatio="xMidYMid meet"
          />
        )}
      </div>

      <aside className={`home-map-sidebar ${selectedStats ? "visible" : ""}`}>
        <div className="home-map-sidebar-header">
          <span>{selectedCity || "Информация о городе"}</span>
          <button
            type="button"
            onClick={() => {
              setSelectedCity("");
              setSelectedStats(null);
            }}
          >
            ✕
          </button>
        </div>

        {selectedStats && (
          <>
            <div className="home-map-city-stats">
              <div><strong>Питомников:</strong> {selectedStats.count}</div>
              <div><strong>Членов НКП:</strong> {selectedStats.members}</div>
            </div>

            <div className="home-map-kennel-list">
              {selectedStats.kennels.map((kennel, index) => (
                <div className="home-map-kennel-item" key={`${kennel.name_rus || "kennel"}-${index}`}>
                  <div className="home-map-kennel-title-row">
                    <div className="home-map-kennel-name">{kennel.name_rus || "Без названия"}</div>
                    {kennel.isMember && <span className="home-map-member-badge">в НКП</span>}
                  </div>

                  {kennel.FCIname && (
                    <div className="home-map-kennel-fci">
                      {kennel.FCIname}{kennel.FCInumber ? ` ${kennel.FCInumber}` : ""}
                    </div>
                  )}

                  {kennel.breederName && (
                    <div className="home-map-contact-line">{kennel.breederName}</div>
                  )}

                  {kennel.website && (
                    <div className="home-map-contact-line">
                      <a href={kennel.website} target="_blank" rel="noopener noreferrer">сайт</a>
                    </div>
                  )}

                  {kennel.vkGroup && (
                    <div className="home-map-contact-line">
                      <a href={kennel.vkGroup} target="_blank" rel="noopener noreferrer">вк</a>
                    </div>
                  )}

                  {kennel.telegramGroup && (
                    <div className="home-map-contact-line">
                      <a href={kennel.telegramGroup} target="_blank" rel="noopener noreferrer">телеграм</a>
                    </div>
                  )}

                  {kennel.email && (
                    <div className="home-map-contact-line">
                      <a href={`mailto:${kennel.email}`}>{kennel.email}</a>
                    </div>
                  )}

                  {kennel.phone && (
                    <div className="home-map-contact-line">
                      <a href={`tel:${formatContactPhone(kennel.phone)}`}>{kennel.phone}</a>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </aside>
    </div>

    <div className="home-map-stats-wrapper">
      <div className="home-map-stats">
      <div className="home-region-stat">
        <div className="home-stat-icon">🏙️</div>
        <div>
          <div className="home-stat-number">
            {Object.entries(cityStats).filter(([city]) => city === "Москва" || city === "Московская область" || city === "Подмосковье").reduce((sum, [, item]) => sum + item.count, 0)}
          </div>
          <div className="home-stat-label">Москва и МО</div>
        </div>
      </div>

      <div className="home-region-stat">
        <div className="home-stat-icon">🏛️</div>
        <div>
          <div className="home-stat-number">
            {cityStats["Санкт-Петербург"]?.count || 0}
          </div>
          <div className="home-stat-label">Санкт-Петербург</div>
        </div>
      </div>

      <div className="home-region-stat">
        <div className="home-stat-icon">⛰️</div>
        <div>
          <div className="home-stat-number">
            {Object.entries(cityStats)
              .filter(([city]) => city !== "Москва" && city !== "Московская область" && city !== "Подмосковье" && city !== "Санкт-Петербург")
              .reduce((sum, [, item]) => sum + item.count, 0)}
          </div>
          <div className="home-stat-label">Другие регионы</div>
        </div>
      </div>
    </div>
    </div>
  </div>
  );
}

/* PAGE */
export default function Home() {
  const [homeNews, setHomeNews] = useState<HomeNewsItem[]>([]);
  const [breederCount, setBreederCount] = useState(350);
  const [heroDog, setHeroDog] = useState<HeroDog | null | "loading">("loading");

  const visibleNews = useMemo(() => {
    const source: Array<(typeof news)[number] | HomeNewsItem> = homeNews.length ? homeNews : news;
    return source.slice(0, 5);
  }, [homeNews]);
  const featured = visibleNews[0] ?? news[0];
  const others = featured ? visibleNews.slice(1) : visibleNews;

  // ── Загружаем кол-во питомников (заводчиков) из БД ──────────────────────────────
  useEffect(() => {
    fetch("/api/dogs/stats/")
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.breeders != null) setBreederCount(data.breeders);
      })
      .catch(() => {});
  }, []);

  // ── Загружаем собаку-звезду для hero-карточки ───────────────────────────────
  useEffect(() => {
    fetch("/api/dogs/search/?q=Chudni Medvezhonok Gold Sensation")
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        const results = Array.isArray(data) ? data : data?.results;
        if (results?.length) setHeroDog(results[0] as HeroDog);
        else setHeroDog(null);
      })
      .catch(() => setHeroDog(null));
  }, []);

  // ── Новости ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    let ignore = false;

    const loadNews = async () => {
      try {
        const dict = await getDict();
        if (ignore) return;

        let payload: any = null;
        try {
          const res = await fetch("/api/news/");
          if (res.ok) payload = await res.json();
        } catch { payload = null; }
        if (ignore) return;

        const results: any[] = Array.isArray(payload?.results)
          ? payload.results
          : Array.isArray(payload) ? payload : [];

        const mapped: HomeNewsItem[] = results.map((item: any) => ({
          id:      String(item.id ?? Math.random()),
          tag:     pickValue(dict, item.category) ?? item.category ?? "Новости",
          date:    formatNewsDate(item.published_at ?? item.created_at) || item.date || "",
          title:   item.title ?? "",
          excerpt: item.excerpt ?? item.description ?? "",
          link:    "Подробнее",
          icon:    item.icon ?? "📰",
          to:      `/news/${item.id ?? item.slug ?? "#"}`,
        }));

        if (!ignore && mapped.length) setHomeNews(mapped);
      } catch {
        if (!ignore) setHomeNews([]);
      }
    };

    loadNews();
    return () => { ignore = true; };
  }, []);

  const stats = [
    { label: "Членов клуба", value: 1250,        plus: true },
    { label: "Питомников",   value: breederCount, plus: true },
    { label: "Лет работы",   value: 15,           plus: true },
  ];

  return (
    <div className="home-page">
      {/* HERO */}
      <section className="home-hero">
        <div className="home-hero-content">
          <div className="home-hero-text">
            <h2>Сибирские хаски<br />мирового класса</h2>
            <p className="home-hero-subtitle">
              Ведущий национальный клуб России, объединяющий заводчиков, владельцев и любителей породы сибирский хаски.
              Сохраняем традиции, развиваем будущее.
            </p>
            <div className="home-hero-buttons">
              <Link to="/archive" className="home-btn home-btn-primary">🔍 Найти собаку</Link>
              <Link to="/breed" className="home-btn home-btn-secondary">📚 О породе</Link>
            </div>

            <div className="home-hero-stats">
              {stats.map(s => <StatCard key={s.label} {...s} />)}
            </div>
          </div>

          {/* ── Hero-карточка с реальной собакой ── */}
          <div className="home-hero-visual">
            {heroDog === "loading" || heroDog === null ? (
              <p className="home-hero-loading">Загрузка...</p>
            ) : (
              <div className="home-hero-card">
                <div className="home-hero-image">
                  {heroDog.photo_url ? (
                    <img
                      src={dogPhoto(heroDog.photo_url)}
                      alt={heroDog.display_name}
                      style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%" }}
                    />
                  ) : "🐕"}
                </div>
                <h3>{heroDog.display_name}</h3>
                <p>
                  {[heroDog.prefix_titles, heroDog.suffix_titles].filter(Boolean).join(" · ") || "Сибирский хаски"}
                </p>
                <Link to={`/archive/dog/${heroDog.id}`} className="home-btn home-btn-primary">
                  Посмотреть профиль
                </Link>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* MAP */}
      <section className="home-interactive-map-section">
        <div className="home-map-content">
          <div className="home-head-section-header">
            <h2 className="home-head-section-title">Наша география</h2>
            <p className="home-head-section-subtitle">Питомники и члены клуба по всей России</p>
          </div>

          <KennelsMap />
        </div>
      </section>

      {/* ACTIVITY */}
      <section className="home-activity-section">
        <div className="home-activity-content">
          <div className="home-head-section-header">
            <h2 className="home-head-section-title">Живая лента активности</h2>
            <p className="home-head-section-subtitle">Что происходит в мире хаски прямо сейчас</p>
          </div>
          <ActivityFeed />
        </div>
      </section>

      {/* FEATURES */}
      <section className="home-features">
        <div className="home-features-content">
          <div className="home-head-section-header">
            <h2 className="home-head-section-title">Всё для породы хаски</h2>
            <p className="home-head-section-subtitle">Комплексная экосистема для заводчиков, владельцев и любителей сибирских хаски</p>
          </div>

          <div className="home-features-grid">
            {[
              { icon: "📊", title: "Породный архив", desc: "15,000+ собак в базе данных с интерактивными родословными, результатами тестов здоровья и полной историей титулов.", link: "Перейти к архиву", to: "/archive" },
              { icon: "🧬", title: "Здоровье породы", desc: "Генетические тесты, офтальмологические обследования, реестры здоровья и инструменты для планирования вязок.", link: "Тестирование", to: "/health" },
              { icon: "🏆", title: "Выставки и спорт", desc: "Календарь мероприятий, результаты выставок, ездовой спорт, семинары и обучающие программы.", link: "Мероприятия", to: "/events" },
              { icon: "🤝", title: "Сообщество", desc: "Объединяем заводчиков и владельцев, обмениваемся опытом, поддерживаем новичков и развиваем породу вместе.", link: "Присоединиться", to: "/about" },
              { icon: "🎯", title: "Умные инструменты", desc: "AI-анализ совместимости, предиктивная аналитика наследственных заболеваний, компьютерное зрение для оценки экстерьера.", link: "Инновации", to: "/tools" },
              { icon: "🌐", title: "Интеграция", desc: "Партнерство с breedarchive.com, обмен данными с ведущими клубами мира, участие в глобальных проектах.", link: "Узнать больше", to: "/about" },
            ].map(f => (
              <div key={f.title} className="home-feature-card">
                <div className="home-feature-icon">{f.icon}</div>
                <h3 className="home-feature-title">{f.title}</h3>
                <p className="home-feature-description">{f.desc}</p>
                <Link to={f.to} className="home-feature-link">{f.link} →</Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* NEWS */}
      <section className="home-news-section">
        <div className="home-news-content">
          <div className="home-head-section-header">
            <h2 className="home-head-section-title">Последние новости</h2>
            <p className="home-head-section-subtitle">Будьте в курсе всех событий в мире сибирских хаски</p>
          </div>

          <div className="home-news-grid">
            {featured && <NewsCard item={featured} featured />}
            {others.map(n => <NewsCard key={n.id} item={n} />)}
          </div>
        </div>
      </section>

      {/* PUPPIES */}
      <section className="home-features">
        <div className="home-features-content">
          <div className="home-head-section-header">
            <h2 className="home-head-section-title">🐾 Доступные щенки</h2>
            <p className="home-head-section-subtitle">Помёты от проверенных питомников — только от членов НКП.</p>
          </div>

          <div className="home-features-grid">
            {puppies.map(p => (
              <div key={p.id} className="home-feature-card">
                <div className="home-feature-icon">{p.icon}</div>
                <h3 className="home-feature-title">{p.name}</h3>
                <p className="home-feature-description">
                  {p.sex}, род. {p.dob}<br />
                  Отец: {p.sire} × Мать: {p.dam}
                </p>
                <Link to={`/puppies/${p.id}`} className="home-feature-link">Подробнее →</Link>
              </div>
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: "2rem" }}>
            <Link to="/puppies" className="home-btn home-btn-primary">Все помёты</Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="home-cta-section">
        <div className="home-cta-content">
          <h2 className="home-cta-title">Готовы присоединиться?</h2>
          <p className="home-cta-subtitle">Станьте частью сообщества, которое формирует будущее породы сибирский хаски в России.</p>
          <div className="home-cta-buttons">
            <Link to="/contact" className="home-btn home-btn-white">🚀 Стать членом клуба</Link>
            <Link to="/contact" className="home-btn home-btn-outline">📞 Связаться с нами</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
