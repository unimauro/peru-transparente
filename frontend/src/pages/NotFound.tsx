import { Link, useLocation } from "react-router-dom";
import { Empty } from "@/components/ui";

/** Ruta inexistente (#/lo-que-sea): antes quedaba cabecera y pie vacíos. */
export function NotFound() {
  const { pathname } = useLocation();
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <div className="chip mb-3">404</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Página no encontrada</h1>
      <p className="mt-2 break-all text-ink-soft">
        No existe ninguna sección en <code className="rounded bg-surface/10 px-1 text-[0.9em]">{pathname}</code>.
      </p>
      <Empty>
        <Link to="/" className="text-accent-blue underline">Volver al inicio</Link>
        {" · "}
        <Link to="/entidades" className="text-accent-blue underline">Entidades</Link>
        {" · "}
        <Link to="/funcionarios" className="text-accent-blue underline">Funcionarios</Link>
      </Empty>
    </div>
  );
}
