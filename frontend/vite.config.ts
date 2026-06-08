import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// GitHub Pages sirve bajo /<repo>/. Para project pages usar base = "/peru-transparente/".
// Si se usa dominio propio o user-page, exportar PT_BASE="/" en el build.
const base = process.env.PT_BASE ?? "/peru-transparente/";

export default defineConfig({
  base,
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  build: { outDir: "dist", sourcemap: false },
});
