"""Genera el contexto de datos para el bot de capital humano (frontend/public/data/bot_context.json).

Un resumen compacto y verídico de las cifras del Estado, para que el bot responda
SOLO con datos reales (grounding, anti-overclaiming).
"""
from __future__ import annotations

import json
from pathlib import Path

J = Path("frontend/public/data")


def load(name):
    p = J / name
    return json.loads(p.read_text()) if p.exists() else {}


def fmt(n):
    return f"{int(n):,}".replace(",", " ")


def main() -> None:
    k = load("national_kpis.json")
    m = load("meta.json")
    air = load("airhsp.json")
    sal = load("salarios.json")
    jer = load("jerarquia_estado.json").get("items", [])
    rot = load("rotacion.json")
    ords = load("ordenes_servicio.json")

    L = []
    L.append("DATOS DE CAPITAL HUMANO DEL ESTADO PERUANO (Perú Transparente). Cifras reales, usa SOLO estas.")
    L.append("")
    L.append("== TAMAÑO ==")
    L.append(f"- Total servidores públicos del Estado (AIRHSP/MEF, dic 2025, agregado sin nombres): {fmt(air.get('total',0))}.")
    L.append(f"- Masa salarial mensual: S/{fmt(air.get('masa_mensual',0))} (~S/{fmt(air.get('masa_mensual',0)*12)}/año).")
    L.append(f"- Personal NOMINAL con nombre y cargo (PTE, foto 2026): {fmt(k.get('total_funcionarios',0))}, de {k.get('entities_with_data',0)} entidades.")
    L.append("- Histórico nominal 2015-2024: 653 359 registros → 403 319 personas con trayectoria rastreable.")
    L.append("")
    L.append("== TIPOS DE EMPLEO (régimen, AIRHSP, todo el Estado) ==")
    for r in air.get("por_regimen", []):
        L.append(f"- {r['regimen']}: {fmt(r['n'])} personas, sueldo promedio S/{fmt(r['prom'])}.")
    L.append("  (Carreras Especiales = docentes y salud; el PTE NO publica docentes ni FF.AA., el AIRHSP sí los cuenta.)")
    L.append("")
    L.append("== ESTRUCTURA / CARGOS DE MANDO ==")
    L.append(f"- Cargos clave (de jefe hacia arriba): {fmt(k.get('total_cargos_clave',0))} (~4% del total nominal).")
    for niv, n in k.get("por_nivel", []):
        L.append(f"  · {niv}: {fmt(n)}")
    L.append("")
    L.append("== SUELDOS ==")
    if sal:
        L.append(f"- Mediana nacional S/{fmt(sal['mediana_nacional'])}, promedio S/{fmt(sal['promedio_nacional'])}, máximo S/{fmt(sal['top'][0]['sueldo'])} (incluye pagos extraordinarios).")
        L.append("- Distribución: la mayoría gana entre S/2 000 y S/5 000. CAS es el régimen más numeroso.")
        L.append("- Sueldo mediano por tipo de entidad (top): " + "; ".join(f"{c['categoria']} S/{fmt(c['mediana'])}" for c in sal.get("por_categoria", [])[:6]) + ".")
    L.append("")
    L.append("== SECTORES MÁS GRANDES (Sector → personal) ==")
    for s in jer[:8]:
        L.append(f"- {s['sector']}: {fmt(s['n'])} servidores, S/{fmt(s['masa'])}/mes.")
    L.append("  (Economía y Finanzas incluye pensiones del Estado; Educación es la mayor cartera de personal activo.)")
    L.append("")
    if rot:
        L.append("== ROTACIÓN / DESIGNACIONES (2024 → 2026) ==")
        L.append(f"- Tasa de rotación global: {rot.get('tasa_global')}% ({fmt(rot.get('altas',0))} altas, {fmt(rot.get('bajas',0))} bajas, {fmt(rot.get('permanecen',0))} permanecen).")
        L.append(f"- {len(rot.get('cambios_mando',[]))} entidades con cambios en cargos de mando.")
        L.append("")
    if ords:
        L.append("== LOCADORES / ÓRDENES DE SERVICIO (OCDS, ventana reciente) ==")
        L.append(f"- {fmt(ords.get('total_locadores',0))} locadores (personas naturales) con {fmt(ords.get('total_ordenes',0))} órdenes, S/{fmt(ords.get('monto_total',0))} total. El RUC contiene el DNI.")
        L.append("")
    L.append("== COBERTURA Y TRANSPARENCIA ==")
    L.append(f"- Catálogo de entidades del Estado: {fmt(k.get('total_entities',0))}. Barridas: {m.get('cobertura_pct')}%.")
    L.append(f"- Con personal publicado: {k.get('entities_with_data',0)}. SIN publicar su planilla: {fmt(k.get('entities_no_data',0))} (hallazgo: no transparentan a su personal).")
    L.append("- Empresas FONAFE (Petroperú, etc.), FF.AA., PNP e INPE NO publican personal en el PTE (régimen privado o seguridad).")
    L.append("- 27 de 35 universidades publican solo su planilla CAS administrativa, sin docentes ni rector.")
    L.append("")
    L.append("== FUENTES ==")
    L.append("PTE (transparencia.gob.pe, planilla nominal), gob.pe (autoridades), AIRHSP/MEF (agregado total), OCDS/OECE (contrataciones). Sitio: unimauro.github.io/peru-transparente")
    L.append("")
    L.append("== PRINCIPIO ==")
    L.append("Anti-overclaiming: estos datos describen y vinculan información pública; NO afirman irregularidades. 'Personal compartido' entre entidades es casi siempre rotación en el tiempo (mismo nombre en distintos años) u homónimos, NO doble empleo. La ley prohíbe doble percepción salvo docencia.")

    ctx = "\n".join(L)
    (J / "bot_context.json").write_text(json.dumps({"context": ctx}, ensure_ascii=False), encoding="utf-8")
    print(f"✔ bot_context.json · {len(ctx)} chars (~{len(ctx)//4} tokens)")


if __name__ == "__main__":
    main()
