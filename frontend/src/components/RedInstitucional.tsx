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
    // mostrar etiqueta solo en los 22 nodos más conectados (los hubs); el resto al pasar el cursor
    const umbral = [...data.nodes].sort((a, b) => b.deg - a.deg)[Math.min(21, data.nodes.length - 1)]?.deg ?? 0;
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...data.nodes.map((n) => ({
          data: { id: n.id, label: n.label, full: n.label, deg: n.deg, size: 12 + (n.deg / maxDeg) * 38, big: n.deg >= umbral ? 1 : 0 },
        })),
        ...data.edges.map((e, i) => ({ data: { id: `x${i}`, source: e.a, target: e.b, w: Math.min(8, 1 + Math.log(e.w)) } })),
      ],
      style: [
        { selector: "node", style: { width: "data(size)", height: "data(size)", "background-color": "#4f8cff", "border-width": 0 } },
        { selector: 'node[big = 1]', style: { label: "data(label)", color: "#cdd8e6", "font-size": "9px", "text-wrap": "wrap", "text-max-width": "84px", "text-valign": "bottom", "text-margin-y": 2 } },
        { selector: "node.hl", style: { label: "data(full)", "background-color": "#e11d2a", "z-index": 99, color: "#fff", "font-size": "11px" } },
        { selector: "edge", style: { width: "data(w)", "line-color": "#e11d2a", "line-opacity": 0.3, "curve-style": "bezier" } },
        { selector: "edge.hl", style: { "line-opacity": 0.9, "line-color": "#ff5d6c" } },
      ],
      layout: { name: "cose", animate: false, nodeRepulsion: 11000, idealEdgeLength: 95 },
    });
    cy.on("mouseover", "node", (e) => { e.target.addClass("hl"); e.target.connectedEdges().addClass("hl"); e.target.neighborhood("node").addClass("hl"); });
    cy.on("mouseout", "node", () => { cy.elements().removeClass("hl"); });
    cy.on("tap", "node", (e) => { window.location.hash = `#/entidad/${e.target.id()}`; });
    return () => cy.destroy();
  }, [data]);

  return (
    <div>
      {/* Cómo leer */}
      <div className="mb-3 glass flex flex-wrap items-center gap-x-5 gap-y-2 p-3 text-xs">
        <span className="font-semibold text-ink">Cómo leer:</span>
        <span className="flex items-center gap-1.5"><span className="inline-block h-3 w-3 rounded-full bg-accent-blue" /> <span className="text-ink-soft">cada bola = una <b>entidad</b> (más grande = comparte más personal)</span></span>
        <span className="flex items-center gap-1.5"><span className="inline-block h-0.5 w-5 bg-peru-red" /> <span className="text-ink-soft">línea = <b>personas en común</b> (más gruesa = más)</span></span>
        <span className="flex items-center gap-1.5">🖱️ <span className="text-ink-soft">pasa el cursor para resaltar · <b>clic abre la entidad</b></span></span>
      </div>
      <div ref={ref} className="h-[560px] w-full rounded-xl border border-surface/10 bg-bg-deep" />
      <p className="mt-2 text-[11px] text-ink-faint">
        Las conexiones más fuertes suelen ser <b>programas afines</b> (ej. los del MIDIS: Qali Warma, Cuna Más, Juntos)
        o entidades con el mismo personal administrativo. No implica irregularidad — solo muestra vínculos de personal.
      </p>
    </div>
  );
}
