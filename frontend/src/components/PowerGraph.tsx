import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import type { GraphData } from "@/types";

/** Grafo de poder (Cytoscape). Verificado = línea sólida; hipótesis IA = punteada. */
export function PowerGraph({ data }: { data: GraphData }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...data.nodes.map((n) => ({ data: { id: n.id, label: n.name ?? n.id, kind: n.label } })),
        ...data.edges.map((e) => ({
          data: { source: e.source, target: e.target, label: e.type, hyp: e.hypothesis ? 1 : 0 },
        })),
      ],
      style: [
        { selector: "node", style: { label: "data(label)", "background-color": "#2563eb", color: "#e5e7eb", "font-size": "9px" } },
        { selector: 'node[kind = "Entity"]', style: { "background-color": "#D91023" } },
        { selector: 'node[kind = "Company"]', style: { "background-color": "#7c3aed" } },
        { selector: 'node[kind = "Contract"]', style: { "background-color": "#0891b2", shape: "diamond" } },
        { selector: "edge", style: { width: 1, "line-color": "#4b5563", "curve-style": "bezier", "target-arrow-shape": "triangle", "target-arrow-color": "#4b5563" } },
        { selector: "edge[hyp = 1]", style: { "line-style": "dashed", "line-color": "#d97706" } },
      ],
      layout: { name: "cose", animate: false },
    });
    return () => cy.destroy();
  }, [data]);

  return <div ref={ref} className="h-[520px] w-full rounded-lg border border-gray-800 bg-peru-panel" />;
}
