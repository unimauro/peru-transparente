"""Clasificación de entidades por NOMBRE (más fiable que el Tipo_Pod del PTE).

- categoria(nombre): etiqueta legible para el sitio y los gráficos.
- prioridad(nombre): orden de barrido. Menor = se scrapea primero.

Prioridad pedida: UNI → sistema educativo → salud/asistencial → fiscalías/justicia →
ministerios → reguladores → FF.AA./policía → empresas públicas → regional/local → resto.
"""
from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Universidad", re.compile(r"\bUNIVERSIDAD\b|\bUNI\b", re.I)),
    ("Educación", re.compile(r"COLEGIO|INSTITUTO\s+(SUPERIOR|DE\s+EDUCACI|PEDAG|TECNOL)|ESCUELA|EDUCATIV|"
                             r"PEDAG[OÓ]G|MAGISTERIO|\bUGEL\b|DIRECCI[ÓO]N\s+REGIONAL\s+DE\s+EDUCACI|"
                             r"\bDRE\b|EESPP|CETPRO|MINISTERIO DE EDUCACI", re.I)),
    ("Salud", re.compile(r"HOSPITAL|\bSALUD\b|ESSALUD|RED\s+DE\s+SALUD|DIRESA|GERESA|MINSA|SANIDAD|"
                         r"INSTITUTO NACIONAL DE SALUD|MATERNO|INSTITUTO.*NEOPL|SEGURO SOCIAL", re.I)),
    ("Justicia/Fiscalía", re.compile(r"FISCAL|MINISTERIO P[UÚ]BLICO|CORTE|PODER JUDICIAL|MAGISTRATURA|"
                                     r"JUSTICIA|PENITENCIARIO|\bINPE\b|JURADO|TRIBUNAL", re.I)),
    ("Ministerio", re.compile(r"\bMINISTERIO\b|PRESIDENCIA DEL CONSEJO", re.I)),
    ("Regulador/Superintendencia", re.compile(r"SUPERINTENDENCIA|OSINERGMIN|OSIPTEL|OSITR[AÁ]N|SUNASS|"
                                              r"SUTRAN|SUNEDU|SUNAT|\bSBS\b|\bSMV\b|INDECOPI|ORGANISMO.*SUPERVIS|REGULADOR", re.I)),
    ("Fuerzas Armadas/Policía", re.compile(r"EJ[EÉ]RCITO|MARINA DE GUERRA|FUERZA A[EÉ]REA|\bFAP\b|"
                                           r"COMANDO CONJUNTO|MINISTERIO DE DEFENSA|\bMILITAR\b|POLIC[IÍ]A|MININTER|"
                                           r"SUPERIOR DE GUERRA", re.I)),
    ("Empresa pública", re.compile(r"\bS\.?A\.?C?\.?\b|\bEMPRESA\b|PETRO|ELECTRO|SEDAPAL|\bEPS\b|"
                                   r"BANCO|CAJA MUNICIPAL|FONAFE|SIMA|FAME|ENACO|CORPAC|SERPOST", re.I)),
    ("Gobierno Regional", re.compile(r"GOBIERNO REGIONAL|\bREGI[OÓ]N\b", re.I)),
    ("Municipalidad", re.compile(r"MUNICIPALIDAD|MUNICIPAL", re.I)),
    ("Organismo constitucional", re.compile(r"BANCO CENTRAL|CONTRALOR|DEFENSOR[IÍ]A|RENIEC|\bONPE\b|"
                                            r"TRIBUNAL CONSTITUCIONAL|CONGRESO", re.I)),
]

# Orden de prioridad de barrido (por etiqueta de categoría).
_PRIORIDAD = {
    "Universidad": 1,
    "Educación": 2,
    "Salud": 3,
    "Justicia/Fiscalía": 4,
    "Ministerio": 5,
    "Organismo constitucional": 6,
    "Regulador/Superintendencia": 7,
    "Fuerzas Armadas/Policía": 8,
    "Empresa pública": 9,
    "Gobierno Regional": 10,
    "Municipalidad": 11,
    "Organismo público": 12,
}

_UNI = re.compile(r"UNIVERSIDAD NACIONAL DE INGENIER[IÍ]A|\(UNI\)", re.I)


def categoria(nombre: str) -> str:
    for label, rx in _PATTERNS:
        if rx.search(nombre or ""):
            return label
    return "Organismo público"


def prioridad(nombre: str) -> tuple[int, str]:
    # UNI primero de todo (pedido explícito).
    if _UNI.search(nombre or ""):
        return (0, nombre)
    return (_PRIORIDAD.get(categoria(nombre), 13), nombre)
