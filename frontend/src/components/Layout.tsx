import { useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { ThemeToggle } from "@/components/ThemeToggle";
import { YapeModal } from "@/components/YapeModal";

function NavItem({ to, children }: { to: string; children: ReactNode }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        `rounded-lg px-3 py-1.5 text-sm transition-colors ${
          isActive ? "bg-surface/10 text-ink" : "text-ink-soft hover:text-ink"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-surface/[0.06] bg-bg-base/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <img src={`${import.meta.env.BASE_URL}favicon.svg`} alt="" className="h-7 w-7" />
            <span className="font-semibold tracking-tight text-ink">Perú Transparente</span>
          </Link>
          <nav className="flex items-center gap-1">
            <NavItem to="/">Inicio</NavItem>
            <NavItem to="/entidades">Entidades</NavItem>
            <NavItem to="/funcionarios">Funcionarios</NavItem>
            <NavItem to="/autoridades">Autoridades</NavItem>
            <NavItem to="/regiones">Regiones</NavItem>
            <NavItem to="/metodologia">FAQ</NavItem>
            <a
              href="https://github.com/unimauro/peru-transparente"
              target="_blank"
              rel="noreferrer"
              className="ml-1 hidden rounded-lg border border-surface/10 px-3 py-1.5 text-sm text-ink-soft hover:border-surface/20 hover:text-ink sm:block"
            >
              GitHub
            </a>
            <ThemeToggle />
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <Footer />
    </div>
  );
}

function Footer() {
  const [yape, setYape] = useState(false);
  return (
    <footer className="mt-20 border-t border-surface/[0.06]">
      <YapeModal open={yape} onClose={() => setYape(false)} />
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="glass grid gap-6 p-6 sm:grid-cols-[auto,1fr] sm:items-center">
          <div className="flex justify-center">
            <button onClick={() => setYape(true)} className="block rounded-xl bg-white p-2 shadow-glow transition-transform hover:-translate-y-0.5" aria-label="Mostrar QR de Yape">
              <img src="https://unimauro.github.io/salariosperu/yape.png" alt="Yape QR" className="h-28 w-28 rounded-lg object-cover" loading="lazy" />
            </button>
          </div>
          <div className="text-center sm:text-left">
            <div className="text-base font-semibold text-ink">¿Te resulta útil este proyecto? Apóyalo 🙌</div>
            <p className="mt-1 text-sm text-ink-mute">
              Es open source y gratuito. Tu aporte mantiene el scraping diario y el hosting. Yapea al QR
              o usa cualquiera de estas opciones.
            </p>
            <div className="mt-3 flex flex-wrap justify-center gap-2 sm:justify-start">
              <button className="btn-primary" onClick={() => setYape(true)}>📲 Yape · 940 584 307</button>
              <a className="btn-ghost" href="https://buymeacoffee.com/unimauro" target="_blank" rel="noreferrer">☕ Buy me a coffee</a>
              <a className="btn-ghost" href="https://wa.me/51940584307" target="_blank" rel="noreferrer">💬 WhatsApp</a>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-col items-center justify-between gap-2 text-xs text-ink-mute sm:flex-row">
          <span>
            Por{" "}
            <a href="https://github.com/unimauro" target="_blank" rel="noreferrer" className="font-medium text-ink-soft hover:text-ink">
              Carlos Cárdenas Fernández · @unimauro
            </a>
          </span>
          <span>Código AGPL-3.0 · Datos CC BY 4.0 · Fuente: Portal de Transparencia Estándar</span>
        </div>
        <p className="mt-2 text-center text-[11px] text-ink-faint sm:text-right">
          Solo información pública · trazable a la fuente · sin imputar irregularidades
        </p>
      </div>
    </footer>
  );
}
