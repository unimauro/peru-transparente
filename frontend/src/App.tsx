import { Routes, Route, Link } from "react-router-dom";
import { Home } from "@/pages/Home";

function Placeholder({ title }: { title: string }) {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <h2 className="text-2xl font-semibold text-white">{title}</h2>
      <p className="mt-2 text-gray-400">Vista en construcción — ver docs/UI_UX.md para el mockup.</p>
    </div>
  );
}

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-800">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-bold text-white">🇵🇪 Perú Transparente</Link>
          <nav className="flex gap-4 text-sm text-gray-300">
            <Link to="/entidades">Entidades</Link>
            <Link to="/grafo">Grafo</Link>
            <Link to="/dashboards">Dashboards</Link>
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/entidades" element={<Placeholder title="Directorio de Entidades" />} />
          <Route path="/grafo" element={<Placeholder title="Grafo Nacional de Poder" />} />
          <Route path="/dashboards" element={<Placeholder title="Dashboards" />} />
          <Route path="/metodologia" element={<Placeholder title="Metodología y fuentes" />} />
        </Routes>
      </main>
      <footer className="mt-16 border-t border-gray-800 py-6 text-center text-xs text-gray-500">
        Código AGPL-3.0 · Datos CC BY 4.0 · Solo información pública · Sin imputación de irregularidades
      </footer>
    </div>
  );
}
