// Renderizador de markdown compacto y SIN dependencias para burbujas de chat.
// Los modelos (sobre todo los :free) emiten markdown aunque se les pida texto
// plano; en vez de pelear con el modelo, lo renderizamos. Maneja: **negrita**,
// *cursiva*, `código`, [texto](url), ![alt](img), rutas internas #/x, URLs
// sueltas, listas (- / *), encabezados (#) y tablas GFM (| a | b |).
//
// Patrón REUTILIZABLE: copiar este archivo a cualquier dashboard React y usar
// renderMarkdown(texto). El gateway ai.tunky.net es content-agnostic — el
// render vive en el frontend. Para apps de HTML plano, usar `marked`+DOMPurify.
import type { ReactNode } from "react";

const BASE = import.meta.env.BASE_URL;
const LINK = "text-accent-cyan underline underline-offset-2";

// ── Inline: negrita, cursiva, código, enlaces, imágenes, rutas, URLs ──────
const INLINE_RE =
  /(!\[[^\]]*\]\([^)]+\)|\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`]+`|#\/[a-z]+|https?:\/\/[^\s)]+)/g;

function inline(text: string, kp: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  INLINE_RE.lastIndex = 0;
  while ((m = INLINE_RE.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    const key = `${kp}-${i++}`;
    let mm: RegExpMatchArray | null;
    if ((mm = t.match(/^!\[([^\]]*)\]\(([^)]+)\)$/)))
      out.push(<img key={key} src={mm[2]} alt={mm[1]} loading="lazy" className="my-1 max-w-full rounded-lg" />);
    else if ((mm = t.match(/^\[([^\]]+)\]\(([^)]+)\)$/))) {
      const url = mm[2];
      const internal = url.startsWith("#/");
      out.push(
        <a key={key} href={internal ? `${BASE}${url}` : url} {...(internal ? {} : { target: "_blank", rel: "noreferrer" })} className={LINK}>
          {mm[1]}
        </a>,
      );
    } else if (t.startsWith("**")) out.push(<strong key={key} className="font-semibold text-ink">{t.slice(2, -2)}</strong>);
    else if (t.startsWith("*")) out.push(<em key={key}>{t.slice(1, -1)}</em>);
    else if (t.startsWith("`")) out.push(<code key={key} className="rounded bg-surface/10 px-1 text-[0.85em]">{t.slice(1, -1)}</code>);
    else if (t.startsWith("#/")) out.push(<a key={key} href={`${BASE}${t}`} className={LINK}>{t.replace("#/", "")}</a>);
    else out.push(<a key={key} href={t} target="_blank" rel="noreferrer" className={LINK}>enlace</a>);
    last = INLINE_RE.lastIndex;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const cells = (row: string): string[] => row.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
const isSep = (l: string | undefined): boolean => !!l && l.includes("|") && /^[\s|:-]+$/.test(l) && l.includes("-");

// ── Bloques: tablas, listas, encabezados, párrafos ────────────────────────
export function renderMarkdown(src: string): ReactNode {
  const lines = src.replace(/\r/g, "").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let b = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    // Tabla GFM: encabezado + fila separadora |---|
    if (line.includes("|") && isSep(lines[i + 1])) {
      const head = cells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) { rows.push(cells(lines[i])); i++; }
      blocks.push(
        <div key={b++} className="my-1 overflow-x-auto">
          <table className="w-full border-collapse text-[0.85em]">
            <thead>
              <tr>{head.map((c, j) => <th key={j} className="border-b border-surface/20 px-2 py-1 text-left font-semibold">{inline(c, `t${b}h${j}`)}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri}>{r.map((c, ci) => <td key={ci} className="border-b border-surface/[0.06] px-2 py-1">{inline(c, `t${b}r${ri}c${ci}`)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // Lista con viñetas
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*[-*]\s+/, "")); i++; }
      blocks.push(
        <ul key={b++} className="my-1 list-disc space-y-0.5 pl-5">
          {items.map((it, j) => <li key={j}>{inline(it, `u${b}i${j}`)}</li>)}
        </ul>,
      );
      continue;
    }

    // Encabezado
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) { blocks.push(<div key={b++} className="font-semibold text-ink">{inline(h[2], `h${b}`)}</div>); i++; continue; }

    // Párrafo (líneas consecutivas hasta blanco / bloque especial)
    const para: string[] = [];
    while (
      i < lines.length && lines[i].trim() &&
      !/^\s*[-*]\s+/.test(lines[i]) && !/^#{1,6}\s/.test(lines[i]) &&
      !(lines[i].includes("|") && isSep(lines[i + 1]))
    ) { para.push(lines[i]); i++; }
    blocks.push(<p key={b++} className="whitespace-pre-wrap">{inline(para.join("\n"), `p${b}`)}</p>);
  }
  return <div className="space-y-2">{blocks}</div>;
}
