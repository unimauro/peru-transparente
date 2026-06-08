import type { Provenance } from "@/types";

/** Muestra fuente, fecha de captura y nivel de confianza de un dato. */
export function ProvenanceBadge({ p }: { p: Provenance }) {
  const color =
    p.confidence >= 0.85 ? "text-conf-high" : p.confidence >= 0.6 ? "text-conf-mid" : "text-conf-low";
  return (
    <span className="inline-flex items-center gap-1 text-xs text-gray-400">
      <span className={color}>●</span>
      <a href={p.source_url} target="_blank" rel="noreferrer" className="underline hover:text-gray-200">
        {p.source}
      </a>
      <span>· {new Date(p.captured_at).toLocaleDateString("es-PE")}</span>
      <span className="tabular">· conf {p.confidence.toFixed(2)}</span>
    </span>
  );
}
