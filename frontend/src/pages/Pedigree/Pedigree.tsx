// src/pages/Pedigree/Pedigree.tsx
import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import * as d3 from "d3";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { getDogPedigree } from "@/api/dogs";
import type { PedigreeNode } from "@/types/dog";
import "./Pedigree.css";

/* ═══════════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════════ */

type TreeNode = {
  id: number;
  name: string;
  img?: string;
  color?: string;
  prefix_titles?: string;
  suffix_titles?: string;
  sex?: number;
  year_of_birth?: number | null;
  date_of_birth?: string | null;
  land_of_birth?: string | null;
  coi?: number | null;
  children?: TreeNode[];
};

/* ═══════════════════════════════════════════════════════════════════
   API → tree
   ═══════════════════════════════════════════════════════════════════ */

function convertNode(node: PedigreeNode): TreeNode {
  const children: TreeNode[] = [];
  if (node.sire) children.push(convertNode(node.sire));
  if (node.dam) children.push(convertNode(node.dam));
  return {
    id: node.id,
    name: node.display_name || node.registered_name || "?",
    img: node.photo_url ?? undefined,
    color: node.color ?? undefined,
    prefix_titles: (node as any).prefix_titles ?? undefined,
    suffix_titles: (node as any).suffix_titles ?? undefined,
    sex: node.sex,
    year_of_birth: node.year_of_birth,
    date_of_birth: (node as any).date_of_birth ?? undefined,
    land_of_birth: (node as any).land_of_birth ?? undefined,
    coi: (node as any).coi ?? undefined,
    children: children.length ? children : undefined,
  };
}

/* ═══════════════════════════════════════════════════════════════════
   Card dimensions — compact, shrinks per depth
   ═══════════════════════════════════════════════════════════════════ */

interface CardDims {
  w: number;
  h: number;
  photoW: number;
  photoH: number;
  r: number;
  padX: number;
  titleFs: number;
  nameFs: number;
  subFs: number;
  lineH: number;
}

function getDims(depth: number, maxDepth: number): CardDims {
  const compact = maxDepth >= 4;
  const ultraCompact = maxDepth >= 5;

  if (depth === 0) {
    return ultraCompact
      ? { w: 128, h: 152, photoW: 68, photoH: 68, r: 9, padX: 5, titleFs: 7, nameFs: 8.5, subFs: 7.5, lineH: 9.5 }
      : compact
        ? { w: 136, h: 160, photoW: 74, photoH: 74, r: 10, padX: 5, titleFs: 7.5, nameFs: 9, subFs: 7.5, lineH: 10 }
        : { w: 146, h: 172, photoW: 82, photoH: 82, r: 10, padX: 6, titleFs: 8, nameFs: 9.5, subFs: 8, lineH: 10.5 };
  }

  if (depth >= 3) {
    return ultraCompact
      ? { w: 92, h: 114, photoW: 42, photoH: 42, r: 6, padX: 4, titleFs: 5.5, nameFs: 6.5, subFs: 5.5, lineH: 7.5 }
      : { w: 104, h: 128, photoW: 50, photoH: 50, r: 7, padX: 4, titleFs: 6, nameFs: 7.5, subFs: 6.5, lineH: 8.5 };
  }

  // Mid generations (depth 1-2)
  return ultraCompact
    ? { w: 110, h: 134, photoW: 56, photoH: 56, r: 7, padX: 4, titleFs: 6.5, nameFs: 7.5, subFs: 6.5, lineH: 8.5 }
    : compact
      ? { w: 120, h: 144, photoW: 62, photoH: 62, r: 8, padX: 5, titleFs: 7, nameFs: 8, subFs: 7, lineH: 9 }
      : { w: 130, h: 156, photoW: 68, photoH: 68, r: 9, padX: 5, titleFs: 7, nameFs: 8.5, subFs: 7.5, lineH: 10 };
}

/* ═══════════════════════════════════════════════════════════════════
   Colors
   ═══════════════════════════════════════════════════════════════════ */

const MALE_BORDER = "#3b82f6";
const FEMALE_BORDER = "#c026d3";
const NEUTRAL_BORDER = "#94a3b8";
const NO_IMAGE_PATH = "/no-image-dog.png";
const PLACEHOLDER_URLS = ["https://zooportal.pro/images/logo1.png"];

function dogPhoto(url?: string): string {
  return url && !PLACEHOLDER_URLS.includes(url) ? url : NO_IMAGE_PATH;
}

function borderColor(sex?: number): string {
  if (sex === 1) return MALE_BORDER;
  if (sex === 2) return FEMALE_BORDER;
  return NEUTRAL_BORDER;
}

/* ═══════════════════════════════════════════════════════════════════
   Text helpers
   ═══════════════════════════════════════════════════════════════════ */

function trunc(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}

function wrapText(s: string, maxChars: number, maxLines: number): string[] {
  const words = s.split(" ");
  const lines: string[] = [];
  let cur = "";
  let wordIdx = 0;

  for (; wordIdx < words.length; wordIdx++) {
    const w = words[wordIdx];
    const test = cur ? cur + " " + w : w;
    if (test.length <= maxChars) {
      cur = test;
    } else {
      if (cur) lines.push(cur);
      cur = w.length > maxChars ? trunc(w, maxChars) : w;
    }
    if (lines.length >= maxLines) break;
  }
  if (cur && lines.length < maxLines) lines.push(cur);

  // If there's remaining text beyond maxLines, add "…" to last line
  const hasMore = wordIdx < words.length - 1 || (lines.length === maxLines && cur !== lines[maxLines - 1]);
  if (hasMore && lines.length > 0) {
    const last = lines[lines.length - 1];
    if (!last.endsWith("…")) {
      lines[lines.length - 1] = trunc(last + "…", maxChars);
    }
  }
  return lines;
}

/* ═══════════════════════════════════════════════════════════════════
   Draw one card (SVG) — clean: only colored border, no strip,
   no dots, no sex symbol
   ═══════════════════════════════════════════════════════════════════ */

function drawCard(
  g: d3.Selection<SVGGElement, unknown, null, undefined>,
  defs: d3.Selection<SVGDefsElement, unknown, null, undefined>,
  node: TreeNode,
  depth: number,
  maxDepth: number,
  uid: string
) {
  const dim = getDims(depth, maxDepth);
  const isRoot = depth === 0;
  const cx = -dim.w / 2;
  const cy = -dim.h / 2;
  const bColor = borderColor(node.sex);

  // ── Shadow ───────────────────────────────────────────────────
  const fid = `shd-${uid}`;
  const flt = defs.append("filter")
    .attr("id", fid)
    .attr("x", "-20%").attr("y", "-15%")
    .attr("width", "140%").attr("height", "140%");
  flt.append("feDropShadow")
    .attr("dx", 0)
    .attr("dy", isRoot ? 3 : 1.5)
    .attr("stdDeviation", isRoot ? 5 : 2.5)
    .attr("flood-color", isRoot ? `${bColor}25` : "rgba(0,0,0,0.06)");

  // ── Card rect — colored border only ─────────────────────────
  g.append("rect")
    .attr("x", cx).attr("y", cy)
    .attr("width", dim.w).attr("height", dim.h)
    .attr("rx", dim.r).attr("ry", dim.r)
    .attr("fill", "#ffffff")
    .attr("stroke", bColor)
    .attr("stroke-width", isRoot ? 2 : 1.4)
    .attr("filter", `url(#${fid})`);

  // ── Titles (prefix) ──────────────────────────────────────────
  let topY = cy + 6;
  const titlesStr = [node.prefix_titles, node.suffix_titles].filter(Boolean).join(", ");
  if (titlesStr) {
    const maxTitleChars = Math.floor((dim.w - dim.padX * 2) / (dim.titleFs * 0.6));
    g.append("text")
      .attr("x", cx + dim.w / 2)
      .attr("y", topY + dim.titleFs)
      .attr("text-anchor", "middle")
      .attr("font-size", dim.titleFs)
      .attr("font-weight", "700")
      .attr("fill", "#d97706")
      .attr("letter-spacing", "0.02em")
      .text(trunc(titlesStr, maxTitleChars));
    topY += dim.titleFs + 3;
  } else {
    topY += 2;
  }

  // ── Photo ────────────────────────────────────────────────────
  const photoX = cx + (dim.w - dim.photoW) / 2;
  const photoY = topY;
  const photoR = 8;

  const pcid = `pc-${uid}`;
  defs.append("clipPath").attr("id", pcid)
    .append("rect")
    .attr("x", photoX).attr("y", photoY)
    .attr("width", dim.photoW).attr("height", dim.photoH)
    .attr("rx", photoR).attr("ry", photoR);

  const imgSrc = dogPhoto(node.img);
  g.append("image")
    .attr("href", imgSrc)
    .attr("x", photoX).attr("y", photoY)
    .attr("width", dim.photoW).attr("height", dim.photoH)
    .attr("preserveAspectRatio", "xMidYMid slice")
    .attr("clip-path", `url(#${pcid})`);

  g.append("rect")
    .attr("x", photoX).attr("y", photoY)
    .attr("width", dim.photoW).attr("height", dim.photoH)
    .attr("rx", photoR).attr("ry", photoR)
    .attr("fill", "none")
    .attr("stroke", "#e2e8f0")
    .attr("stroke-width", 0.8);

  // ── Text below photo ─────────────────────────────────────────
  let textY = photoY + dim.photoH + dim.lineH + 4;
  const textAreaW = dim.w - dim.padX * 2;
  // Conservative char-width (wider = fewer chars = names always fit)
  const maxChars = Math.floor(textAreaW / (dim.nameFs * 0.62));
  const maxSubChars = Math.floor(textAreaW / (dim.subFs * 0.58));

  // Name — always truncated with "…" if too long
  const nameLines = wrapText(node.name, maxChars, 2);
  nameLines.forEach((line, li) => {
    g.append("text")
      .attr("x", cx + dim.w / 2)
      .attr("y", textY + li * dim.lineH)
      .attr("text-anchor", "middle")
      .attr("font-size", dim.nameFs)
      .attr("font-weight", "800")
      .attr("fill", "#1d4ed8")
      .attr("cursor", "pointer")
      .text(line);
  });
  textY += nameLines.length * dim.lineH + 1;

  // Color
  if (node.color) {
    g.append("text")
      .attr("x", cx + dim.w / 2)
      .attr("y", textY)
      .attr("text-anchor", "middle")
      .attr("font-size", dim.subFs)
      .attr("fill", "#475569")
      .text(trunc(node.color, maxSubChars));
    textY += dim.lineH;
  }

  // Country + Year
  const yr = node.year_of_birth
    ? String(node.year_of_birth)
    : node.date_of_birth
      ? node.date_of_birth.slice(0, 4)
      : null;
  const loc = [node.land_of_birth, yr].filter(Boolean).join(" ");
  if (loc) {
    g.append("text")
      .attr("x", cx + dim.w / 2)
      .attr("y", textY)
      .attr("text-anchor", "middle")
      .attr("font-size", dim.subFs)
      .attr("fill", "#475569")
      .text(trunc(loc, maxSubChars));
    textY += dim.lineH;
  }

  // COI
  if (node.coi != null) {
    g.append("text")
      .attr("x", cx + dim.w / 2)
      .attr("y", textY)
      .attr("text-anchor", "middle")
      .attr("font-size", dim.subFs - 0.5)
      .attr("font-weight", "600")
      .attr("fill", "#94a3b8")
      .text(`COI ${node.coi.toFixed(2)} %`);
  }
}

/* ═══════════════════════════════════════════════════════════════════
   Layout — tight gaps
   ═══════════════════════════════════════════════════════════════════ */

const MIN_GEN = 3;
const MAX_GEN = 6;
const H_GAP = 24;
const V_GAP = 3;
const PAD_TOP = 12;
const PAD_BOTTOM = 12;
const PAD_LEFT = 8;
const PAD_RIGHT = 10;

/* ═══════════════════════════════════════════════════════════════════
   Component
   ═══════════════════════════════════════════════════════════════════ */

export default function Pedigree() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [depth, setDepth] = useState(3);
  const [rawData, setRawData] = useState<TreeNode | null>(null);
  const [dogName, setDogName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const frameRef = useRef<HTMLDivElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const gRef = useRef<SVGGElement | null>(null);

  // ── Load ────────────────────────────────────────────────────
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    getDogPedigree(Number(id), depth)
      .then((p) => {
        setDogName(p.display_name || p.registered_name || "");
        setRawData(convertNode(p));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Ошибка загрузки"))
      .finally(() => setLoading(false));
  }, [id, depth]);

  // ── Render ──────────────────────────────────────────────────
  const renderTree = useCallback(() => {
    const frame = frameRef.current;
    const scroll = scrollRef.current;
    const svgEl = svgRef.current;
    const gEl = gRef.current;
    if (!frame || !scroll || !svgEl || !gEl || !rawData) return;

    const svg = d3.select(svgEl);
    const gSel = d3.select(gEl);
    const frameW = frame.clientWidth;

    // Max depth in data
    let actualMaxDepth = 0;
    const walkDepth = (n: TreeNode, d: number) => {
      if (d > actualMaxDepth) actualMaxDepth = d;
      n.children?.forEach((c) => walkDepth(c, d + 1));
    };
    walkDepth(rawData, 0);

    const rootDim = getDims(0, actualMaxDepth);
    const midDim = getDims(1, actualMaxDepth);

    // Tighter spacing for deeper pedigrees
    const vSpace = rootDim.h + V_GAP;
    const hSpace = midDim.w + H_GAP;

    const root = d3.tree<TreeNode>()
      .nodeSize([vSpace, hSpace])
      .separation((a, b) => (a.parent === b.parent ? 1 : 1.02))(
        d3.hierarchy<TreeNode>(rawData)
      );

    const nodes = root.descendants();
    const links = root.links();

    const xs = nodes.map((d) => d.x);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const maxY = Math.max(...nodes.map((d) => d.y));

    const largestH = rootDim.h;
    const largestW = rootDim.w;

    const svgH = Math.max(280, Math.ceil(maxX - minX) + largestH + PAD_TOP + PAD_BOTTOM);
    const baseTop = PAD_TOP + largestH / 2 - minX;
    const contentW = PAD_LEFT + largestW / 2 + maxY + largestW / 2 + PAD_RIGHT;
    const needScroll = contentW > frameW;

    // Clear
    gSel.selectAll("*").remove();
    svg.selectAll("defs").remove();
    const defs = svg.insert<SVGDefsElement>("defs", ":first-child");

    if (needScroll) {
      frame.classList.add("is-scroll");
      scroll.style.width = `${contentW}px`;
      svg.attr("width", contentW).attr("height", svgH).attr("viewBox", null);
    } else {
      frame.classList.remove("is-scroll");
      scroll.style.width = "100%";
      svg
        .attr("width", frameW)
        .attr("height", svgH)
        .attr("viewBox", `0 0 ${contentW} ${svgH}`)
        .attr("preserveAspectRatio", "xMinYMin meet");
    }

    // ── Connectors — right-angle elbows ────────────────────────
    links.forEach((link) => {
      const sDim = getDims(link.source.depth, actualMaxDepth);
      const tDim = getDims(link.target.depth, actualMaxDepth);

      const x0 = PAD_LEFT + largestW / 2 + link.source.y + sDim.w / 2;
      const y0 = baseTop + link.source.x;
      const x1 = PAD_LEFT + largestW / 2 + link.target.y - tDim.w / 2;
      const y1 = baseTop + link.target.x;
      const mx = (x0 + x1) / 2;

      // Horizontal from parent → vertical turn → horizontal to child
      gSel.append("path")
        .attr("class", "pdg-link")
        .attr("d", `M${x0},${y0} H${mx} V${y1} H${x1}`);
    });

    // ── Cards ────────────────────────────────────────────────
    nodes.forEach((d, i) => {
      const nodeG = gSel
        .append<SVGGElement>("g")
        .datum(d)
        .attr("class", `pdg-node${d.depth === 0 ? " pdg-node--root" : ""}`)
        .attr("transform", `translate(${PAD_LEFT + largestW / 2 + d.y},${baseTop + d.x})`)
        .style("cursor", "pointer")
        .on("click", () => navigate(`/archive/dog/${d.data.id}`));

      drawCard(nodeG as any, defs as any, d.data, d.depth, actualMaxDepth, `n${i}`);
    });
  }, [rawData, navigate]);

  useEffect(() => {
    renderTree();
    const frame = frameRef.current;
    if (!frame) return;
    const ro = new ResizeObserver(renderTree);
    ro.observe(frame);
    return () => ro.disconnect();
  }, [renderTree]);

  // ── Stats ──────────────────────────────────────────────────
  const stats = useMemo(() => {
    if (!rawData) return null;
    let males = 0, females = 0, total = 0;
    const walk = (n: TreeNode) => {
      total++;
      if (n.sex === 1) males++;
      if (n.sex === 2) females++;
      n.children?.forEach(walk);
    };
    walk(rawData);
    return { males, females, total };
  }, [rawData]);

  return (
    <div className="pedigree-page">
      <Breadcrumb
        title={loading ? "Загрузка…" : dogName || "Родословная"}
        items={[
          { label: "Главная", to: "/" },
          { label: "Архив", to: "/archive" },
          { label: "Родословная" },
        ]}
      />

      <div className="pedigree-controls-bar">
        <div className="pedigree-gen-tabs" role="group" aria-label="Количество поколений">
          <span className="pedigree-gen-label">Поколений:</span>
          {Array.from({ length: MAX_GEN - MIN_GEN + 1 }, (_, i) => MIN_GEN + i).map((n) => (
            <button
              key={n}
              className={`pedigree-gen-tab${depth === n ? " is-active" : ""}`}
              onClick={() => setDepth(n)}
              aria-pressed={depth === n}
            >
              {n}
            </button>
          ))}
        </div>

        {stats && !loading && (
          <div className="pedigree-stats">
            <span className="pdg-badge pdg-badge--male">♂ {stats.males}</span>
            <span className="pdg-badge pdg-badge--female">♀ {stats.females}</span>
            <span className="pdg-badge pdg-badge--total">Всего {stats.total}</span>
          </div>
        )}
      </div>

      {error && <div className="pedigree-error">⚠️ {error}</div>}

      {loading && (
        <div className="pedigree-loading">
          <div className="pedigree-spinner" />
          <span className="pedigree-loading-text">Загрузка родословной…</span>
        </div>
      )}

      {!loading && !error && rawData && (
        <>
          <section className="pedigree-frame" ref={frameRef} aria-label="Генеалогическое дерево">
            <div className="pedigree-scroll" ref={scrollRef}>
              <svg ref={svgRef} className="pedigree-svg" role="img" aria-label={`Родословная ${dogName}`}>
                <g ref={gRef} />
              </svg>
            </div>

            <div className="pedigree-legend">
              <span className="pdg-legend-item">
                <span className="pdg-legend-swatch pdg-legend-swatch--male" />
                Кобель
              </span>
              <span className="pdg-legend-item">
                <span className="pdg-legend-swatch pdg-legend-swatch--female" />
                Сука
              </span>
            </div>
          </section>

          <div className="pedigree-scroll-hint">← прокрутите горизонтально →</div>
        </>
      )}
    </div>
  );
}

