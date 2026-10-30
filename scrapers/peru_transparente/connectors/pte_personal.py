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
    remuneracion: str            # REMUNERACIONES (base: SERVIR/728/276/CAS)
    honorarios: str              # HONORARIOS (FAG/PAC/PNUD)
    incentivo: str               # INCENTIVO (CAFAE)
    aguinaldo: str               # AGUINALDO/GRATIFICACIÓN/ESCOLARIDAD
    otros: str                   # OTROS INGRESOS (DU) — extraordinarios
    total_ingreso_mensual: str
    fuente_url: str
    captured_at: str


# Tokens que solo aparecen en filas de cabecera/aviso. OJO: NO incluir "RÉGIMEN", "AGUINALDO" ni
# "OTROS INGRESOS": la primera celda de cada fila de datos es "Régimen 276" / "Régimen 728/OTROS",
# y filtrarlos descartaba TODOS los nombrados y docentes (bug detectado en auditoría 2026-10-30).
_HEADER_TOKENS = (
    "APELLIDOS Y", "DETALLE DE INGRESOS", "TOTAL INGRESOS", "DEPENDENCIA Y/O",
    "NO SE ENCONTR", "NO EXISTE INFORMACI",
)
_N_COLS = 10  # RÉGIMEN | NOMBRES | CARGO | DEPENDENCIA | REMUN | HONOR | INCENT | AGUIN | OTROS | TOTAL


def _strip(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


_MONEY_RE = re.compile(r"-?\d{1,9}(\.\d{1,2})?")
_SUNAT_NOTE_RE = re.compile(r",?\s*Para ver la informaci.*$", re.I | re.S)
_ULTIMO_RE = re.compile(r"pag=(\d+)'>\s*(?:Ultimo|Último|&Uacute;ltimo)", re.I)


def _money(s: str) -> str:
    """'S/ 2,664.19' → '2664.19'; vacío/guion → ''. Lanza ValueError si no es un monto."""
    s = s.replace("S/.", "").replace("S/", "").replace(",", "").strip()
    if s in ("", "-", "--"):
        return ""
    if not _MONEY_RE.fullmatch(s):
        raise ValueError(f"monto no numérico: {s!r}")
    return s


def _clean_name(s: str) -> str:
    # SUNAT incrusta en el nombre "…, Para ver la información de remuneración, ingrese al siguiente enlace: https://…"
    return _SUNAT_NOTE_RE.sub("", s).strip()


class PtePersonalConnector:
    source = "PTE_PERSONAL"
    method = "scrape"
    confidence = 0.90

    def __init__(self, timeout: float = 50.0):
        # Diagnóstico de la última entidad barrida: errores HTTP y páginas incompletas (ver fetch_entity).
        self.failures: list[dict] = []
        self.incomplete: list[dict] = []
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
            # Se conservan las celdas vacías: si CARGO o DEPENDENCIA vienen en blanco, eliminarlas
            # desplazaba los montos a esas columnas (8,914 filas con dependencia numérica en el CSV).
            cells = [_strip(td) for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
            out.append(cells)
        return out

    def fetch_entity(
        self, id_entidad: int, anio: int, mes: int,
        regimes: list[int] | None = None, max_pages: int = 200, entity_name: str | None = None,
    ) -> Iterator[FuncionarioRow]:
        """Genera filas de funcionarios de una entidad/período, TODOS los regímenes y páginas."""
        name = entity_name or self.entity_name(self._get(id_entidad)) or f"Entidad {id_entidad}"
        self.failures, self.incomplete = [], []
        for reg in (regimes or list(REGIMES)):
            seen: set[tuple] = set()
            n_pages = None  # se fija con el enlace "Ultimo" de la primera página
            pag = 0
            while True:
                pag += 1
                if pag > max_pages or (n_pages is not None and pag > n_pages):
                    break
                try:
                    resp = self._get_query(id_entidad, anio, mes, reg, pag)
                except Exception as e:  # noqa: BLE001 — tras los reintentos: se registra, NO se asume "sin datos"
                    self.failures.append({"id_entidad": id_entidad, "anio": anio, "mes": mes, "regimen": reg,
                                          "pag": pag, "error": f"{type(e).__name__}: {e}"[:200]})
                    break
                if n_pages is None:
                    m = _ULTIMO_RE.search(resp)
                    n_pages = int(m.group(1)) if m else None
                page_rows = 0
                for cells in self._parse_rows(resp):
                    # fila de datos = exactamente 10 columnas; las de "DESCRIPCIÓN:" (2 celdas) y cabeceras se saltan
                    if len(cells) != _N_COLS:
                        continue
                    reg_txt, nombre, cargo, dep = cells[0], _clean_name(cells[1]), cells[2], cells[3]
                    if reg_txt.upper().startswith(("REGIMEN LABORAL", "RÉGIMEN LABORAL")):
                        continue  # cabecera
                    if any(h in " ".join(cells).upper() for h in _HEADER_TOKENS):
                        continue
                    if not re.search(r"[A-Za-zÁÉÍÓÚÑ]", nombre):
                        continue
                    if "," not in nombre and len(nombre.split()) < 2:
                        continue
                    try:
                        inc = [_money(c) for c in cells[4:10]]  # REMUN | HONOR | INCENT | AGUIN | OTROS | TOTAL
                    except ValueError as e:
                        self.failures.append({"id_entidad": id_entidad, "anio": anio, "mes": mes, "regimen": reg,
                                              "pag": pag, "error": f"{e} ({nombre[:40]})"})
                        continue
                    page_rows += 1
                    key = (reg, nombre, cargo, dep, *inc)
                    if key in seen:
                        continue  # el portal repite filas entre páginas (paginación inestable)
                    seen.add(key)
                    yield FuncionarioRow(
                        id_entidad=id_entidad, entidad=name, anio=anio, mes=mes,
                        regimen=REGIMES.get(reg, str(reg)),
                        apellidos_nombres=nombre, cargo=cargo, dependencia=dep,
                        remuneracion=inc[0], honorarios=inc[1], incentivo=inc[2],
                        aguinaldo=inc[3], otros=inc[4], total_ingreso_mensual=inc[5],
                        fuente_url=self._query_url(id_entidad, anio, mes, reg, pag),
                        captured_at=utcnow(),
                    )
                if n_pages is None and ("Siguiente" not in resp or page_rows == 0):
                    break  # sin enlace "Ultimo": paginación clásica
            # Páginas de 30: si faltan más de 30 filas únicas respecto a lo esperado, el régimen quedó incompleto.
            if n_pages and len(seen) < 30 * (n_pages - 1) - 30:
                self.incomplete.append({"id_entidad": id_entidad, "anio": anio, "mes": mes, "regimen": reg,
                                        "paginas": n_pages, "filas_unicas": len(seen)})


CSV_FIELDS = list(asdict(
    FuncionarioRow(0, "", 0, 0, "", "", "", "", "", "", "", "", "", "", "", "")
).keys())


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
