import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { ThemeToggle } from "@/components/ThemeToggle";
import { YapeModal } from "@/components/YapeModal";
import { ChatBot } from "@/components/ChatBot";
import { tituloDeRuta, setTitulo } from "@/lib/pageTitle";

// Navegación. En escritorio se muestran las PRIMARIAS más un desplegable "Más"
// con el resto (14 entradas en línea no caben en max-w-6xl: 1 360 px medidos).
// En móvil/tablet (< lg) todas van al panel hamburguesa. Entre lg y xl el botón
// GitHub se esconde del nav y aparece dentro de "Más" (a 1 024 px no cabía).
const NAV_PRIMARIA: [string, string][] = [
  ["/", "Inicio"],
  ["/entidades", "Entidades"],
  ["/funcionarios", "Funcionarios"],
  ["/personas", "Personas"],
  ["/historico", "Histórico"],
  ["/costo", "Costo"],
  ["/contratos", "Contratos"],
  ["/sanciones", "Sanciones"],
];
const NAV_MAS: [string, string][] = [
  ["/nuevos", "Nuevos funcionarios"],
  ["/trayectorias", "Trayectorias"],
  ["/ordenes", "Locadores"],
  ["/autoridades", "Autoridades"],
  ["/regiones", "Regiones"],
  ["/metodologia", "FAQ / Metodología"],
];
export const NAV: [string, string][] = [...NAV_PRIMARIA, ...NAV_MAS];

function NavItem({ to, children, onClick, block }: { to: string; children: ReactNode; onClick?: () => void; block?: boolean }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      onClick={onClick}
      className={({ isActive }) =>
        `rounded-lg px-3 py-1.5 text-sm transition-colors ${block ? "block" : ""} ${
          isActive ? "bg-surface/10 text-ink" : "text-ink-soft hover:text-ink"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

/** Desplegable "Más" del escritorio: cierra con clic fuera, Escape o al navegar. */
function MenuMas() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { pathname } = useLocation();
  const activo = NAV_MAS.some(([to]) => pathname === to || pathname.startsWith(`${to}/`));

  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${activo ? "bg-surface/10 text-ink" : "text-ink-soft hover:text-ink"}`}
      >
        Más <span aria-hidden="true" className="text-[10px]">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div role="menu" className="glass absolute right-0 top-full z-50 mt-1 flex w-52 flex-col gap-0.5 bg-bg-base p-1.5 shadow-xl">
          {NAV_MAS.map(([to, label]) => (
            <NavItem key={to} to={to} block onClick={() => setOpen(false)}>{label}</NavItem>
          ))}
          <a
            href="https://github.com/unimauro/peru-transparente"
            target="_blank"
            rel="noreferrer"
            role="menuitem"
            onClick={() => setOpen(false)}
            className="block rounded-lg border-t border-surface/[0.06] px-3 py-1.5 text-sm text-ink-soft hover:text-ink xl:hidden"
          >
            GitHub ↗
          </a>
        </div>
      )}
    </div>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const [menu, setMenu] = useState(false);
  const { pathname } = useLocation();

  // <title> por ruta (historial y pestañas legibles). Las páginas con detalle
  // (p. ej. entidad) lo afinan después con setTitulo().
  useEffect(() => { setTitulo(tituloDeRuta(pathname)); }, [pathname]);
  // Cierra el panel móvil al navegar.
  useEffect(() => { setMenu(false); }, [pathname]);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-surface/[0.06] bg-bg-base/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <Link to="/" className="flex shrink-0 items-center gap-2" onClick={() => setMenu(false)}>
            <img src={`${import.meta.env.BASE_URL}favicon.svg`} alt="" className="h-7 w-7" />
            <span className="whitespace-nowrap font-semibold tracking-tight text-ink">Perú Transparente</span>
          </Link>

          {/* Navegación de escritorio (≥ lg): primarias + "Más" */}
          <nav className="hidden min-w-0 items-center gap-0.5 lg:flex" aria-label="Principal">
            {NAV_PRIMARIA.map(([to, label]) => <NavItem key={to} to={to}>{label}</NavItem>)}
            <MenuMas />
            <a
              href="https://github.com/unimauro/peru-transparente"
              target="_blank"
              rel="noreferrer"
              className="ml-1 hidden rounded-lg border border-surface/10 px-3 py-1.5 text-sm text-ink-soft hover:border-surface/20 hover:text-ink xl:inline-block"
            >
              GitHub
            </a>
            <ThemeToggle />
          </nav>

          {/* Controles móviles/tablet: tema + hamburguesa */}
          <div className="flex items-center gap-1 lg:hidden">
            <ThemeToggle />
            <button
              onClick={() => setMenu((o) => !o)}
              aria-label={menu ? "Cerrar menú" : "Abrir menú"}
              aria-expanded={menu}
              className="rounded-lg border border-surface/10 px-3 py-2 text-lg leading-none text-ink-soft hover:text-ink"
            >
              {menu ? "✕" : "☰"}
            </button>
          </div>
        </div>

        {/* Panel de navegación móvil/tablet */}
        {menu && (
          <nav className="flex flex-col gap-1 border-t border-surface/[0.06] px-3 py-3 lg:hidden" aria-label="Principal (móvil)">
            {NAV.map(([to, label]) => (
              <NavItem key={to} to={to} onClick={() => setMenu(false)}>{label}</NavItem>
            ))}
            <a
              href="https://github.com/unimauro/peru-transparente"
              target="_blank"
              rel="noreferrer"
              onClick={() => setMenu(false)}
              className="rounded-lg px-3 py-1.5 text-sm text-ink-soft hover:text-ink"
            >
              GitHub ↗
            </a>
          </nav>
        )}
      </header>

      <main className="flex-1">{children}</main>

      <Footer />
      <ChatBot />
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
