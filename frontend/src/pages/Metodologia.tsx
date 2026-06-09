import { useEffect, useState } from "react";
import { staticData } from "@/lib/api";
import type { NationalKpis } from "@/types";
import { fmt, SectionTitle } from "@/components/ui";

function QA({ q, children }: { q: string; children: React.ReactNode }) {
  return (
    <div className="glass p-5">
      <h3 className="font-semibold text-ink">{q}</h3>
      <div className="mt-2 space-y-2 text-sm text-ink-soft">{children}</div>
    </div>
  );
}

export function Metodologia() {
  const [k, setK] = useState<NationalKpis | null>(null);
  useEffect(() => { staticData.nationalKpis().then((d) => setK(d as NationalKpis)).catch(() => {}); }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="chip mb-3">Metodología · FAQ</div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">Cómo leer estos datos</h1>
      <p className="mt-2 text-ink-soft">
        Qué es, de dónde viene, qué cubre y qué <i>no</i> cubre. Sin sobreventa: solo datos públicos, trazables a su fuente.
      </p>

      <div className="mt-8 space-y-4">
        <QA q="¿Qué es Perú Transparente?">
          <p>Una plataforma open source que consolida el <b>personal, cargos y remuneraciones</b> de las entidades del Estado peruano en un solo lugar, buscable y descargable. Cada dato enlaza a su página oficial de origen.</p>
        </QA>

        <QA q="¿Qué es el PTE (nuestra fuente principal)?">
          <p><b>PTE = Portal de Transparencia Estándar</b> (<a className="text-accent-blue underline" href="https://www.transparencia.gob.pe" target="_blank" rel="noreferrer">transparencia.gob.pe</a>): el portal oficial donde cada entidad pública debe publicar su personal, presupuesto y contrataciones. Nosotros lo leemos entidad por entidad, régimen por régimen.</p>
        </QA>

        <QA q="¿Cómo leo un registro de funcionario?">
          <ul className="list-inside list-disc space-y-1">
            <li><b>Entidad</b> y <b>dependencia</b>: dónde trabaja (ej. SUNAT → Gerencia de Sistemas).</li>
            <li><b>Cargo</b>: su puesto (Director, Jefe, Especialista, Docente…).</li>
            <li><b>Régimen</b>: su modalidad de contrato (ver abajo).</li>
            <li><b>Período</b> (mes/año): la foto a la que corresponde el dato.</li>
            <li><b>Ingreso mensual</b>: remuneración total reportada (S/).</li>
            <li><b>Fuente ↗</b>: enlace a la página exacta del PTE para verificar.</li>
          </ul>
        </QA>

        <QA q="Servidor público vs. funcionario: ¿no es lo mismo?">
          <p>No. El total ({k ? fmt.format(k.total_funcionarios) : "…"}) son <b>servidores públicos</b> (todos los que trabajan para el Estado). Dentro de ellos, los <b>cargos clave</b> ({k ? fmt.format(k.total_cargos_clave) : "…"}) son <b>funcionarios y directivos</b> — de jefe para arriba (ministros, viceministros, directores, gerentes, jefes). Es la estratificación de la Ley del Servicio Civil (Ley 30057).</p>
        </QA>

        <QA q="¿Qué regímenes laborales aparecen?">
          <p><b>CAS</b> (contrato administrativo de servicios), <b>Ley Servir</b> (servicio civil), <b>D.L. 276</b> (carrera administrativa), <b>D.L. 728</b> (régimen privado), <b>FAG/PAC/PNUD</b> (consultores), <b>Altos Funcionarios</b> (ministros, viceministros). Capturamos todos los que la entidad publique.</p>
        </QA>

        <QA q="¿Por qué algunas entidades aparecen 'sin datos'?">
          <p>Existen en el catálogo del PTE pero <b>no suben su rubro de personal</b>. Eso es un hallazgo de transparencia en sí mismo: una entidad pública que no transparenta a su personal. Lo marcamos honestamente, no inventamos datos.</p>
        </QA>

        <QA q="¿Están TODOS los docentes del país?">
          <p><b>No, y es importante decirlo.</b> Perú tiene ~500,000 docentes, pero <b>la mayoría de UGEL/DRE no los publica en el PTE</b> — los gestionan en el sistema NEXUS/SIAGIE de MINEDU. Solo capturamos los docentes de las entidades educativas que sí publican (ej. DRE Callao, MINEDU). El padrón docente completo requiere una fuente adicional (NEXUS), que está en el roadmap.</p>
        </QA>

        <QA q="¿Y las Fuerzas Armadas y la Policía?">
          <p>Ejército, Marina, FAP y PNP <b>no publican su personal individual</b> en el PTE (excepción de seguridad). Solo aparece personal administrativo de algunas (Comando Conjunto, MINDEF). Los nombramientos de generales se hacen por Resolución Suprema (El Peruano), otra fuente.</p>
        </QA>

        <QA q="Si una persona aparece en dos entidades, ¿es la misma?">
          <p>No necesariamente. Buscar por nombre puede traer <b>homónimos</b>. Confirmar que es la misma persona (ej. profesor de la UNI que también asesora en SUNAT) requiere <b>resolución de entidades</b> con DNI/contexto — la capa de IA del roadmap.</p>
        </QA>

        <QA q="¿Cada cuánto se actualiza?">
          <p>El barrido corre de forma continua y publica el avance automáticamente. La cobertura actual y la fecha se muestran en la portada.</p>
        </QA>

        <QA q="¿Puedo descargar los datos?">
          <p>Sí. El dataset completo está como CSV comprimido en el repositorio (<a className="text-accent-blue underline" href="https://github.com/unimauro/peru-transparente" target="_blank" rel="noreferrer">GitHub</a>). Código bajo AGPL-3.0, datos bajo CC BY 4.0 (con atribución a las fuentes oficiales).</p>
        </QA>
      </div>

      <div className="mt-8 glass p-5">
        <SectionTitle kicker="Principio">Anti-overclaiming</SectionTitle>
        <p className="text-sm text-ink-soft">
          Esta plataforma <b>reúne y vincula</b> datos públicos; <b>no imputa irregularidades</b>. Toda inferencia
          (posibles vínculos, conflictos) se marca como hipótesis con su nivel de confianza. Las conclusiones son del lector.
        </p>
      </div>
    </div>
  );
}
