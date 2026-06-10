"""Genera una imagen OG por sección + un stub HTML por ruta (para previews al compartir).

Como el sitio es SPA con hash routing, los crawlers solo ven el OG de index.html.
Solución: por cada sección creamos /<seccion>/index.html con su propio OG y un
redirect a /#/<seccion>. Compartir el link de PATH muestra el preview de esa sección.
"""
from __future__ import annotations

import html
import json
import subprocess
from pathlib import Path

PUB = Path("frontend/public")
BASE = "/peru-transparente"
SITE = "https://unimauro.github.io/peru-transparente"

# Lee cifras reales del KPI para ponerlas en cada OG
kpi = json.loads((PUB / "data/national_kpis.json").read_text())
sal = json.loads((PUB / "data/salarios.json").read_text()) if (PUB / "data/salarios.json").exists() else {}
fmt = lambda n: f"{int(n):,}".replace(",", " ")

SECCIONES = {
    "funcionarios": ("Servidores públicos", "Todo el personal del Estado con cargo, dependencia y sueldo",
                     f"{fmt(kpi['total_funcionarios'])} servidores", "#1aa3c0"),
    "personas": ("Buscador de personas", "Encuentra a cualquiera y mira en cuántas entidades aparece — grafo de poder",
                 "210 203 personas · 2 470 en redes", "#a78bfa"),
    "entidades": ("Entidades del Estado", "Ministerios, reguladores, universidades, FF.AA., empresas, municipios",
                  f"{fmt(kpi['total_entities'])} entidades", "#4f8cff"),
    "sueldos": ("Sueldos del Estado", "Distribución, comparación por entidad y los sueldos más altos",
                f"mediana S/ {fmt(sal.get('mediana_nacional', 3336))}", "#e11d2a"),
    "regiones": ("Personal por región", "Cómo se distribuye el personal y la planilla en el mapa del Perú",
                 "mapa nacional", "#22c55e"),
    "autoridades": ("Autoridades del Estado", "Rectores, ministros, superintendentes y jefes con contacto",
                    "5 637 autoridades", "#f59e0b"),
}

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" font-family="Inter, Arial, sans-serif">
 <defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b0f17"/><stop offset="0.6" stop-color="#0d1320"/><stop offset="1" stop-color="#11030a"/></linearGradient>
  <radialGradient id="glow" cx="0.82" cy="0.2" r="0.6"><stop offset="0" stop-color="{accent}" stop-opacity="0.28"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>
 </defs>
 <rect width="1200" height="630" fill="url(#bg)"/><rect width="1200" height="630" fill="url(#glow)"/>
 <rect x="0" y="0" width="1200" height="6" fill="#e11d2a"/>
 <g stroke="#22304a" stroke-width="1.2" opacity="0.7">
  <line x1="880" y1="150" x2="1010" y2="110"/><line x1="880" y1="150" x2="1040" y2="250"/><line x1="1040" y1="250" x2="1110" y2="180"/><line x1="1040" y1="250" x2="1070" y2="370"/><line x1="880" y1="150" x2="960" y2="300"/></g>
 <g><circle cx="880" cy="150" r="13" fill="{accent}"/><circle cx="1010" cy="110" r="7" fill="#4f8cff"/><circle cx="1040" cy="250" r="9" fill="#a78bfa"/><circle cx="1110" cy="180" r="6" fill="#22d3ee"/><circle cx="1070" cy="370" r="7" fill="#22d3ee"/><circle cx="960" cy="300" r="6" fill="#16a34a"/></g>
 <g transform="translate(80,120)"><rect width="10" height="30" rx="1" fill="#e11d2a"/><rect x="10" width="10" height="30" fill="#f3f4f6"/><rect x="20" width="10" height="30" rx="1" fill="#e11d2a"/></g>
 <text x="124" y="142" fill="#9fb0c9" font-size="22" font-weight="600" letter-spacing="3">PERÚ TRANSPARENTE</text>
 <text x="78" y="262" fill="#ffffff" font-size="82" font-weight="800" letter-spacing="-2">{titulo}</text>
 <text x="80" y="320" fill="#c7d2e0" font-size="29" font-weight="500">{sub1}</text>
 <text x="80" y="358" fill="#c7d2e0" font-size="29" font-weight="500">{sub2}</text>
 <g transform="translate(80,430)"><rect width="{statw}" height="64" rx="14" fill="#111827" stroke="{accent}" stroke-opacity="0.5"/><text x="26" y="42" fill="{accent}" font-size="30" font-weight="700">{stat}</text></g>
 <text x="80" y="590" fill="#6b7a90" font-size="20">Datos públicos · trazables a la fuente · @unimauro</text>
 <text x="1120" y="590" fill="#6b7a90" font-size="20" text-anchor="end">{site}</text>
</svg>"""


def wrap(sub: str) -> tuple[str, str]:
    words = sub.split()
    line1, line2 = "", ""
    for w in words:
        if len(line1) < 52:
            line1 += w + " "
        else:
            line2 += w + " "
    return line1.strip(), line2.strip()


def main() -> None:
    (PUB / "og").mkdir(exist_ok=True)
    for slug, (titulo, sub, stat, accent) in SECCIONES.items():
        s1, s2 = wrap(sub)
        svg = SVG.format(titulo=html.escape(titulo), sub1=html.escape(s1), sub2=html.escape(s2),
                         stat=html.escape(stat), accent=accent, statw=22 + len(stat) * 17,
                         site=f"{SITE.replace('https://', '')}/{slug}")
        svgp = PUB / "og" / f"{slug}.svg"
        svgp.write_text(svg, encoding="utf-8")
        subprocess.run(["rsvg-convert", "-w", "1200", "-h", "630", str(svgp), "-o", str(PUB / "og" / f"{slug}.png")], check=True)
        svgp.unlink()
        # stub HTML
        stub = PUB / slug
        stub.mkdir(exist_ok=True)
        (stub / "index.html").write_text(f"""<!doctype html><html lang="es"><head><meta charset="utf-8"/>
<title>{titulo} — Perú Transparente</title>
<meta name="description" content="{html.escape(sub)}"/>
<meta property="og:type" content="website"/>
<meta property="og:title" content="{titulo} — Perú Transparente"/>
<meta property="og:description" content="{html.escape(sub)}"/>
<meta property="og:image" content="{SITE}/og/{slug}.png"/>
<meta property="og:url" content="{SITE}/{slug}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:image" content="{SITE}/og/{slug}.png"/>
<script>location.replace("{BASE}/#/{slug}");</script>
<meta http-equiv="refresh" content="0;url={BASE}/#/{slug}"/>
</head><body>Redirigiendo a <a href="{BASE}/#/{slug}">{titulo}</a>…</body></html>""", encoding="utf-8")
        print(f"  ✔ {slug}: og/{slug}.png + {slug}/index.html")
    print("Listo. Comparte los links de PATH (ej. .../peru-transparente/personas) para el preview por sección.")


if __name__ == "__main__":
    main()
