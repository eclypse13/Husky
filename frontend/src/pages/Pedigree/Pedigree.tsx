import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import "./Pedigree.css";

/** Твои данные из html-файла */
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

/** Разворачиваем «♂/♀» как в html-демо (только подписи глубже корня) */
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

/** высота полотна по глубине — как в html */
const HEIGHT_BY_DEPTH: Record<number, number> = {
  3: 800,
  4: 1300,
  5: 2000,
  6: 2600,
};

export default function Pedigree() {
  const [depth, setDepth] = useState<number>(3);
  const frameRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const gRef = useRef<SVGGElement | null>(null);

  /** подготовим данные один раз на смену depth */
  const data = useMemo<DogNode>(() => expandTree(baseTree, 1, depth), [depth]);

  useEffect(() => {
    const wrap = frameRef.current;
    const svg = d3.select(svgRef.current);
    const g = d3.select(gRef.current);
    if (!wrap || !svgRef.current || !gRef.current) return;

    // функция перерисовки — зависит от ширины контейнера
    const render = () => {
      const width = wrap.clientWidth;                // ширина карточки
      const height = HEIGHT_BY_DEPTH[depth] ?? 1600; // как в html-версии
      const marginLeft = 16;                         // чуть воздуха слева

      // чистим
      g.selectAll("*").remove();

      // холст
      svg.attr("width", width).attr("height", height)
         .attr("viewBox", `0 0 ${width} ${height}`)
         .attr("preserveAspectRatio", "xMinYMin meet");

      // раскладка дерева: по X — высота, по Y — ширина минус поля
      const innerW = Math.max(700, width - 2 * marginLeft);
      const hRoot = d3.hierarchy<DogNode>(data);
      const layout = d3.tree<DogNode>().size([height - 100, innerW - 200]);
      const root = layout(hRoot) as d3.HierarchyPointNode<DogNode>;
      const treeLayout = d3.tree<DogNode>().size([height - 100, innerW - 200]); // -200, чтобы карточки не прилипали к правой границе
      treeLayout(root);

      // переносим координаты: меняем местами x/y, чуть двигаем вправо/вниз
      const tx = (d: d3.HierarchyPointNode<DogNode>) =>
        `translate(${d.y + 100}, ${d.x + 50})`;

      // рёбра (ортогональные — как в html)
      g.selectAll<SVGPathElement, d3.HierarchyPointLink<DogNode>>(".pdg-link")
        .data(root.links())
        .join("path")
        .attr("class", "pdg-link")
        .attr("d", (d) => {
          const x0 = d.source.y + 100;
          const y0 = d.source.x + 50;
          const x1 = d.target.y + 100;
          const y1 = d.target.x + 50;
          const midX = (x0 + x1) / 2;
          return `M${x0},${y0}H${midX}V${y1}H${x1}`;
        });

      // узлы
      const node = g
        .selectAll<SVGGElement, d3.HierarchyPointNode<DogNode>>(".pdg-node")
        .data(root.descendants())
        .join("g")
        .attr("class", "pdg-node")
        .attr("transform", tx);

      // прямоугольник карточки (как в html: 160x60, скругление 12)
      node
        .append("rect")
        .attr("x", -80)
        .attr("y", -30)
        .attr("width", 160)
        .attr("height", 60)
        .attr("rx", 12)
        .attr("ry", 12);

      // содержимое карточки foreignObject — фото + имя + титул
      node
        .append("foreignObject")
        .attr("x", -75)
        .attr("y", -26)
        .attr("width", 150)
        .attr("height", 52)
        .html((d) => {
          const img = d.data.img
            ? `<img src="${d.data.img}" class="pdg-img" />`
            : "";
          const title = d.data.title
            ? `<div class="pdg-title">${d.data.title}</div>`
            : "";
          return `
            <div class="pdg-fo">
              ${img}
              <div class="pdg-text">
                <div>${d.data.name}</div>
                ${title}
              </div>
            </div>
          `;
        });
    };

    // первичная отрисовка
    render();

    // ресайз-наблюдатель, чтобы svg всегда вписывался в карточку
    const ro = new ResizeObserver(() => render());
    ro.observe(wrap);

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
        <svg ref={svgRef} className="pedigree-svg" role="img" aria-hidden="false">
          <g ref={gRef} />
        </svg>
      </section>
    </div>
  );
}
