import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";

// aparición: [id_entidad, entidad_abrev, cargo, regimen, sueldo]
type Ap = [string, string, string, string, number];

export function PersonaGrafo({ nombre, apariciones }: { nombre: string; apariciones: Ap[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ents = new Map<string, string>();
    apariciones.forEach((a) => ents.set(a[0], a[1]));
    const elements: cytoscape.ElementDefinition[] = [
      { data: { id: "P", label: nombre.split(",")[0], kind: "person" } },
      ...[...ents].map(([id, ab]) => ({ data: { id: `E${id}`, label: ab, kind: "entity" } })),
      ...apariciones.map((a, i) => ({
        data: { id: `e${i}`, source: "P", target: `E${a[0]}`, label: a[2].slice(0, 22) },
      })),
    ];
    const cy = cytoscape({
      container: ref.current,
      elements,
      style: [
        { selector: "node", style: { label: "data(label)", color: "#e6edf6", "font-size": "10px", "text-wrap": "wrap", "text-max-width": "90px" } },
        { selector: 'node[kind="person"]', style: { "background-color": "#e11d2a", width: 26, height: 26, "font-size": "12px", "font-weight": "bold" } },
        { selector: 'node[kind="entity"]', style: { "background-color": "#4f8cff", width: 16, height: 16, shape: "round-rectangle" } },
        { selector: "edge", style: { label: "data(label)", width: 1.5, "line-color": "#3a4760", "target-arrow-shape": "triangle", "target-arrow-color": "#3a4760", "curve-style": "bezier", "font-size": "8px", color: "#8a96a8", "text-rotation": "autorotate" } },
      ],
      layout: { name: "concentric", concentric: (n: cytoscape.NodeSingular) => (n.data("kind") === "person" ? 10 : 1), minNodeSpacing: 60, animate: false },
    });
    return () => cy.destroy();
  }, [nombre, apariciones]);

  return (
    <div>
      <div ref={ref} className="h-[340px] w-full rounded-xl border border-surface/10 bg-bg-deep" />
      <p className="mt-1.5 text-[11px] text-ink-faint">
        <span className="text-peru-redsoft">●</span> la persona · <span className="text-accent-blue">▪</span> cada entidad donde aparece · la línea muestra el cargo. Si hay 2+ entidades, esta persona conecta varias instituciones.
      </p>
    </div>
  );
}
