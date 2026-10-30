// <title> por ruta. El sitio es una SPA con HashRouter: sin esto, historial,
// pestañas y marcadores muestran el mismo texto en todas las rutas.
const SITIO = "Perú Transparente";

const TITULOS: [RegExp, string][] = [
  [/^\/$/, "Mapa Nacional de Funcionarios y Redes de Poder"],
  [/^\/entidades$/, "Entidades"],
  [/^\/entidad\//, "Entidad"],
  [/^\/funcionarios$/, "Funcionarios"],
  [/^\/nuevos$/, "Nuevos funcionarios"],
  [/^\/ordenes$/, "Locadores de servicio"],
  [/^\/contratos$/, "Contratos del Estado"],
  [/^\/sanciones$/, "Sanciones"],
  [/^\/salarios$/, "Salarios"],
  [/^\/personas$/, "Personas y redes"],
  [/^\/trayectorias$/, "Trayectorias de poder"],
  [/^\/historico$/, "Histórico"],
  [/^\/costo$/, "Costo del Estado"],
  [/^\/autoridades$/, "Autoridades"],
  [/^\/regiones$/, "Regiones"],
  [/^\/metodologia$/, "FAQ y metodología"],
];

export function tituloDeRuta(pathname: string): string {
  const hit = TITULOS.find(([re]) => re.test(pathname));
  return hit ? hit[1] : "Página no encontrada";
}

/** Fija document.title como "<sección> · Perú Transparente". */
export function setTitulo(seccion: string | null | undefined): void {
  const s = (seccion ?? "").trim();
  document.title = s ? `${s} · ${SITIO}` : SITIO;
}
