// src/pages/Pedigree/Pedigree.tsx

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import * as d3 from "d3";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { useDogsPedigreeRetrieve } from "@/generated/dogs/dogs";
import type { PedigreeNode } from "@/types/dog";
import "./Pedigree.css";

// ═══════════════════════════════════════════════════════════════
// 1. TYPES
// ═══════════════════════════════════════════════════════════════

type TreeNode = {
  id: number;
  name: string;
  img?: string;
  color?: string;
  prefixTitles?: string;
  suffixTitles?: string;
  sex?: number;
  yearOfBirth?: number | null;
  dateOfBirth?: string | null;
  landOfBirth?: string | null;
  coi?: number | null;
  children?: TreeNode[];
};

type CardLayout = "vertical" | "horizontal" | "hcompact" | "textonly";

interface CardConfig {
  w: number;          // card width (px)
  h: number;          // card height (px)
  layout: CardLayout; // which draw function to use
  photoSize: number;  // photo square size; 0 = no photo
  nameFs: number;     // name font-size
  subFs: number;      // secondary text font-size
  titleFs: number;    // titles font-size
  lineH: number;      // vertical spacing between text lines
  r: number;          // border-radius
}

// ═══════════════════════════════════════════════════════════════
// 2. STYLE CONSTANTS
//    Change colors/sizes here — they propagate everywhere.
// ═══════════════════════════════════════════════════════════════

const C = {
  name:    "#2563eb",  // dog name — matches var(--bright-blue)
  title:   "#d97706",  // championship titles — orange
  text:    "#374151",  // secondary info (color, country)
  muted:   "#6b7280",  // COI value
  cardBg:  "#ffffff",  // card background
  cardBdr: "#dbe0e5",  // card border
  shadow:  "rgba(0,0,0,0.06)",
  line:    "#3b82f6",  // connector lines — brand blue
} as const;

const PLACEHOLDER_URLS = ["https://zooportal.pro/images/logo1.png"];
const DEFAULT_PHOTO = "/no-image-dog.png";

// ═══════════════════════════════════════════════════════════════
// 3. CARD CONFIGURATIONS
//    Each key maps to a generation tier. Adjust w/h/photoSize
//    to resize cards. Layout names must match draw functions.
// ═══════════════════════════════════════════════════════════════

const CONFIGS: Record<string, CardConfig> = {
  root:       { w: 210, h: 230, layout: "vertical",   photoSize: 105, nameFs: 14, subFs: 12, titleFs: 14, lineH: 16, r: 14 },
  parent:     { w: 190, h: 215, layout: "vertical",   photoSize: 95,  nameFs: 12,   subFs: 10,   titleFs: 12, lineH: 14,   r: 12 },
  horizontal: { w: 190, h: 85,  layout: "horizontal", photoSize: 62,  nameFs: 10,   subFs: 9, titleFs: 10, lineH: 12, r: 10 },
  hcompact:   { w: 170, h: 62,  layout: "hcompact",   photoSize: 46,  nameFs: 9.5,  subFs: 8,   titleFs: 9, lineH: 11, r: 8  },
  textonly:   { w: 155, h: 26,  layout: "textonly",    photoSize: 0,   nameFs: 9,    subFs: 0,   titleFs: 0, lineH: 0,  r: 6  },
};

function getConfig(depth: number): CardConfig {
  if (depth === 0) return CONFIGS.root;
  if (depth === 1) return CONFIGS.parent;
  if (depth === 2) return CONFIGS.horizontal;
  return CONFIGS.hcompact;  // gen 3+ — all same compact cards
}

// ═══════════════════════════════════════════════════════════════
// 4. HELPERS
// ═══════════════════════════════════════════════════════════════

function resolvePhoto(url?: string): string {
  return url && !PLACEHOLDER_URLS.includes(url) ? url : DEFAULT_PHOTO;
}

function sexSuffix(s?: number): string {
  return s === 1 ? " ♂" : s === 2 ? " ♀" : "";
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}

/** How many characters fit in `pxWidth` at `fontSize` */
function mc(pxWidth: number, fontSize: number): number {
  return Math.floor(pxWidth / (fontSize * 0.6));
}

function locationStr(n: TreeNode): string {
  const yr = n.yearOfBirth ? String(n.yearOfBirth) : n.dateOfBirth?.slice(0, 4) ?? null;
  return [n.landOfBirth, yr].filter(Boolean).join(" ");
}

function titlesStr(n: TreeNode): string {
  return [n.prefixTitles, n.suffixTitles].filter(Boolean).join(", ");
}

// ═══════════════════════════════════════════════════════════════
// 5. API → TREE
// ═══════════════════════════════════════════════════════════════

function convertNode(api: PedigreeNode): TreeNode {
  const ch: TreeNode[] = [];
  if (api.sire) ch.push(convertNode(api.sire));
  if (api.dam)  ch.push(convertNode(api.dam));
  return {
    id: api.id,
    name: api.display_name || api.registered_name || "?",
    img: api.photo_url ?? undefined,
    color: api.color ?? undefined,
    prefixTitles: (api as any).prefix_titles ?? undefined,
    suffixTitles: (api as any).suffix_titles ?? undefined,
    sex: api.sex,
    yearOfBirth: api.year_of_birth,
    dateOfBirth: (api as any).date_of_birth ?? undefined,
    landOfBirth: (api as any).land_of_birth ?? undefined,
    coi: (api as any).coi ?? undefined,
    children: ch.length ? ch : undefined,
  };
}

// ═══════════════════════════════════════════════════════════════
// 6. SVG DRAWING
// ═══════════════════════════════════════════════════════════════

type G = d3.Selection<SVGGElement, unknown, null, undefined>;
type Defs = d3.Selection<SVGDefsElement, unknown, null, undefined>;

// ── Shared primitives ────────────────────────────────────────

function mkShadow(defs: Defs, uid: string): string {
  const id = `sh-${uid}`;
  defs.append("filter").attr("id", id)
    .attr("x", "-10%").attr("y", "-8%").attr("width", "120%").attr("height", "125%")
    .append("feDropShadow").attr("dx", 0).attr("dy", 1.5)
    .attr("stdDeviation", 2.5).attr("flood-color", C.shadow);
  return id;
}

function mkBg(g: G, cx: number, cy: number, c: CardConfig, fid: string) {
  g.append("rect").attr("x", cx).attr("y", cy)
    .attr("width", c.w).attr("height", c.h).attr("rx", c.r)
    .attr("fill", C.cardBg).attr("stroke", C.cardBdr)
    .attr("stroke-width", 1).attr("filter", `url(#${fid})`);
}

function mkPhoto(g: G, defs: Defs, uid: string, src: string, x: number, y: number, s: number, r: number) {
  const cid = `cp-${uid}`;
  defs.append("clipPath").attr("id", cid).append("rect")
    .attr("x", x).attr("y", y).attr("width", s).attr("height", s).attr("rx", r);
  g.append("image").attr("href", src).attr("x", x).attr("y", y)
    .attr("width", s).attr("height", s)
    .attr("preserveAspectRatio", "xMidYMid slice").attr("clip-path", `url(#${cid})`);
  g.append("rect").attr("x", x).attr("y", y).attr("width", s).attr("height", s)
    .attr("rx", r).attr("fill", "none").attr("stroke", "#e5e7eb").attr("stroke-width", .6);
}

// ── Layout: VERTICAL (gen 0–1) ───────────────────────────────

function drawVertical(g: G, defs: Defs, n: TreeNode, c: CardConfig, uid: string) {
  const cx = -c.w / 2, cy = -c.h / 2;
  const nameMax = mc(c.w - 14, c.nameFs);
  const subMax = mc(c.w - 14, c.subFs);
  const ps = c.photoSize;
  const t = titlesStr(n);
  const loc = locationStr(n);

  // Measure text block height below photo
  let textH = c.lineH; // name (always)
  if (n.color) textH += c.lineH;
  if (loc) textH += c.lineH;
  if (n.coi != null) textH += c.lineH;

  // Total content = photo + gap + text
  const contentH = ps + 6 + textH;

  // Photo starts so that photo+text block is vertically centered
  const photoY = cy + (c.h - contentH) / 2;

  // Titles — centered between card top and photo top
  if (t) {
    const titleY = cy + (photoY - cy) / 2 + c.titleFs / 3;
    g.append("text").attr("x", cx + c.w / 2).attr("y", titleY)
      .attr("text-anchor", "middle").attr("font-size", c.titleFs)
      .attr("font-weight", "400").attr("fill", C.title)
      .text(truncate(t, mc(c.w - 20, c.titleFs)));
  }

  // Photo — centered horizontally
  mkPhoto(g, defs, uid, resolvePhoto(n.img), cx + (c.w - ps) / 2, photoY, ps, 7);

  // Text below photo
  let y = photoY + ps + 6 + c.lineH;

  // Name + sex
  g.append("text").attr("x", cx + c.w / 2).attr("y", y)
    .attr("text-anchor", "middle").attr("font-size", c.nameFs)
    .attr("font-weight", "600").attr("fill", C.name)
    .text(truncate(n.name + sexSuffix(n.sex), nameMax));
  y += c.lineH;

  // Color
  if (n.color) {
    g.append("text").attr("x", cx + c.w / 2).attr("y", y)
      .attr("text-anchor", "middle").attr("font-size", c.subFs).attr("fill", C.text)
      .text(truncate(n.color, subMax));
    y += c.lineH;
  }

  // Location + year
  if (loc) {
    g.append("text").attr("x", cx + c.w / 2).attr("y", y)
      .attr("text-anchor", "middle").attr("font-size", c.subFs).attr("fill", C.text)
      .text(truncate(loc, subMax));
    y += c.lineH;
  }

  // COI
  if (n.coi != null) {
    g.append("text").attr("x", cx + c.w / 2).attr("y", y)
      .attr("text-anchor", "middle").attr("font-size", c.subFs).attr("fill", C.muted)
      .text(`COI ${n.coi.toFixed(2)} %`);
  }
}

// ── Layout: HORIZONTAL (gen 2-3) ───────────────────────────────

function drawHoriz(g: G, defs: Defs, n: TreeNode, c: CardConfig, uid: string) {
  const cx = -c.w / 2, cy = -c.h / 2;
  const pad = 7, ps = c.photoSize;
  mkPhoto(g, defs, uid, resolvePhoto(n.img), cx + pad, cy + (c.h - ps) / 2, ps, 6);

  const tx = cx + pad + ps + 8;
  const tw = cx + c.w - tx - 14;
  const nm = mc(tw, c.nameFs), sm = mc(tw, c.subFs);
  let ty = cy + 17;

  const t = titlesStr(n);
  if (t) {
    g.append("text").attr("x", tx).attr("y", ty).attr("font-size", c.titleFs)
      .attr("font-weight", "400").attr("fill", C.title)
      .text(truncate(t, mc(tw, c.titleFs)));
    ty += c.lineH;
  }
  g.append("text").attr("x", tx).attr("y", ty).attr("font-size", c.nameFs)
    .attr("font-weight", "600").attr("fill", C.name)
    .text(truncate(n.name + sexSuffix(n.sex), nm));
  ty += c.lineH;
  if (n.color) {
    g.append("text").attr("x", tx).attr("y", ty).attr("font-size", c.subFs)
      .attr("fill", C.text).text(truncate(n.color, sm));
    ty += c.lineH;
  }
  const loc = locationStr(n);
  if (loc) {
    g.append("text").attr("x", tx).attr("y", ty).attr("font-size", c.subFs)
      .attr("fill", C.text).text(truncate(loc, sm));
  }
}

// ── Layout: HCOMPACT (gen 4) ─────────────────────────────────

function drawHCompact(g: G, defs: Defs, n: TreeNode, c: CardConfig, uid: string) {
  const cx = -c.w / 2, cy = -c.h / 2;
  const pad = 5, ps = c.photoSize;
  mkPhoto(g, defs, uid, resolvePhoto(n.img), cx + pad, cy + (c.h - ps) / 2, ps, 5);

  const tx = cx + pad + ps + 6;
  const tw = cx + c.w - tx - 12;
  let ty = cy + 15;

  const t = titlesStr(n);
  if (t) {
    g.append("text").attr("x", tx).attr("y", ty).attr("font-size", c.titleFs)
      .attr("font-weight", "400").attr("fill", C.title)
      .text(truncate(t, mc(tw, c.titleFs)));
    ty += c.lineH;
  }
  g.append("text").attr("x", tx).attr("y", ty).attr("font-size", c.nameFs)
    .attr("font-weight", "600").attr("fill", C.name)
    .text(truncate(n.name + sexSuffix(n.sex), mc(tw, c.nameFs)));
  ty += c.lineH;
  const loc = locationStr(n);
  if (loc) {
    g.append("text").attr("x", tx).attr("y", ty).attr("font-size", c.subFs)
      .attr("fill", C.text).text(truncate(loc, mc(tw, c.subFs)));
  }
}

// ── Layout: TEXTONLY (gen 5+) ────────────────────────────────

function drawText(g: G, n: TreeNode, c: CardConfig) {
  const cx = -c.w / 2, cy = -c.h / 2;
  g.append("text").attr("x", cx + 7).attr("y", cy + c.h / 2 + 3)
    .attr("font-size", c.nameFs).attr("font-weight", "600")
    .attr("fill", C.name).attr("dominant-baseline", "middle")
    .text(truncate(n.name + sexSuffix(n.sex), mc(c.w - 22, c.nameFs)));
}

// ── Dispatcher ───────────────────────────────────────────────

function drawCard(g: G, defs: Defs, n: TreeNode, depth: number, uid: string) {
  const c = getConfig(depth);
  const cx = -c.w / 2, cy = -c.h / 2;
  mkBg(g, cx, cy, c, mkShadow(defs, uid));
  if (c.layout === "vertical")   drawVertical(g, defs, n, c, uid);
  else if (c.layout === "horizontal") drawHoriz(g, defs, n, c, uid);
  else if (c.layout === "hcompact")   drawHCompact(g, defs, n, c, uid);
  else drawText(g, n, c);
}

// ═══════════════════════════════════════════════════════════════
// 7. LAYOUT
// ═══════════════════════════════════════════════════════════════

const MIN_GEN = 3, MAX_GEN = 6;
// const H_GAP = 12;
const V_GAP = 46;
const PAD = { top: 12, bottom: 12, left: 8, right: 12 };

// ═══════════════════════════════════════════════════════════════
// 8. COMPONENT
// ═══════════════════════════════════════════════════════════════

export default function Pedigree() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const numId = Number(id);

  const [depth, setDepth] = useState(3);

  const { data: response, isLoading: loading, error: fetchError } = useDogsPedigreeRetrieve(
    numId,
    { generations: depth },
    { query: { enabled: !!id && !isNaN(numId) } },
  );

  // Сгенерированный тип Pedigree не поддерживает рекурсию (sire/dam: string),
  // но API реально возвращает вложенные объекты — кастуем к PedigreeNode
  const pedigreeData = response?.data as unknown as PedigreeNode | undefined;
  const error = fetchError ? "Ошибка загрузки" : null;
  const dogName = pedigreeData?.display_name || pedigreeData?.registered_name || "";
  const rawData = useMemo(() => pedigreeData ? convertNode(pedigreeData) : null, [pedigreeData]);

  const frameRef  = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const svgRef    = useRef<SVGSVGElement>(null);
  const gRef      = useRef<SVGGElement>(null);

  const renderTree = useCallback(() => {
    const frame = frameRef.current, scroll = scrollRef.current;
    const svgEl = svgRef.current, gEl = gRef.current;
    if (!frame || !scroll || !svgEl || !gEl || !rawData) return;

    const svg = d3.select(svgEl), gSel = d3.select(gEl);
    const frameW = frame.clientWidth;

    let maxD = 0;
    const wd = (n: TreeNode, d: number) => { if (d > maxD) maxD = d; n.children?.forEach(c => wd(c, d + 1)); };
    wd(rawData, 0);

    const rc = getConfig(0);

    // ── Per-depth column positions ─────────────────────────────
    // Gap between card edges SHRINKS with depth — root area is
    // spacious, deep ancestors are packed tight (like breedarchive).
    const GAPS = [20, 20, 20, 20, 20, 20, 20]; // gap at depth 0→1, 1→2, 2→3, ...
    const colX: number[] = [0];
    for (let d = 1; d <= maxD; d++) {
      const prevW = getConfig(d - 1).w;
      const curW = getConfig(d).w;
      const gap = GAPS[d - 1] ?? 6;
      colX[d] = colX[d - 1] + prevW / 2 + gap + curW / 2;
    }

    // d3 tree for vertical positioning only
    const maxW = Math.max(...Object.values(CONFIGS).map(c => c.w));
    // const root = d3.tree<TreeNode>()
    //   .nodeSize([rc.h + V_GAP, 1])
    const smallestH = Math.min(...Object.values(CONFIGS).map(c => c.h));
    const root = d3.tree<TreeNode>()
      .nodeSize([smallestH + V_GAP, 1])
      .separation((a, b) => {
        const base = a.parent === b.parent ? 1 : 1.05;
        // At each depth, cards have different heights.
        // We need enough space so tall cards don't overlap.
        // nodeSize vertical step = smallestH + V_GAP.
        // Required separation = maxCardHeight / step.
        const step = smallestH + V_GAP;
        const aH = getConfig(a.depth).h;
        const bH = getConfig(b.depth).h;
        const needed = Math.max(aH, bH) / step * 1.05;
        return Math.max(base, needed);
      })(d3.hierarchy(rawData));
      // .separation((a, b) => a.parent === b.parent ? 1 : 1.02)(d3.hierarchy(rawData));

    // Override d3's y with our compressed column positions
    const nodes = root.descendants();
    nodes.forEach(n => { n.y = colX[n.depth] ?? colX[colX.length - 1]; });

    const links = root.links();
    const xs = nodes.map(n => n.x);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const maxY = Math.max(...nodes.map(n => n.y));
    const hw = maxW / 2;

    const svgH = Math.max(300, maxX - minX + rc.h + PAD.top + PAD.bottom);
    const bt = PAD.top + rc.h / 2 - minX;
    const cw = PAD.left + hw + maxY + hw + PAD.right;
    const scroll_ = cw > frameW;

    gSel.selectAll("*").remove();
    svg.selectAll("defs").remove();
    const defs = svg.insert<SVGDefsElement>("defs", ":first-child");

    if (scroll_) {
      frame.classList.add("is-scroll");
      scroll.style.width = `${cw}px`;
      svg.attr("width", cw).attr("height", svgH).attr("viewBox", null);
    } else {
      frame.classList.remove("is-scroll");
      scroll.style.width = "100%";
      svg.attr("width", frameW).attr("height", svgH)
        .attr("viewBox", `0 0 ${cw} ${svgH}`)
        .attr("preserveAspectRatio", "xMinYMin meet");
    }

    links.forEach(l => {
      const sc = getConfig(l.source.depth), tc = getConfig(l.target.depth);
      const x0 = PAD.left + hw + l.source.y + sc.w / 2;
      const y0 = bt + l.source.x;
      const x1 = PAD.left + hw + l.target.y - tc.w / 2;
      const y1 = bt + l.target.x;
      const mx = (x0 + x1) / 2;
      gSel.append("path").attr("class", "pdg-link")
        .attr("d", `M${x0},${y0} H${mx} V${y1} H${x1}`);
    });

    nodes.forEach((nd, i) => {
      const ng = gSel.append<SVGGElement>("g").attr("class", "pdg-node")
        .attr("transform", `translate(${PAD.left + hw + nd.y},${bt + nd.x})`)
        .style("cursor", "pointer")
        .on("click", () => navigate(`/archive/dog/${nd.data.id}`));
      drawCard(ng as any, defs as any, nd.data, nd.depth, `c${i}`);
    });
  }, [rawData, navigate]);

  useEffect(() => {
    renderTree();
    const f = frameRef.current;
    if (!f) return;
    const ro = new ResizeObserver(renderTree);
    ro.observe(f);
    return () => ro.disconnect();
  }, [renderTree]);


  return (
    <div className="pedigree-page">
      <Breadcrumb
        title={loading ? "Загрузка…" : dogName || "Родословная"}
        items={[{ label: "Главная", to: "/" }, { label: "Архив", to: "/archive" }, { label: "Родословная" }]}
      />
      <div className="pedigree-controls">
        <div className="pedigree-gen-tabs" role="group">
          <span className="pedigree-gen-label">Глубина:</span>
          {Array.from({ length: MAX_GEN - MIN_GEN + 1 }, (_, i) => MIN_GEN + i).map(n => (
            <button key={n} className={`pedigree-gen-tab${depth === n ? " is-active" : ""}`}
              onClick={() => setDepth(n)}>{n}</button>
          ))}
        </div>
      </div>
      {error && <div className="pedigree-error">⚠️ {error}</div>}
      {loading && <div className="pedigree-loading"><div className="pedigree-spinner" /><span>Загрузка…</span></div>}
      {!loading && !error && rawData && (
        <>
          <div className="pedigree-frame" ref={frameRef}>
            <div className="pedigree-scroll" ref={scrollRef}>
              <svg ref={svgRef} className="pedigree-svg" role="img"><g ref={gRef} /></svg>
            </div>
          </div>
          <div className="pedigree-scroll-hint">← прокрутите →</div>
        </>
      )}
    </div>
  );
}
