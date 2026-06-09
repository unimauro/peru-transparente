import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { staticData } from "@/lib/api";

interface Red {
  nodes: { id: string; label: string; deg: number }[];
  edges: { a: string; b: string; w: number }[];
}

export function RedInstitucional() {
  const ref = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<Red | null>(null);

  useEffect(() => {
    staticData.redesEntidades().then((d) => setData(d as Red)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!ref.current || !data) return;
    const maxDeg = Math.max(...data.nodes.map((n) => n.deg), 1);
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...data.nodes.map((n) => ({ data: { id: n.id, label: n.label, deg: n.deg, size: 12 + (n.deg / maxDeg) * 34 } })),
        ...data.edges.map((e, i) => ({ data: { id: `x${i}`, source: e.a, target: e.b, w: Math.min(8, 1 + Math.log(e.w)) } })),
      ],
      style: [
        { selector: "node", style: { label: "data(label)", width: "data(size)", height: "data(size)", "background-color": "#4f8cff", color: "#cdd8e6", "font-size": "8px", "text-wrap": "wrap", "text-max-width": "80px", "text-valign": "bottom" } },
        { selector: "edge", style: { width: "data(w)", "line-color": "#e11d2a", "line-opacity": 0.35, "curve-style": "bezier" } },
        { selector: "node:hover", style: { "background-color": "#e11d2a" } },
      ],
      layout: { name: "cose", animate: false, nodeRepulsion: 9000, idealEdgeLength: 90 },
    });
    cy.on("tap", "node", (e) => {
      const id = e.target.id();
      window.location.hash = `#/entidad/${id}`;
    });
    return () => cy.destroy();
  }, [data]);

  if (!data) return <div className="skeleton h-[560px] w-full rounded-xl" />;
  return (
    <div>
      <div ref={ref} className="h-[560px] w-full rounded-xl border border-surface/10 bg-bg-deep" />
      <p className="mt-2 text-[11px] text-ink-faint">
        Cada nodo es una entidad (tamaño = cuántas personas comparte); cada línea roja une entidades con
        personal en común. Clic en un nodo abre la entidad. Las conexiones más fuertes suelen ser
        programas/ministerios afines (ej. los programas del MIDIS).
      </p>
    </div>
  );
}
