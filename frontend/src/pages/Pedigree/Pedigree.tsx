// src/pages/Pedigree/Pedigree.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import * as d3 from "d3";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { getDogPedigree } from "@/api/dogs";
import type { PedigreeNode } from "@/types/dog";
import "./Pedigree.css";

// ── Типы ──────────────────────────────────────────────────────────────────────

type TreeNode = {
  id: number;
  name: string;
  img?: string;
  color?: string;
  prefix_titles?: string;
  sex?: number;
  year_of_birth?: number | null;
  children?: TreeNode[];
};

// ── Конвертация API → d3 ──────────────────────────────────────────────────────

function pedigreeToTree(node: PedigreeNode | null): TreeNode | null {
  if (!node) return null;

  const children: TreeNode[] = [];
  const sireTree = pedigreeToTree(node.sire);
  const damTree  = pedigreeToTree(node.dam);

  if (sireTree) children.push(sireTree);
  if (damTree)  children.push(damTree);

  return {
    id:            node.id,
    name:          node.display_name || node.registered_name || "?",
    img:           node.photo_url ?? undefined,
    color:         node.color ?? undefined,
    prefix_titles: (node as any).prefix_titles ?? undefined,
    sex:           node.sex,
    year_of_birth: node.year_of_birth,
    children:      children.length > 0 ? children : undefined,
  };
}

// ── Константы узла ────────────────────────────────────────────────────────────

const NODE_W      = 168;
const NODE_H      = 64;
const IMG_SIZE    = 40;
const H_GAP       = 48;   // горизонтальный зазор между уровнями
const V_GAP       = 12;   // вертикальный зазор между узлами
const PAD_V       = 40;   // отступ сверху/снизу
const PAD_L       = NODE_W / 2 + 16;   // отступ слева — минимум NODE_W/2 чтобы корень не обрезался
const PAD_R       = 32;   // отступ справа от последнего уровня

// Цвета по полу
// Цвета согласованы с токенами сайта (--bright-blue, --gradient-secondary)
const SEX_STROKE: Record<number, string> = {
  1: "#60a5fa",   // blue-400
  2: "#c084fc",   // purple-400
};
const SEX_BADGE: Record<number, string> = {
  1: "#3b82f6",   // var(--bright-blue)
  2: "#9333ea",   // purple-600
};

// ── Компонент ─────────────────────────────────────────────────────────────────

export default function Pedigree() {
  const { id } = useParams<{ id: string }>();
  const [depth, setDepth]     = useState<number>(3);
  const [data, setData]       = useState<TreeNode | null>(null);
  const [dogName, setDogName] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const frameRef  = useRef<HTMLDivElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const svgRef    = useRef<SVGSVGElement | null>(null);
  const gRef      = useRef<SVGGElement | null>(null);

  // ── Загрузка ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);

    getDogPedigree(Number(id), depth)
      .then((pedigree) => {
        setDogName(pedigree.display_name || pedigree.registered_name || "");
        setData(pedigreeToTree(pedigree));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Ошибка загрузки"))
      .finally(() => setLoading(false));
  }, [id, depth]);

  // ── D3 рендер ───────────────────────────────────────────────────────────────
  useEffect(() => {
    const frame  = frameRef.current;
    const scroll = scrollRef.current;
    const svgEl  = svgRef.current;
    const gEl    = gRef.current;
    if (!frame || !scroll || !svgEl || !gEl || !data) return;

    const svg = d3.select(svgEl);
    const g   = d3.select(gEl);

    const render = () => {
      const frameW = frame.clientWidth;

      // ── Запускаем layout ──────────────────────────────────────────────────
      const rootData = d3.hierarchy<TreeNode>(data);
      const layout   = d3.tree<TreeNode>().nodeSize([NODE_H + V_GAP, NODE_W + H_GAP]);
      const root     = layout(rootData);

      const nodes = root.descendants();
      const links = root.links();

      // ── Вычисляем реальные экстенты ──────────────────────────────────────
      // x — вертикаль, y — горизонталь (d3.tree горизонтальный)
      const [minX, maxX] = d3.extent(nodes, (d) => d.x) as [number, number];
      const maxY         = d3.max(nodes, (d) => d.y) as number;

      // Реальная высота из экстентов, а не из фиксированной таблицы
      const treeH   = Math.ceil(maxX - minX) + NODE_H + 2 * PAD_V;
      const svgH    = Math.max(240, treeH);

      // Вертикальный сдвиг чтобы дерево было по центру
      const baseTop = PAD_V + NODE_H / 2 - minX;

      // Ширина
      const contentW = PAD_L + maxY + NODE_W / 2 + PAD_R;
      const needScroll = contentW > frameW;

      // ── SVG размеры ────────────────────────────────────────────────────────
      g.selectAll("*").remove();

      if (needScroll) {
        frame.classList.add("is-scroll");
        scroll.style.width = `${contentW}px`;
        svg
          .attr("width",  contentW)
          .attr("height", svgH)
          .attr("viewBox", null);
      } else {
        frame.classList.remove("is-scroll");
        scroll.style.width = "100%";
        svg
          .attr("width",  frameW)
          .attr("height", svgH)
          .attr("viewBox", `0 0 ${contentW} ${svgH}`)
          .attr("preserveAspectRatio", "xMinYMin meet");
      }

      // ── Градиенты в defs ───────────────────────────────────────────────────
      let defs = svg.select<SVGDefsElement>("defs");
      if (defs.empty()) defs = svg.insert("defs", ":first-child");
      defs.selectAll("*").remove();

      // Градиент для кобелей
      // Кобель: синий — соответствует var(--bright-blue) из стиля сайта
      const gradM = defs.append("linearGradient")
        .attr("id", "pdg-grad-m")
        .attr("x1", "0%").attr("y1", "0%")
        .attr("x2", "100%").attr("y2", "100%");
      gradM.append("stop").attr("offset", "0%").attr("stop-color", "#1e40af");
      gradM.append("stop").attr("offset", "100%").attr("stop-color", "#1e3a8a");

      // Сука: пурпурный — var(--gradient-secondary) из стиля сайта
      const gradF = defs.append("linearGradient")
        .attr("id", "pdg-grad-f")
        .attr("x1", "0%").attr("y1", "0%")
        .attr("x2", "100%").attr("y2", "100%");
      gradF.append("stop").attr("offset", "0%").attr("stop-color", "#7e22ce");
      gradF.append("stop").attr("offset", "100%").attr("stop-color", "#6b21a8");

      // Неизвестный: var(--dark-slate)
      const gradN = defs.append("linearGradient")
        .attr("id", "pdg-grad-n")
        .attr("x1", "0%").attr("y1", "0%")
        .attr("x2", "100%").attr("y2", "100%");
      gradN.append("stop").attr("offset", "0%").attr("stop-color", "#334155");
      gradN.append("stop").attr("offset", "100%").attr("stop-color", "#1e293b");

      // Clippath для фото
      nodes.forEach((d, i) => {
        defs.append("clipPath")
          .attr("id", `pdg-clip-${i}`)
          .append("rect")
          .attr("rx", 6)
          .attr("width", IMG_SIZE)
          .attr("height", IMG_SIZE);
      });

      // Glow filter
      const filter = defs.append("filter").attr("id", "pdg-glow");
      filter.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "blur");
      const feMerge = filter.append("feMerge");
      feMerge.append("feMergeNode").attr("in", "blur");
      feMerge.append("feMergeNode").attr("in", "SourceGraphic");

      // ── Рёбра ────────────────────────────────────────────────────────────
      g.selectAll<SVGPathElement, d3.HierarchyPointLink<TreeNode>>(".pdg-link")
        .data(links)
        .join("path")
        .attr("class", "pdg-link")
        .attr("d", (d) => {
          const x0 = PAD_L + d.source.y + NODE_W / 2;
          const y0 = baseTop + d.source.x;
          const x1 = PAD_L + d.target.y - NODE_W / 2;
          const y1 = baseTop + d.target.x;
          const mx = (x0 + x1) / 2;
          // Кубическая кривая Безье
          return `M${x0},${y0} C${mx},${y0} ${mx},${y1} ${x1},${y1}`;
        });

      // ── Узлы ─────────────────────────────────────────────────────────────
      const node = g
        .selectAll<SVGGElement, d3.HierarchyPointNode<TreeNode>>(".pdg-node")
        .data(nodes)
        .join("g")
        .attr("class", (d) => `pdg-node pdg-node--depth-${d.depth}`)
        .attr("transform", (d) => `translate(${PAD_L + d.y}, ${baseTop + d.x})`);

      // Тень/свечение для корневого узла
      node.filter((d) => d.depth === 0)
        .append("rect")
        .attr("class", "pdg-node-glow")
        .attr("x", -NODE_W / 2 - 4)
        .attr("y", -NODE_H / 2 - 4)
        .attr("width", NODE_W + 8)
        .attr("height", NODE_H + 8)
        .attr("rx", 16)
        .attr("ry", 16)
        .attr("fill", (d) =>
          d.data.sex === 1 ? "#3b82f6" : d.data.sex === 2 ? "#c026d3" : "#64748b"
        )
        .attr("opacity", 0.25)
        .attr("filter", "url(#pdg-glow)");

      // Основной прямоугольник
      node.append("rect")
        .attr("class", "pdg-node-bg")
        .attr("x", -NODE_W / 2)
        .attr("y", -NODE_H / 2)
        .attr("width", NODE_W)
        .attr("height", NODE_H)
        .attr("rx", 12)
        .attr("ry", 12)
        .attr("fill", (d) =>
          d.data.sex === 1
            ? "url(#pdg-grad-m)"
            : d.data.sex === 2
            ? "url(#pdg-grad-f)"
            : "url(#pdg-grad-n)"
        )
        .attr("stroke", (d) =>
          d.data.sex === 1
            ? SEX_STROKE[1]
            : d.data.sex === 2
            ? SEX_STROKE[2]
            : "#475569"
        )
        .attr("stroke-width", (d) => (d.depth === 0 ? 2 : 1.5));

      // Цветная полоска слева
      node.append("rect")
        .attr("x", -NODE_W / 2)
        .attr("y", -NODE_H / 2 + 2)
        .attr("width", 4)
        .attr("height", NODE_H - 4)
        .attr("rx", 2)
        .attr("fill", (d) =>
          d.data.sex === 1
            ? SEX_BADGE[1]
            : d.data.sex === 2
            ? SEX_BADGE[2]
            : "#64748b"
        );

      // Фото
      const withPhoto = node.filter((d) => !!d.data.img);
      withPhoto.each(function (d, i) {
        const n = d3.select(this);
        const imgX = -NODE_W / 2 + 10;
        const imgY = -IMG_SIZE / 2;
        n.append("image")
          .attr("x", imgX)
          .attr("y", imgY)
          .attr("width", IMG_SIZE)
          .attr("height", IMG_SIZE)
          .attr("href", d.data.img!)
          .attr("preserveAspectRatio", "xMidYMid slice")
          .attr("clip-path", `url(#pdg-clip-${i})`)
          .attr("style", "border-radius: 6px");

        // Рамка вокруг фото
        n.append("rect")
          .attr("x", imgX)
          .attr("y", imgY)
          .attr("width", IMG_SIZE)
          .attr("height", IMG_SIZE)
          .attr("rx", 6)
          .attr("fill", "none")
          .attr("stroke", "#ffffff22")
          .attr("stroke-width", 1);
      });

      // Текст (foreignObject)
      node.append("foreignObject")
        .attr("x", (d) => (d.data.img ? -NODE_W / 2 + IMG_SIZE + 14 : -NODE_W / 2 + 12))
        .attr("y", -NODE_H / 2 + 6)
        .attr("width", (d) => (d.data.img ? NODE_W - IMG_SIZE - 24 : NODE_W - 20))
        .attr("height", NODE_H - 12)
        .html((d) => {
          const year  = d.data.year_of_birth ? `<span class="pdg-year">${d.data.year_of_birth}</span>` : "";
          const color = d.data.color ? `<span class="pdg-color-dot" style="background:${colorToCSS(d.data.color)}"></span>` : "";
          const titles = d.data.prefix_titles
            ? `<div class="pdg-titles">${d.data.prefix_titles}</div>`
            : "";
          return `
            <div class="pdg-fo">
              ${titles}
              <div class="pdg-name">${d.data.name}</div>
              <div class="pdg-meta">${year}${color}</div>
            </div>
          `;
        });
    };

    render();
    const ro = new ResizeObserver(render);
    ro.observe(frame);
    return () => ro.disconnect();
  }, [data]);

  // ── Вспомогательные ────────────────────────────────────────────────────────
  const depthStats = useMemo(() => {
    if (!data) return null;
    let count = 0;
    const walk = (n: TreeNode) => {
      count++;
      n.children?.forEach(walk);
    };
    walk(data);
    return count;
  }, [data]);

  // ── JSX ─────────────────────────────────────────────────────────────────────
  return (
    <div className="pedigree-page">
      <Breadcrumb
        title="Родословная"
        items={[
          { label: "Главная", to: "/" },
          { label: "Архив", to: "/archive" },
          { label: "Родословная" },
        ]}
      />

      <section className="pedigree-header">
        <h1 className="pedigree-title">
          Родословная:{" "}
          <span className="pedigree-title-accent">
            {loading ? "Загрузка..." : dogName || "—"}
          </span>
        </h1>
        <p className="pedigree-sub">
          Выберите глубину поколений — дерево перестроится автоматически.
        </p>

        <div className="pedigree-controls">
          <div className="pedigree-filter">
            <select
              className="pedigree-select"
              value={depth}
              onChange={(e) => setDepth(parseInt(e.target.value, 10))}
            >
              <option value={3}>3 поколения</option>
              <option value={4}>4 поколения</option>
              <option value={5}>5 поколений</option>
              <option value={6}>6 поколений</option>
            </select>
          </div>

          {depthStats && !loading && (
            <div className="pedigree-stats">
              <span className="pedigree-stats-badge pedigree-stats-badge--male">♂ Кобели</span>
              <span className="pedigree-stats-badge pedigree-stats-badge--female">♀ Суки</span>
              <span className="pedigree-stats-count">{depthStats} записей</span>
            </div>
          )}
        </div>
      </section>

      {error && (
        <div className="pedigree-error">⚠️ {error}</div>
      )}

      {loading && (
        <div className="pedigree-loading">
          <div className="pedigree-spinner" />
          <span>Загрузка родословной...</span>
        </div>
      )}

      {!loading && !error && data && (
        <section className="pedigree-frame" ref={frameRef} aria-label="Генеалогическое дерево">
          <div className="pedigree-scroll" ref={scrollRef}>
            <svg ref={svgRef} className="pedigree-svg" role="img" aria-hidden="false">
              <g ref={gRef} />
            </svg>
          </div>

          <div className="pedigree-legend">
            <span className="pdg-legend-item pdg-legend-item--male">♂ Кобель</span>
            <span className="pdg-legend-item pdg-legend-item--female">♀ Сука</span>
          </div>
        </section>
      )}
    </div>
  );
}

// ── Цвет окраса → CSS цвет для точки ─────────────────────────────────────────
function colorToCSS(color: string): string {
  const map: Record<string, string> = {
    "серо-белый":        "#a0aec0",
    "чёрно-белый":       "#2d3748",
    "палево-белый":      "#d4a96a",
    "серебристо-белый":  "#c0cfe0",
    "медно-белый":       "#c27a3a",
    "рыже-белый":        "#c85a2a",
    "чёрный":            "#1a1a1a",
    "белый":             "#e8e8e8",
    "рыжий":             "#c84a20",
    "агути":             "#7a8a5a",
    "пегий":             "#a0a0a0",
  };
  return map[color.toLowerCase()] ?? "#64748b";
}
