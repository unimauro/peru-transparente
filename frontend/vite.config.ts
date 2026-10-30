import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { createHash } from "node:crypto";

// CSP: la política vive en el <meta> de index.html. Este plugin (1) en build verifica
// que cada <script> inline tenga su hash sha256 listado en script-src (si no, falla el
// build en vez de romper el sitio en silencio) y (2) en `vite dev` relaja script-src y
// connect-src porque Vite/React Refresh inyectan un script inline y usan WebSocket.
function cspPlugin(): Plugin {
  const META_RE = /<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]*)"\s*\/?>/;
  return {
    name: "pt-csp",
    transformIndexHtml: {
      order: "post",
      handler(html, ctx) {
        const meta = html.match(META_RE);
        if (!meta) throw new Error("index.html: falta <meta http-equiv=\"Content-Security-Policy\">");
        if (ctx.server) {
          const dev = meta[1]
            .replace(/script-src [^;]*/, "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com")
            .replace(/connect-src /, "connect-src ws: wss: ");
          return html.replace(meta[0], `<meta http-equiv="Content-Security-Policy" content="${dev}" />`);
        }
        const sinComentarios = html.replace(/<!--[\s\S]*?-->/g, "");
        const inline = [...sinComentarios.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)];
        const missing = inline
          .map((m) => `'sha256-${createHash("sha256").update(m[1]).digest("base64")}'`)
          .filter((h) => !meta[1].includes(h));
        if (missing.length) throw new Error(`CSP: script inline sin hash en script-src: ${missing.join(" ")}`);
        return html;
      },
    },
  };
}

// GitHub Pages sirve bajo /<repo>/. Para project pages usar base = "/peru-transparente/".
// Si se usa dominio propio o user-page, exportar PT_BASE="/" en el build.
const base = process.env.PT_BASE ?? "/peru-transparente/";

export default defineConfig({
  base,
  plugins: [react(), cspPlugin()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  build: { outDir: "dist", sourcemap: false },
});
