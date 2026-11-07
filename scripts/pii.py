"""Punto único de política de datos personales en lo que se PUBLICA (docs/LEGAL.md).

Decisión del dueño del portal (2026-10-30): el DNI y el RUC se publican COMPLETOS, tal como
los publica la fuente oficial y con su enlace (Ley 27806; Ley 29733 art. 14: fuentes accesibles
al público; OECE/SEACE publica el RUC de proveedores; RNSSC/SERVIR el documento del sancionado;
el PTE el campo donde la entidad puso el DNI). Finalidad: control ciudadano de contrataciones,
conflictos de interés y duplicidad de funciones (cruce contratista ↔ planilla por DNI).

Ampliación (mismo día): también el CONTACTO (correos y teléfonos, incluidos celulares y
dominios personales) se publica tal como lo trae la fuente oficial de datos abiertos
(directorio gob.pe), siempre con su procedencia (`url`/`fuente_url` por registro). Este módulo
es el único punto que decide eso: `enmascarar_pii`, `email_publicable` y `telefono_publicable`
son hoy passthrough; para revertir, basta con volver a filtrar aquí (las listas de dominios
personales y la detección de celular se conservan para ese caso).

Uso:
    from pii import enmascarar_pii, email_publicable, telefono_publicable, nombre_publicable
"""
from __future__ import annotations

import re

# 8 dígitos aislados (no parte de un número más largo ni de un decimal "12345678.50").
DNI_SUELTO = re.compile(r"(?<!\d)(?<!\d\.)\d{8}(?!\d)(?!\.\d)")
# RUC de persona natural: 10 + 9 dígitos.
RUC_NATURAL = re.compile(r"(?<!\d)10\d{9}(?!\d)")
CORREO = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
# Celular peruano: 9 dígitos que empiezan en 9, con o sin +51 y separadores.
# (no confundir con montos "S/985 234 123": los separadores de miles son espacios)
CELULAR = re.compile(r"(?<!\d)(?<!\d )(?<!S/)(?<!S/ )(?<!\$)(?<!\$ )(?:\+?51[\s.-]?)?9\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?!\d)")

DOMINIOS_PERSONALES = (
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.es", "hotmail.com.pe", "outlook.com",
    "outlook.es", "outlook.com.pe", "live.com", "live.com.pe", "msn.com", "yahoo.com", "yahoo.es",
    "yahoo.com.pe", "ymail.com", "icloud.com", "me.com", "mac.com", "aol.com", "protonmail.com",
    "proton.me", "zoho.com", "mail.com", "terra.com.pe", "speedy.com.pe",
)
# Dominios institucionales: Estado (.gob.pe), universidades (.edu.pe), FF.AA. (.mil.pe) y
# demás .pe de la propia entidad (empresas públicas en .com.pe / .org.pe, p. ej. distriluz).
DOMINIO_INSTITUCIONAL = re.compile(r"(\.gob\.pe|\.edu\.pe|\.mil\.pe|\.org\.pe|\.com\.pe|\.pe|\.gov|\.edu|\.org|\.int)$")

MASCARA_CORREO = "[correo personal omitido]"
MASCARA_CELULAR = "[celular omitido]"


def es_correo_institucional(email: str | None) -> bool:
    """True solo para correos de dominio institucional (gob.pe, edu.pe, .pe de la entidad…)."""
    e = (email or "").strip().lower()
    if "@" not in e:
        return False
    dominio = e.rsplit("@", 1)[1]
    if dominio in DOMINIOS_PERSONALES or any(dominio.endswith("." + d) for d in DOMINIOS_PERSONALES):
        return False
    return bool(DOMINIO_INSTITUCIONAL.search(dominio))


def email_publicable(email: str | None) -> str:
    """Correo tal como lo publica la fuente (passthrough; decisión 2026-10-30).

    Para volver a publicar solo institucionales: `return e if es_correo_institucional(e) else ""`.
    """
    return (email or "").strip()


def es_celular(telefono: str | None) -> bool:
    """Teléfono móvil (9xxxxxxxx tras quitar el +51 y separadores)."""
    d = re.sub(r"\D", "", telefono or "")
    if d.startswith("51") and len(d) > 9:
        d = d[2:]
    # gob.pe a veces publica el celular truncado a 8 dígitos: también es móvil.
    return len(d) in (8, 9) and d.startswith("9")


def telefono_publicable(telefono: str | None) -> str:
    """Teléfono tal como lo publica la fuente (passthrough; decisión 2026-10-30).

    Para volver a omitir celulares: `return "" if es_celular(t) else t`.
    """
    return (telefono or "").strip()


def es_dni(valor: str | None) -> bool:
    """Exactamente 8 dígitos (un DNI puesto como valor de campo)."""
    return bool(re.fullmatch(r"\d{8}", (valor or "").strip()))


def dni_de_ruc(ruc: str | None) -> str:
    """DNI embebido en el RUC de persona natural (10 + DNI + dígito verificador); '' si no aplica."""
    r = (ruc or "").strip()
    return r[2:10] if len(r) == 11 and r.startswith("10") else ""


# Texto que SUNAT incrusta en la celda del nombre del PTE (no es parte del nombre).
_SUNAT_BOILERPLATE = re.compile(r",?\s*Para ver la informaci[oó]n de remuneraci[oó]n.*$", re.I | re.S)


def limpiar_nombre(nombre: str | None) -> str:
    """Quita el texto incrustado por la fuente ('…, Para ver la información de remuneración…')."""
    return _SUNAT_BOILERPLATE.sub("", nombre or "").strip()


def nombre_publicable(nombre: str | None) -> str:
    """Nombre tal como se publica: sin el boilerplate de la fuente (el DNI, si viene, se conserva)."""
    return enmascarar_pii(limpiar_nombre(nombre))


def enmascarar_pii(texto: str | None) -> str:
    """Texto libre tal cual (passthrough): DNI, RUC, correos y teléfonos se publican como vienen
    de la fuente oficial (decisión 2026-10-30). Devuelve '' para None. Para revertir, aplicar aquí
    CELULAR.sub(MASCARA_CELULAR, …) y CORREO.sub(… es_correo_institucional …).
    """
    return "" if texto is None else texto


def _selftest() -> None:
    assert enmascarar_pii("46081234") == "46081234"                         # DNI: se conserva
    assert enmascarar_pii("RUC 20131370998") == "RUC 20131370998"
    assert enmascarar_pii("10460812349") == "10460812349"                   # RUC natural: se conserva
    assert es_dni("46081234") and not es_dni("4608123") and not es_dni("46081234.5")
    assert dni_de_ruc("10066033207") == "06603320" and dni_de_ruc("20131370998") == ""
    assert enmascarar_pii("cel 987654321") == "cel 987654321"
    assert enmascarar_pii("x@gmail.com") == "x@gmail.com"
    assert email_publicable("juan@hotmail.com") == "juan@hotmail.com"
    assert telefono_publicable("(51)95158788") == "(51)95158788"
    assert telefono_publicable("(01)4824665") == "(01)4824665"
    # las detecciones siguen disponibles por si se revierte la política
    assert es_celular("(51)95158788") and not es_celular("(01)4824665")
    assert not es_correo_institucional("juan@hotmail.com") and es_correo_institucional("mesa@uni.edu.pe")
    assert nombre_publicable("BALBIN BURGA JOSE JOSE, Para ver la información de remuneración, ingrese al "
                             "siguiente enlace: https://www.sunat.gob.pe/x.html") == "BALBIN BURGA JOSE JOSE"
    assert nombre_publicable("PALMA VACAS, 72047116") == "PALMA VACAS, 72047116"
    print("pii.py: selftest OK")


if __name__ == "__main__":
    _selftest()
