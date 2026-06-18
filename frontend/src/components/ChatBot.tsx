import { useEffect, useRef, useState } from "react";
import { askGateway, staticData, type ChatMsg } from "@/lib/api";
import { renderMarkdown } from "@/lib/markdown";

// Asistente del portal. Responde SOLO con los datos de Perú Transparente
// (grounding vía bot_context.json), breve, cordial y humano, con enlaces a las
// secciones. No argumenta de más ni imputa irregularidades (anti-overclaiming).

const SECCIONES = "#/entidades · #/funcionarios · #/personas · #/autoridades · #/regiones · #/ordenes (locadores) · #/salarios · #/metodologia";

function systemPrompt(context: string): string {
  return [
    'Eres el asistente de "Perú Transparente", un portal de datos PÚBLICOS sobre el capital humano del Estado peruano.',
    "",
    "REGLAS (obligatorias):",
    "- Responde ÚNICAMENTE con la información de los DATOS DEL PORTAL de abajo. No inventes ni uses conocimiento externo.",
    "- Si la pregunta no se puede responder con estos datos, dilo con amabilidad y sugiere la sección del portal donde mirar.",
    "- Sé BREVE (1-3 frases), cordial y humano. Da el número o el resultado directo; no argumentes de más.",
    "- Puedes usar markdown ligero (negrita, listas o una tabla pequeña) SOLO si mejora la claridad de varias cifras; si no, texto corto.",
    "- Cuando ayude, incluye un enlace a la sección como ruta corta. Secciones disponibles: " + SECCIONES + ".",
    "- Anti-overclaiming: NO imputes irregularidades ni hagas acusaciones; estos datos solo describen información pública.",
    "- Responde siempre en español.",
    "",
    "DATOS DEL PORTAL:",
    context,
  ].join("\n");
}

const SUGERENCIAS = [
  "¿Cuántos servidores públicos tiene el Estado?",
  "¿Cuál es el sueldo promedio?",
  "¿Qué son los locadores de servicio?",
  "¿Qué sector tiene más personal?",
];

const BIENVENIDA =
  "Hola 👋 Soy el asistente de Perú Transparente. Pregúntame sobre el capital humano del Estado: cuántos servidores hay, sueldos, entidades, locadores… Te doy el dato y el enlace.";

export function ChatBot() {
  const [open, setOpen] = useState(false);
  const [sys, setSys] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<ChatMsg[]>([{ role: "assistant", content: BIENVENIDA }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && sys === null)
      staticData
        .botContext()
        .then((d) => setSys(systemPrompt(d.context)))
        .catch(() => setSys(systemPrompt("(datos no disponibles)")));
  }, [open, sys]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [msgs, loading]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || loading) return;
    setInput("");
    const next: ChatMsg[] = [...msgs, { role: "user", content: q }];
    setMsgs(next);
    setLoading(true);
    try {
      const history = next.filter((m) => m.role !== "system").slice(-8);
      const reply = await askGateway([
        { role: "system", content: sys ?? systemPrompt("") },
        ...history,
      ]);
      setMsgs((m) => [...m, { role: "assistant", content: reply }]);
    } catch {
      setMsgs((m) => [
        ...m,
        { role: "assistant", content: "Uy, no pude responder ahora mismo. Intenta de nuevo en un momento 🙏" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {/* Botón flotante */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Abrir asistente"
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-peru-red to-accent-cyan text-2xl shadow-glow transition-transform hover:-translate-y-0.5 active:scale-95"
      >
        {open ? "✕" : "💬"}
      </button>

      {open && (
        <div className="fixed bottom-24 right-5 z-50 flex h-[min(560px,75vh)] w-[min(380px,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-surface/10 bg-bg-base/95 shadow-glow backdrop-blur-xl">
          <div className="flex items-center gap-2 border-b border-surface/[0.06] px-4 py-3">
            <span className="text-lg">🇵🇪</span>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-ink">Asistente · Perú Transparente</div>
              <div className="text-[11px] text-ink-mute">Solo datos del portal · información pública</div>
            </div>
          </div>

          <div ref={scroller} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {msgs.map((m, i) => (
              <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
                    m.role === "user"
                      ? "bg-peru-red/15 text-ink"
                      : "bg-surface/[0.04] text-ink-soft"
                  }`}
                >
                  {m.role === "assistant" ? renderMarkdown(m.content) : m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-surface/[0.04] px-3 py-2 text-sm text-ink-mute">escribiendo…</div>
              </div>
            )}
            {msgs.length === 1 && !loading && (
              <div className="flex flex-wrap gap-2 pt-1">
                {SUGERENCIAS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="rounded-full border border-surface/10 bg-surface/[0.02] px-3 py-1.5 text-[12px] text-ink-soft transition hover:border-surface/20 hover:text-ink"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-center gap-2 border-t border-surface/[0.06] p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Pregunta sobre el capital humano…"
              className="input flex-1"
            />
            <button type="submit" disabled={loading || !input.trim()} className="btn-primary px-4 disabled:opacity-40">
              ➤
            </button>
          </form>
        </div>
      )}
    </>
  );
}
