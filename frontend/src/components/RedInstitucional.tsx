import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { staticData } from "@/lib/api";

interface Node { id: string; label: string; deg: number; cat: string }
interface Edge { a: string; b: string; w: number; quienes: string[] }
interface Red { nodes: Node[]; edges: Edge[] }

const CAT_COLOR: Record<string, string> = {
  "Ministerio": "#e11d2a",
  "Organismo constitucional": "#f59e0b",
  "Regulador/Superintendencia": "#22d3ee",
  "Justicia/Fiscalía": "#a78bfa",
  "Salud": "#22c55e",
  "Educación": "#4f8cff",
  "Universidad": "#3b82f6",
  "Gobierno Regional": "#fb923c",
  "Municipalidad": "#9aa7b8",
  "Empresa pública": "#7c3aed",
  "Organismo público": "#64748b",
};
const color = (cat: string) => CAT_COLOR[cat] ?? "#64748b";

export function RedInstitucional() {
  const ref = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [data, setData] = useState<Red | null>(null);
  const [sel, setSel] = useState<{ a: string; b: string; w: number; quienes: string[] } | null>(null);
  const [filtro, setFiltro] = useState<string>("");

  useEffect(() => {
    staticData.redesEntidades().then((d) => setData(d as Red)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!ref.current || !data) return;
    const nom: Record<string, string> = {};
    data.nodes.forEach((n) => (nom[n.id] = n.label));
    const maxDeg = Math.max(...data.nodes.map((n) => n.deg), 1);
    const umbral = [...data.nodes].sort((a, b) => b.deg - a.deg)[Math.min(21, data.nodes.length - 1)]?.deg ?? 0;
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...data.nodes.map((n) => ({
          data: { id: n.id, label: n.label, full: n.label, cat: n.cat, color: color(n.cat), size: 12 + (n.deg / maxDeg) * 38, big: n.deg >= umbral ? 1 : 0 },
        })),
        ...data.edges.map((e, i) => ({ data: { id: `x${i}`, source: e.a, target: e.b, w: Math.min(8, 1 + Math.log(e.w)) } })),
      ],
      style: [
        { selector: "node", style: { width: "data(size)", height: "data(size)", "background-color": "data(color)", "border-width": 0 } },
        { selector: 'node[big = 1]', style: { label: "data(label)", color: "#cdd8e6", "font-size": "9px", "text-wrap": "wrap", "text-max-width": "84px", "text-valign": "bottom", "text-margin-y": 2 } },
        { selector: "node.hl", style: { label: "data(full)", "border-width": 3, "border-color": "#fff", "z-index": 99, color: "#fff", "font-size": "11px" } },
        { selector: "node.dim", style: { opacity: 0.08 } },
        { selector: "edge", style: { width: "data(w)", "line-color": "#64748b", "line-opacity": 0.28, "curve-style": "bezier" } },
        { selector: "edge.hl", style: { "line-opacity": 0.95, "line-color": "#e11d2a", width: 3 } },
        { selector: "edge.dim", style: { opacity: 0.04 } },
      ],
      layout: { name: "cose", animate: false, nodeRepulsion: 11000, idealEdgeLength: 95 },
    });
    cyRef.current = cy;
    cy.on("mouseover", "node", (e) => { e.target.addClass("hl"); e.target.connectedEdges().addClass("hl"); e.target.neighborhood("node").addClass("hl"); });
    cy.on("mouseout", () => cy.elements().removeClass("hl"));
    cy.on("tap", "edge", (e) => {
      const d = e.target.data();
      const ed = data.edges.find((x) => (x.a === d.source && x.b === d.target) || (x.a === d.target && x.b === d.source));
      if (ed) setSel({ a: nom[ed.a] ?? ed.a, b: nom[ed.b] ?? ed.b, w: ed.w, quienes: ed.quienes });
    });
    cy.on("tap", "node", (e) => { window.location.hash = `#/entidad/${e.target.id()}`; });
    return () => cy.destroy();
  }, [data]);

  // aplicar filtro por categoría
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass("dim");
      if (filtro) {
        cy.nodes().forEach((n) => { if (n.data("cat") !== filtro) n.addClass("dim"); });
        cy.edges().forEach((e) => { if (e.source().hasClass("dim") || e.target().hasClass("dim")) e.addClass("dim"); });
      }
    });
  }, [filtro, data]);

  const cats = data ? [...new Set(data.nodes.map((n) => n.cat))].sort() : [];

  return (
    <div>
      <div className="mb-3 glass flex flex-wrap items-center gap-x-5 gap-y-2 p-3 text-xs">
        <span className="font-semibold text-ink">Cómo leer:</span>
        <span className="text-ink-soft">cada bola = una <b>entidad</b> (color = tipo, tamaño = personal compartido)</span>
        <span className="text-ink-soft"><span className="text-peru-red">━</span> línea = <b>personas en común</b></span>
        <span className="text-ink-soft">🖱️ <b>clic en una línea</b> → ve quiénes · clic en una bola → abre la entidad</span>
      </div>

      {/* Filtro por tipo (botones) */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        <button onClick={() => setFiltro("")} className={`rounded-full border px-3 py-1 text-[11px] font-medium transition ${!filtro ? "border-peru-red/50 bg-peru-red/15 text-peru-redsoft" : "border-surface/10 bg-surface/[0.03] text-ink-soft hover:text-ink"}`}>Todos</button>
        {cats.map((c) => (
          <button key={c} onClick={() => setFiltro(filtro === c ? "" : c)}
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition ${filtro === c ? "border-ink/40 bg-surface/10 text-ink" : "border-surface/10 bg-surface/[0.03] text-ink-soft hover:text-ink"}`}>
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: color(c) }} /> {c}
          </button>
        ))}
      </div>

      <div ref={ref} className="h-[560px] w-full rounded-xl border border-surface/10 bg-bg-deep" />

      {sel && (
        <div className="mt-3 glass p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="text-sm text-ink">
              <b className="text-peru-redsoft">{fmtN(sel.w)}</b> personas en común entre<br />
              <span className="text-accent-blue">{sel.a}</span> ↔ <span className="text-accent-violet">{sel.b}</span>
            </div>
            <button onClick={() => setSel(null)} className="text-ink-mute hover:text-ink">✕</button>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {sel.quienes.map((q, i) => (
              <span key={i} className="rounded-md border border-surface/10 bg-surface/[0.04] px-2 py-0.5 text-xs text-ink-soft">{q}</span>
            ))}
            {sel.w > sel.quienes.length && <span className="px-2 py-0.5 text-xs text-ink-faint">+{sel.w - sel.quienes.length} más</span>}
          </div>
        </div>
      )}

      <div className="mt-3 rounded-xl border border-accent-amber/30 bg-accent-amber/10 p-3 text-[11px] text-ink-soft">
        ⚠️ <b>No implica doble empleo ni irregularidad.</b> El vínculo es por <b>coincidencia de nombre</b> (no DNI): el
        89% son <b>rotaciones</b> (cambio de trabajo en distintos períodos) y el resto homónimos o entidades renombradas.
        La relación institucional formal es la del ROF; cruzar por DNI está en el roadmap.
      </div>
    </div>
  );
}

function fmtN(n: number) { return new Intl.NumberFormat("es-PE").format(n); }
