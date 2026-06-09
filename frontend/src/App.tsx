import { Routes, Route, Link } from "react-router-dom";
import { Home } from "@/pages/Home";
import { Entidades } from "@/pages/Entidades";
import { Funcionarios } from "@/pages/Funcionarios";

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-800">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-bold text-white">🇵🇪 Perú Transparente</Link>
          <nav className="flex gap-4 text-sm text-gray-300">
            <Link to="/" className="hover:text-white">Inicio</Link>
            <Link to="/entidades" className="hover:text-white">Entidades</Link>
            <Link to="/funcionarios" className="hover:text-white">Funcionarios</Link>
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/entidades" element={<Entidades />} />
          <Route path="/funcionarios" element={<Funcionarios />} />
        </Routes>
      </main>
      <footer className="mt-16 border-t border-gray-800 py-6 text-center text-xs text-gray-500">
        <div>
          Por <a href="https://github.com/unimauro" target="_blank" rel="noreferrer" className="font-medium text-gray-300 hover:text-white">Carlos Cárdenas Fernández · @unimauro</a>
        </div>
        <div className="mt-1">
          Código AGPL-3.0 · Datos CC BY 4.0 · Fuente: Portal de Transparencia Estándar · Solo información pública
        </div>
      </footer>
    </div>
  );
}
