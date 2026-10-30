"""Minimización de datos personales en lo que se PUBLICA (Ley 29733 / docs/LEGAL.md §1-2).

Módulo común, sin dependencias, que usan todos los build_*.py antes de escribir un campo
de texto libre (cargo, dependencia, descripción, causa…) o un contacto en los JSON de
frontend/public/data. La regla es simple y conservadora:

- Una secuencia AISLADA de exactamente 8 dígitos en texto libre es, con altísima
  probabilidad, un DNI (hallazgo A2: una entidad llenó "dependencia" con el DNI del
  servidor). Se reemplaza por "DNI ****". Los RUC de empresa (11 dígitos) y los montos
  no se tocan.
- Un RUC de persona natural (10 + DNI + dígito verificador) embebe el DNI: en texto se
  enmascara y, como campo, se publica con `enmascarar_ruc_natural()` (mismo criterio que
  build_contratos.pub_ruc: nunca el RUC natural completo).
- Correos de dominios personales (gmail, hotmail, …) y celulares (9xxxxxxxx) son contacto
  personal, no institucional: no se publican aunque la fuente los exponga.

Uso:
    from pii import enmascarar_pii, email_publicable, telefono_publicable, enmascarar_ruc_natural
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

MASCARA_DNI = "DNI ****"
MASCARA_RUC = "RUC 10********"
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
    """Correo tal cual si es institucional; cadena vacía si es personal o no parece correo."""
    e = (email or "").strip()
    return e if es_correo_institucional(e) else ""


def es_celular(telefono: str | None) -> bool:
    """Teléfono móvil (9xxxxxxxx tras quitar el +51 y separadores)."""
    d = re.sub(r"\D", "", telefono or "")
    if d.startswith("51") and len(d) > 9:
        d = d[2:]
    # gob.pe a veces publica el celular truncado a 8 dígitos: también es móvil.
    return len(d) in (8, 9) and d.startswith("9")


def telefono_publicable(telefono: str | None) -> str:
    """Solo teléfonos FIJOS (institucionales); los celulares (9…) se omiten."""
    t = (telefono or "").strip()
    return "" if (not t or es_celular(t)) else t


def enmascarar_ruc_natural(ruc: str | None) -> str:
    """RUC de persona natural publicable: '10******' + 3 últimos. Jurídicas (20…) completas."""
    r = (ruc or "").strip()
    if len(r) == 11 and r.startswith("10"):
        return "10" + "*" * 6 + r[-3:]
    return r


# Texto que SUNAT incrusta en la celda del nombre del PTE (no es parte del nombre).
_SUNAT_BOILERPLATE = re.compile(r",?\s*Para ver la informaci[oó]n de remuneraci[oó]n.*$", re.I | re.S)


def limpiar_nombre(nombre: str | None) -> str:
    """Quita el texto incrustado por la fuente ('…, Para ver la información de remuneración…')."""
    return _SUNAT_BOILERPLATE.sub("", nombre or "").strip()


def nombre_publicable(nombre: str | None) -> str:
    """Nombre tal como se publica: sin boilerplate de la fuente y sin PII incrustada (DNI)."""
    return enmascarar_pii(limpiar_nombre(nombre))


def enmascarar_pii(texto: str | None) -> str:
    """Enmascara DNI sueltos, RUC naturales, correos personales y celulares en texto libre.

    Idempotente y segura sobre cualquier cadena (devuelve '' para None).
    """
    if not texto:
        return "" if texto is None else texto
    t = RUC_NATURAL.sub(MASCARA_RUC, texto)
    t = DNI_SUELTO.sub(MASCARA_DNI, t)
    t = CELULAR.sub(MASCARA_CELULAR, t)
    t = CORREO.sub(lambda m: m.group(0) if es_correo_institucional(m.group(0)) else MASCARA_CORREO, t)
    return t


def _selftest() -> None:
    assert enmascarar_pii("46081234") == MASCARA_DNI
    assert enmascarar_pii("CIRUJANO DENTISTA 46081234 RED") == f"CIRUJANO DENTISTA {MASCARA_DNI} RED"
    assert enmascarar_pii("RUC 20131370998") == "RUC 20131370998"          # empresa: intacto
    assert enmascarar_pii("12345678.50") == "12345678.50"                   # decimal: intacto
    assert enmascarar_pii("10460812349") == MASCARA_RUC
    assert enmascarar_pii("cel 987654321") == f"cel {MASCARA_CELULAR}"
    assert enmascarar_pii("+51 987 654 321") == MASCARA_CELULAR
    assert enmascarar_pii("masa S/985 234 123 al mes") == "masa S/985 234 123 al mes"   # monto: intacto
    assert enmascarar_pii("x@gmail.com") == MASCARA_CORREO
    assert enmascarar_pii("mesa@uni.edu.pe") == "mesa@uni.edu.pe"
    assert email_publicable("juan@hotmail.com") == ""
    assert email_publicable("juan@distriluz.com.pe") == "juan@distriluz.com.pe"
    assert telefono_publicable("(51)95158788") == ""
    assert telefono_publicable("51 969627733") == ""
    assert telefono_publicable("(01)4824665") == "(01)4824665"
    assert enmascarar_ruc_natural("10066033207") == "10******207"
    assert enmascarar_ruc_natural("20131370998") == "20131370998"
    assert nombre_publicable("BALBIN BURGA JOSE JOSE, Para ver la información de remuneración, ingrese al "
                             "siguiente enlace: https://www.sunat.gob.pe/x.html") == "BALBIN BURGA JOSE JOSE"
    assert nombre_publicable("PALMA VACAS, 72047116") == "PALMA VACAS, DNI ****"
    print("pii.py: selftest OK")


if __name__ == "__main__":
    _selftest()
