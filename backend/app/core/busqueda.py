"""Saneamiento del parámetro de búsqueda libre `q` para consultas ILIKE.

- `%` y `_` son comodines de LIKE: sin escapar, `q=%` obliga a un scan completo de la tabla
  (1,6 M filas en historico.planilla) y `_` casa cualquier carácter. Se escapan con `\\` y las
  consultas usan `ESCAPE '\\'`.
- Mínimo 3 caracteres útiles: evita barridos por una sola letra (coste) y la enumeración
  masiva de nombres.
"""
from fastapi import HTTPException

Q_MIN = 3
ESCAPE = "\\"


def patron_like(q: str | None) -> str | None:
    """Devuelve el patrón '%texto%' con comodines escapados, o None si q viene vacío."""
    if q is None:
        return None
    t = q.strip()
    if not t:
        return None
    if len(t) < Q_MIN:
        raise HTTPException(422, f"q: mínimo {Q_MIN} caracteres")
    t = t.replace(ESCAPE, ESCAPE + ESCAPE).replace("%", ESCAPE + "%").replace("_", ESCAPE + "_")
    return f"%{t}%"
