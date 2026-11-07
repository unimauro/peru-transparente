"""Cruce contratista ↔ planilla del Estado (señal de doble percepción / conflicto de interés).

Índice de la planilla nominal (data/funcionarios.csv + data/funcionarios_historico.csv) con dos
claves, en este orden de confianza:

  1. DNI  — cuando la planilla lo trae (algunas entidades lo ponen en "dependencia" o "cargo",
            p. ej. Red de Salud San Román) y el contratista es persona natural (RUC 10 + DNI + dv).
            match = "dni", confianza ALTA.
  2. Nombre — multiconjunto de tokens sin tildes: la planilla publica "APELLIDOS, NOMBRES" y el
            OCDS "APELLIDO APELLIDO NOMBRE"; se comparan los tokens ordenados (≥ 3 tokens para
            evitar coincidencias triviales). match = "nombre", confianza POSSIBLE_ALTA (homónimo
            posible).

Anti-overclaiming: una coincidencia describe que la persona FIGURA en la planilla de una entidad y
además recibe órdenes/adjudicaciones; no afirma irregularidad (puede ser otra entidad, otro periodo
o un homónimo). El front lo rotula "coincidencia por DNI / por nombre".
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

FUENTES = [Path("data/funcionarios.csv"), Path("data/funcionarios_historico.csv")]
RE_DNI = re.compile(r"^\d{8}$")
MIN_TOKENS = 3


def na(s: str | None) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "")
                  .encode("ascii", "ignore").decode().upper()).strip()


def tokens(nombre: str | None) -> tuple[str, ...]:
    """Multiconjunto (tupla ordenada) de tokens del nombre, sin tildes ni puntuación."""
    return tuple(sorted(t for t in re.split(r"[^A-Z0-9]+", na(nombre)) if t))


def es_dni(valor: str | None) -> bool:
    return bool(RE_DNI.fullmatch((valor or "").strip()))


def dni_de_ruc(ruc: str | None) -> str:
    """DNI embebido en el RUC de persona natural (10 + DNI + dígito verificador); '' si no aplica."""
    r = (ruc or "").strip()
    return r[2:10] if len(r) == 11 and r.startswith("10") else ""


def dni_en_fila(r: dict) -> str:
    """DNI que la entidad puso en un campo libre de la planilla (dependencia o cargo)."""
    for campo in ("dependencia", "cargo"):
        v = (r.get(campo) or "").strip()
        if es_dni(v):
            return v
    return ""


def _rows(path: Path):
    fh = path.open(encoding="utf-8", errors="ignore", newline="")
    return csv.DictReader(line.replace("\x00", "") for line in fh)


class IndicePlanilla:
    """Índice en memoria de la planilla por DNI y por tokens del nombre."""

    def __init__(self, fuentes: list[Path] | None = None) -> None:
        self.por_dni: dict[str, tuple[str, str]] = {}        # dni -> (nombre, entidad)
        self.por_tokens: dict[tuple[str, ...], str] = {}      # tokens -> entidad
        self.n_filas = 0
        for p in (fuentes or FUENTES):
            if not p.exists():
                continue
            for r in _rows(p):
                nombre = r.get("apellidos_nombres") or ""
                if not nombre:
                    continue
                self.n_filas += 1
                ent = r.get("entidad", "")
                d = dni_en_fila(r)
                if d and d not in self.por_dni:
                    self.por_dni[d] = (nombre, ent)
                tk = tokens(nombre)
                if len(tk) >= MIN_TOKENS and tk not in self.por_tokens:
                    self.por_tokens[tk] = ent

    def buscar(self, nombre: str | None, dni: str | None = None) -> dict:
        """{'match': 'dni'|'nombre'|'', 'entidad': str, 'confianza': 'ALTA'|'POSSIBLE_ALTA'|''}."""
        d = (dni or "").strip()
        if d and d in self.por_dni:
            return {"match": "dni", "entidad": self.por_dni[d][1], "confianza": "ALTA"}
        tk = tokens(nombre)
        if len(tk) >= MIN_TOKENS and tk in self.por_tokens:
            return {"match": "nombre", "entidad": self.por_tokens[tk], "confianza": "POSSIBLE_ALTA"}
        return {"match": "", "entidad": "", "confianza": ""}


if __name__ == "__main__":
    assert tokens("OCAÑA TAFUR, NORA MARÍA") == tokens("OCANA TAFUR NORA MARIA")
    assert dni_de_ruc("10066033207") == "06603320" and dni_de_ruc("20131370998") == ""
    assert dni_en_fila({"dependencia": "46081234", "cargo": "X"}) == "46081234"
    idx = IndicePlanilla()
    print(f"planilla: {idx.n_filas:,} filas · {len(idx.por_dni):,} con DNI · {len(idx.por_tokens):,} nombres (≥3 tokens)")
