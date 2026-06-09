"""Connector PTE — Personal (funcionarios y servidores públicos) por entidad.

Fuente: Portal de Transparencia Estándar (transparencia.gob.pe).
Cada entidad tiene un `id_entidad` entero. El rubro "Personal" se sirve por POST
WebForms (año/mes/régimen). Devuelve la tabla:
    RÉGIMEN | APELLIDOS Y NOMBRES | CARGO | DEPENDENCIA | <5 ingresos> | TOTAL

Esta es LA fuente de cargos del Estado peruano: de altos funcionarios (ministros,
viceministros) hasta jefaturas y servidores, con su remuneración y dependencia.

Diseñado para descarga progresiva: barato, sin navegador, idempotente.
"""
from __future__ import annotations

import html
import re
from collections.abc import Iterator
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

BASE = "https://www.transparencia.gob.pe/personal/pte_transparencia_personal.aspx"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# Códigos de régimen del PTE. 8=Pensionistas se excluye por defecto (no son cargos vigentes).
REGIMES = {
    1: "CAS",
    2: "Régimen 276",
    3: "Régimen 728/OTROS",
    4: "PAC",
    5: "FAG",
    6: "PNUD",
    7: "Altos Funcionarios",
    9: "Ley Servir",
}

_ENTITY_RE = re.compile(
    r"(MINISTERIO|PRESIDENCIA|GOBIERNO REGIONAL|GOBIERNO LOCAL|MUNICIPALIDAD|UNIVERSIDAD|"
    r"ORGANISMO|INSTITUTO|SUPERINTENDENCIA|CONSEJO|PODER|JURADO|REGISTRO|SEGURO|BANCO|"
    r"EMPRESA|SERVICIO|AUTORIDAD|COMISI[ÓO]N|PROGRAMA|FONDO|CENTRAL|CONTRALOR[ÍI]A|"
    r"DEFENSOR[ÍI]A|TRIBUNAL|FISCAL[ÍI]A|ACADEMIA|BIBLIOTECA|ARCHIVO|CAJA|SOCIEDAD|"
    r"AGENCIA|DIRECCI[ÓO]N|PROYECTO|UNIDAD|HOSPITAL|RED DE SALUD)[^<|>]{2,90}",
    re.I,
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FuncionarioRow:
    id_entidad: int
    entidad: str
    anio: int
    mes: int
    regimen: str
    apellidos_nombres: str
    cargo: str
    dependencia: str
    total_ingreso_mensual: str
    fuente_url: str
    captured_at: str


_HEADER_TOKENS = (
    "APELLIDOS Y", "RÉGIMEN", "REGIMEN", "DETALLE DE INGRESOS", "TOTAL INGRESOS",
    "REMUNERACIONES (", "HONORARIOS (", "INCENTIVO (", "AGUINALDO", "OTROS INGRESOS",
    "DEPENDENCIA Y/O", "NO SE ENCONTR", "NO EXISTE INFORMACI",
)


def _strip(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


class PtePersonalConnector:
    source = "PTE_PERSONAL"
    method = "scrape"
    confidence = 0.90

    def __init__(self, timeout: float = 50.0):
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def _url(self, id_entidad: int) -> str:
        return f"{BASE}?id_entidad={id_entidad}&id_tema=32&ver="

    def _query_url(self, id_entidad: int, anio: int, mes: int, regimen: int, pag: int) -> str:
        return (f"{BASE}?id_entidad={id_entidad}&in_anno_consulta={anio}"
                f"&ch_mes_consulta={mes:02d}&vc_nombre_funcionario=&vc_dni_funcionario="
                f"&ch_tipo_regimen={regimen}&id_tema=32&Ver=&pag={pag}")

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=30))
    def _get(self, id_entidad: int) -> str:
        r = self._client.get(self._url(id_entidad))
        r.raise_for_status()
        return r.text

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=30))
    def _get_query(self, id_entidad: int, anio: int, mes: int, regimen: int, pag: int) -> str:
        r = self._client.get(self._query_url(id_entidad, anio, mes, regimen, pag))
        r.raise_for_status()
        return r.text

    @staticmethod
    def entity_name(page: str) -> str | None:
        # El nombre real vive en <h2 class='esp-title-00'>Nombre (SIGLA)
        m = re.search(r"<h2[^>]*esp-title-00[^>]*>([^<]+)", page, re.I)
        if m and _strip(m.group(1)):
            return _strip(m.group(1))
        return None  # sin h2 esp-title-00 → id de entidad inválido/sin publicar

    @staticmethod
    def _parse_rows(html_text: str) -> list[list[str]]:
        t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_text, flags=re.S | re.I)
        out = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, flags=re.S | re.I):
            cells = [_strip(td) for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
            cells = [c for c in cells if c != ""]
            out.append(cells)
        return out

    def fetch_entity(
        self, id_entidad: int, anio: int, mes: int,
        regimes: list[int] | None = None, max_pages: int = 200, entity_name: str | None = None,
    ) -> Iterator[FuncionarioRow]:
        """Genera filas de funcionarios de una entidad/período, TODOS los regímenes y páginas."""
        name = entity_name or self.entity_name(self._get(id_entidad)) or f"Entidad {id_entidad}"
        for reg in (regimes or list(REGIMES)):
            for pag in range(1, max_pages + 1):
                try:
                    resp = self._get_query(id_entidad, anio, mes, reg, pag)
                except Exception:
                    break
                page_rows = 0
                for cells in self._parse_rows(resp):
                    if len(cells) < 5:
                        continue
                    nombre, cargo, dep = cells[1], cells[2], cells[3]
                    if any(h in " ".join(cells).upper() for h in _HEADER_TOKENS):
                        continue
                    if not re.search(r"[A-Za-zÁÉÍÓÚÑ]", nombre):
                        continue
                    if "," not in nombre and len(nombre.split()) < 2:
                        continue
                    page_rows += 1
                    yield FuncionarioRow(
                        id_entidad=id_entidad, entidad=name, anio=anio, mes=mes,
                        regimen=REGIMES.get(reg, str(reg)),
                        apellidos_nombres=nombre, cargo=cargo, dependencia=dep,
                        total_ingreso_mensual=cells[-1],
                        fuente_url=self._query_url(id_entidad, anio, mes, reg, pag),
                        captured_at=utcnow(),
                    )
                # avanzar solo si hay "Siguiente" y la página trajo filas
                if "Siguiente" not in resp or page_rows == 0:
                    break


CSV_FIELDS = list(asdict(FuncionarioRow(0, "", 0, 0, "", "", "", "", "", "", "")).keys())


if __name__ == "__main__":
    c = PtePersonalConnector()
    n = 0
    for row in c.fetch_entity(145, 2024, 12, regimes=[5, 7]):
        print(row.regimen, "|", row.apellidos_nombres, "|", row.cargo, "|", row.dependencia)
        n += 1
        if n >= 10:
            break
    print("filas:", n)
    c.close()
