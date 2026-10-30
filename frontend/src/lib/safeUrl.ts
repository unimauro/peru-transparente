// Validación de URLs que llegan de fuera del código (JSON de datos, respuestas
// del chatbot). Solo deja pasar http(s):, mailto: y tel: (y rutas internas
// "#/..." si se pide). Todo lo demás (javascript:, data:, vbscript:, rutas
// relativas, basura) devuelve null y el llamador debe mostrar texto sin enlace.

export interface SafeUrlOpts {
  /** Acepta rutas internas del SPA ("#/entidades"); se devuelven tal cual, sin BASE. */
  allowHash?: boolean;
  /** Solo https: (p. ej. para recursos que se cargan, no solo se enlazan). */
  httpsOnly?: boolean;
}

const INTERNAL_RE = /^#\/[\w\-/]*$/;

export function safeUrl(u: unknown, opts: SafeUrlOpts = {}): string | null {
  if (typeof u !== "string") return null;
  const s = u.trim();
  if (!s || s.length > 2048) return null;
  if (opts.allowHash && INTERNAL_RE.test(s)) return s;

  let parsed: URL;
  try {
    parsed = new URL(s); // solo absolutas; relativas lanzan y se descartan
  } catch {
    return null;
  }
  const p = parsed.protocol.toLowerCase();
  const ok = opts.httpsOnly ? p === "https:" : p === "https:" || p === "http:" || p === "mailto:" || p === "tel:";
  if (!ok) return null;
  // Para http(s) exigimos host; evita "https:evil" u otras formas raras.
  if ((p === "https:" || p === "http:") && !parsed.hostname) return null;
  return parsed.href;
}
