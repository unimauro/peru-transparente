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
    act, pen, form, vac = air.get("activos") or {}, air.get("pensiones") or {}, air.get("formativa") or {}, air.get("vacantes") or {}
    per = air.get("periodo", "dic 2025")
    if act.get("registros"):
        L.append(f"- Total registros AIRHSP/MEF ({per}): {fmt(air.get('total_registros') or air.get('total',0))} = "
                 f"{fmt(act.get('registros',0))} ACTIVOS (plaza, CAS, convenio) + {fmt(pen.get('registros',0))} PENSIONISTAS y sobrevivientes "
                 f"+ {fmt(form.get('registros',0))} modalidad formativa/promotoras + {fmt(vac.get('plazas',0))} plazas vacantes. "
                 "NO decir que hay 2,7 millones de 'servidores': los activos son ~1,3 millones.")
        L.append(f"- Servidores públicos ACTIVOS (AIRHSP, {per}): {fmt(act.get('registros',0))}; masa mensual permanente S/{fmt(act.get('masa_mensual',0))} "
                 f"(sueldo promedio S/{fmt(act.get('prom',0))}); costo anual total S/{fmt(act.get('costo_anual',0))} (incluye aguinaldos, escolaridad y aportes).")
        L.append(f"- Pensiones a cargo del Tesoro (AIRHSP, {per}): {fmt(pen.get('registros',0))} pensionistas y sobrevivientes, S/{fmt(pen.get('masa_mensual',0))}/mes "
                 f"(pensión promedio S/{fmt(pen.get('prom',0))}), S/{fmt(pen.get('costo_anual',0))}/año.")
        L.append(f"- Cobertura AIRHSP: {air.get('cobertura','Gobierno Nacional y Regional')}. Las municipalidades no están.")
    else:
        L.append(f"- Total registros AIRHSP/MEF ({per}, agregado sin nombres): {fmt(air.get('total',0))} (incluye pensionistas; no es headcount de activos).")
        L.append(f"- Masa mensual de todos los registros: S/{fmt(air.get('masa_mensual',0))}.")
    L.append(f"- Personal NOMINAL con nombre y cargo (PTE, foto 2026): {fmt(k.get('total_funcionarios',0))}, de {k.get('entities_with_data',0)} entidades.")
    L.append("- Histórico nominal 2015-2024: 653 359 registros → 403 319 personas con trayectoria rastreable.")
    L.append("")
    L.append("== TIPOS DE EMPLEO (régimen laboral de los ACTIVOS, AIRHSP GN+GR) ==")
    regs = (act.get("por_regimen") if act else None) or []
    if regs:
        for r in regs:
            L.append(f"- {r['regimen']}: {fmt(r['n'])} activos, sueldo promedio S/{fmt(r['prom'])}.")
    else:
        for r in air.get("por_regimen", []):
            if r.get("regimen", "").lower().startswith("sin regimen"):
                L.append(f"- {r['regimen']}: {fmt(r['n'])} registros a S/{fmt(r['prom'])} promedio: NO son trabajadores; son sobre todo pensionistas ONP, sobrevivientes, tropa y practicantes.")
            else:
                L.append(f"- {r['regimen']}: {fmt(r['n'])} registros, promedio S/{fmt(r['prom'])}.")
    L.append("  (Carreras Especiales = docentes y salud; el PTE NO publica docentes ni FF.AA., el AIRHSP sí los cuenta.)")
    if act.get("por_nivel"):
        L.append("- Activos por nivel: " + "; ".join(f"{n['nivel']} {fmt(n['n'])} (S/{fmt(n['masa'])}/mes)" for n in act["por_nivel"]) + ".")
    if act.get("por_sector"):
        L.append("- Sectores con más masa salarial de activos: " + "; ".join(f"{x['sector']} {fmt(x['n'])} (S/{fmt(x['masa'])}/mes)" for x in act["por_sector"][:6]) + ".")
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
    L.append("  (OJO: esos conteos por sector incluyen pensionistas: Economía y Finanzas incluye ~777 mil pensionistas de la ONP, que NO son trabajadores del MEF. Educación es la mayor cartera de personal activo.)")
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
    L.append("PTE (transparencia.gob.pe, planilla nominal), gob.pe (autoridades), AIRHSP/MEF (datos abiertos: datosabiertos.gob.pe, dataset 'Personal activo y pensionista del sector público registrado en el AIRHSP'), OCDS/OECE (contrataciones). Sitio: unimauro.github.io/peru-transparente")
    L.append("")
    L.append("== PRINCIPIO ==")
    L.append("Anti-overclaiming: estos datos describen y vinculan información pública; NO afirman irregularidades. 'Personal compartido' entre entidades es casi siempre rotación en el tiempo (mismo nombre en distintos años) u homónimos, NO doble empleo. La ley prohíbe doble percepción salvo docencia.")

    ctx = "\n".join(L)
    (J / "bot_context.json").write_text(json.dumps({"context": ctx}, ensure_ascii=False), encoding="utf-8")
    print(f"✔ bot_context.json · {len(ctx)} chars (~{len(ctx)//4} tokens)")


if __name__ == "__main__":
    main()
