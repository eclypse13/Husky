import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./Pedigree.css";

type DogNode = {
  name: string;
  img?: string;
  title?: string;
  children?: DogNode[];
};

const baseTree: DogNode = {
  name: "Arctic Storm's Thunder King",
  img: "https://karnovandakennels.com/albumsh/girlalbums/photosRheannan/files/page203-1001-full.jpg",
  title: "Ch. BIS",
  children: [
    {
      name: "Storm",
      img: "https://karnovandakennels.com/albumsh/boyalbums/photosXeke/files/page147-1003-full.jpg",
      title: "Ch.",
      children: new Array(2).fill({ name: "..." }),
    },
    {
      name: "Ice Queen",
      img: "https://karnovandakennels.com/albumsh/girlalbums/photosSnowy/files/page144-1000-full.jpg",
      title: "BIS",
      children: new Array(2).fill({ name: "..." }),
    },
  ],
};

function expandTree(node: DogNode, level: number, maxLevel: number): DogNode {
  if (level >= maxLevel) return node;
  return {
    ...node,
    children: [
      expandTree({ name: `${node.name} ♂` }, level + 1, maxLevel),
      expandTree({ name: `${node.name} ♀` }, level + 1, maxLevel),
    ],
  };
}

const HEIGHT_BY_DEPTH: Record<number, number> = {
  3: 400,
  4: 800,
  5: 1400,
  6: 2300,
};

export default function Pedigree() {
  const [depth, setDepth] = useState<number>(3);
  const frameRef = useRef<HTMLDivElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const gRef = useRef<SVGGElement | null>(null);

  const data = useMemo<DogNode>(() => expandTree(baseTree, 1, depth), [depth]);

  useEffect(() => {
    const frame = frameRef.current;
    const scroll = scrollRef.current;
    const svgEl = svgRef.current;
    const gEl = gRef.current;
    if (!frame || !scroll || !svgEl || !gEl) return;

    const svg = d3.select(svgEl);
    const g = d3.select(gEl);

    const render = () => {
      const frameW = frame.clientWidth;

      // Высота полотна
      const height = HEIGHT_BY_DEPTH[depth];

      // Размеры узла
      const nodeW = 150;
      const nodeH = 56;
      const imgSize = 36;

      const hGap = 80 - (depth - 3) * 10;
      const vGap = 15 - (depth - 3) * 8;

      // Ширина контента
      const leftPad = 100, rightPad = 100;
      const columns = depth;
      const contentW = leftPad + (columns - 1) * (nodeW + hGap) + nodeW + rightPad;

      const needScroll = contentW > frameW;

      // Очистка
      g.selectAll("*").remove();

      if (needScroll) {
        frame.classList.add("is-scroll");
        scroll.style.width = `${contentW}px`;
        svg.attr("width", contentW).attr("height", height).attr("viewBox", null);
      } else {
        frame.classList.remove("is-scroll");
        scroll.style.width = "100%";
        svg
          .attr("width", frameW)
          .attr("height", height)
          .attr("viewBox", `0 0 ${contentW} ${height}`)
          .attr("preserveAspectRatio", "xMinYMin meet");
      }

      const rootData = d3.hierarchy<DogNode>(data);
      const layout = d3.tree<DogNode>().nodeSize([vGap + nodeH, nodeW + hGap]);
      const root = layout(rootData) as d3.HierarchyPointNode<DogNode>;

      const nodes = root.descendants() as d3.HierarchyPointNode<DogNode>[];
      const [minX, maxX] = d3.extent(nodes, (d) => d.x) as [number, number];
      const padV = 30; // Вертикальные внутренние отступы
      // Базовый топ так, чтобы корень был в центре высоты
      let baseTop = Math.round(height / 2 - root.x);
      const minTop = padV - minX - nodeH / 2;                         // Самый верхний узел + отступ
      const maxTop = height - (maxX + nodeH / 2) - padV;              // Самый нижний узел + отступ
      baseTop = Math.max(minTop, Math.min(maxTop, baseTop));

      const TX = (d: d3.HierarchyPointNode<DogNode>) =>
        `translate(${leftPad + d.y}, ${baseTop + d.x})`;

      // Рёбра
      const links = root.links() as d3.HierarchyPointLink<DogNode>[];
      g.selectAll<SVGPathElement, d3.HierarchyPointLink<DogNode>>(".pdg-link")
        .data(links)
        .join("path")
        .attr("class", "pdg-link")
        .attr("d", (d) => {
          const s = d.source as d3.HierarchyPointNode<DogNode>;
          const t = d.target as d3.HierarchyPointNode<DogNode>;
          const x0 = leftPad + s.y, y0 = baseTop + s.x;
          const x1 = leftPad + t.y, y1 = baseTop + t.x;
          const midX = (x0 + x1) / 2;
          return `M${x0},${y0}H${midX}V${y1}H${x1}`;
        });

      // Узлы
      const node = g
        .selectAll<SVGGElement, d3.HierarchyPointNode<DogNode>>(".pdg-node")
        .data(nodes)
        .join("g")
        .attr("class", "pdg-node")
        .attr("transform", TX);

      node
        .append("rect")
        .attr("x", -nodeW / 2)
        .attr("y", -nodeH / 2)
        .attr("width", nodeW)
        .attr("height", nodeH)
        .attr("rx", 12)
        .attr("ry", 12);

      node
        .append("foreignObject")
        .attr("x", -nodeW / 2 + 5)
        .attr("y", -nodeH / 2 + 4)
        .attr("width", nodeW - 10)
        .attr("height", nodeH - 8)
        .html((d) => {
          const img = d.data.img
            ? `<img src="${d.data.img}" class="pdg-img" style="width:${imgSize}px;height:${imgSize}px" />`
            : "";
          const title = d.data.title ? `<div class="pdg-title">${d.data.title}</div>` : "";
          return `
            <div class="pdg-fo">
              ${img}
              <div class="pdg-text">
                <div class="pdg-name">${d.data.name}</div>
                ${title}
              </div>
            </div>
          `;
        });
    };

    render();
    const ro = new ResizeObserver(render);
    ro.observe(frame);
    return () => ro.disconnect();
  }, [data, depth]);

  return (
    <div className="pedigree-page">
      <Breadcrumb
        title="Родословная"
        items={[{ label: "Главная", to: "/" }, { label: "Родословная" }]}
      />

      <section className="pedigree-header">
        <h1 className="pedigree-title">
          Родословная:{" "}
          <span className="pedigree-title-accent">Arctic Storm&apos;s Thunder King</span>
        </h1>
        <p className="pedigree-sub">
          Выберите глубину поколений — дерево перестроится автоматически.
        </p>

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
      </section>

      <section className="pedigree-frame" ref={frameRef} aria-label="Генеалогическое дерево">
        <div className="pedigree-scroll" ref={scrollRef}>
          <svg ref={svgRef} className="pedigree-svg" role="img" aria-hidden="false">
            <g ref={gRef} />
          </svg>
        </div>
      </section>
    </div>
  );
}
