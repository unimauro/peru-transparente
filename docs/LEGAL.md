# Marco legal y ético

Perú Transparente **republica datos de fuentes oficiales de acceso público** (PTE, directorios gob.pe, OECE/SEACE, RNSSC de SERVIR, datos abiertos de la CGR y del MEF, El Peruano), amparado en el derecho fundamental de acceso a la información pública, y lo hace **siempre con su procedencia** (enlace a la fuente oficial en cada dato).

## Marco normativo peruano
- **Ley N.º 27806** — Ley de Transparencia y Acceso a la Información Pública (TUO DS 021-2019-JUS): la información que producen las entidades del Estado (personal, remuneraciones, contrataciones) es pública.
- **Ley N.º 29733** — Ley de Protección de Datos Personales y su reglamento. **Art. 14**: no se requiere consentimiento del titular cuando los datos provienen de **fuentes accesibles al público**.
- **D. Leg. N.º 1412** (Gobierno Digital) y normativa del **OECE/SEACE**: el portal de contrataciones abiertas (OCDS) publica el **RUC de cada proveedor** adjudicado.
- **RNSSC (SERVIR)**: el Registro Nacional de Sanciones contra Servidores Civiles publica el **número de documento** del sancionado.
- **DS N.º 029-2021-PCM** — Reglamento de la Ley de Gobierno Digital / interoperabilidad.
- Portal de Transparencia Estándar (PTE) y Datos Abiertos del Estado (datosabiertos.gob.pe).

## Principios
1. **Solo información pública, tal como la publica la fuente.** Publicamos el **DNI y el RUC completos** cuando la fuente oficial los publica (RUC de proveedores en OECE/SEACE —el RUC de persona natural contiene el DNI—, documento de sancionados en el RNSSC, DNI que algunas entidades ponen en su planilla del PTE), siempre **con el enlace a esa fuente**. Decisión del titular del portal, 2026-10-30.
2. **Contacto tal como lo publica la fuente.** El correo y el teléfono de las autoridades (incluidos celulares y dominios personales) se republican **tal como los publica el directorio oficial de gob.pe** —fuente accesible al público (Ley 29733, art. 14)—, con el enlace a la ficha de cada autoridad. No se publica ningún contacto que no provenga de una fuente pública identificable. La política vive en un único punto, `scripts/pii.py`, para poder revertirla.
2b. **Procedencia visible.** Cada registro de persona, orden, contrato, sanción o autoridad lleva `url`/`fuente_url` a la página oficial concreta y cada archivo `_meta.fuente` + `_meta.fuente_url`; el validador de publicación (`scripts/validar_publicacion.py`) rechaza archivos de personas sin procedencia. En la interfaz, cada dato muestra un enlace "fuente ↗".
3. **Finalidad legítima y declarada.** Control ciudadano de las contrataciones, detección de **conflictos de interés, duplicidad de funciones** (una misma persona en planilla y como contratista), colusión y posibles ilegalidades; periodismo de datos e investigación. El cruce contratista ↔ planilla se hace por **DNI** cuando ambas fuentes lo traen y, si no, por nombre normalizado (marcado `POSSIBLE_` / homónimo posible).
4. **Trazabilidad.** Todo dato cita su fuente, URL y fecha; cualquiera puede verificar el original.
5. **Anti-overclaiming.** La plataforma no imputa responsabilidades ni afirma irregularidades; una coincidencia se presenta como coincidencia, con su tipo (por DNI / por nombre) y su nivel de confianza. Las conclusiones son del lector.
6. **Derecho de rectificación.** Canal: **carlos@cardenas.pe**. Indica la ficha (URL), el dato y la fuente; se revisa contra la fuente oficial (que prevalece) y la corrección se propaga en el siguiente refresco. Las solicitudes de supresión de cruces inferidos (coincidencias por nombre) se atienden aunque el dato de la fuente siga publicado.
7. **Minimización en lo inferido.** El índice de sanciones por nombre no republica la *causa* textual (solo tipo, entidad, fecha y documento); el detalle está en la fuente.

## Licenciamiento
- Código: **AGPL-3.0**.
- Datos derivados: **CC BY 4.0** con atribución a las fuentes oficiales.

## Exención de responsabilidad
Los datos provienen de fuentes oficiales y pueden contener errores propios del origen. Perú Transparente no garantiza exactitud absoluta y no sustituye a los portales oficiales. Para uso legal o decisiones formales, acudir a la fuente primaria citada.
