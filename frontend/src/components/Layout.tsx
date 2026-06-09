import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

function NavItem({ to, children }: { to: string; children: ReactNode }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        `rounded-lg px-3 py-1.5 text-sm transition-colors ${
          isActive ? "bg-white/10 text-white" : "text-ink-soft hover:text-white"
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
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-bg-base/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <img src={`${import.meta.env.BASE_URL}favicon.svg`} alt="" className="h-7 w-7" />
            <span className="font-semibold tracking-tight text-white">Perú Transparente</span>
          </Link>
          <nav className="flex items-center gap-1">
            <NavItem to="/">Inicio</NavItem>
            <NavItem to="/entidades">Entidades</NavItem>
            <NavItem to="/funcionarios">Funcionarios</NavItem>
            <a
              href="https://github.com/unimauro/peru-transparente"
              target="_blank"
              rel="noreferrer"
              className="ml-1 rounded-lg border border-white/10 px-3 py-1.5 text-sm text-ink-soft hover:border-white/20 hover:text-white"
            >
              GitHub
            </a>
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <Footer />
    </div>
  );
}

function Footer() {
  return (
    <footer className="mt-20 border-t border-white/[0.06]">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="glass flex flex-col items-center gap-4 p-6 text-center sm:flex-row sm:justify-between sm:text-left">
          <div>
            <div className="text-sm font-semibold text-white">¿Te resulta útil este proyecto?</div>
            <div className="mt-0.5 text-xs text-ink-mute">
              Es open source y gratuito. Tu apoyo ayuda a mantener el scraping y el hosting.
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-2">
            <a className="btn-ghost" href="https://buymeacoffee.com/unimauro" target="_blank" rel="noreferrer">☕ Buy me a coffee</a>
            <a className="btn-ghost" href="https://unimauro.github.io/salariosperu/yape.png" target="_blank" rel="noreferrer">📲 Yape</a>
            <a className="btn-ghost" href="https://wa.me/51940584307" target="_blank" rel="noreferrer">💬 WhatsApp</a>
          </div>
        </div>

        <div className="mt-6 flex flex-col items-center justify-between gap-2 text-xs text-ink-mute sm:flex-row">
          <span>
            Por{" "}
            <a href="https://github.com/unimauro" target="_blank" rel="noreferrer" className="font-medium text-ink-soft hover:text-white">
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
