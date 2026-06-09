import { useEffect } from "react";

export function YapeModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm animate-fade-up" />
      <div
        className="relative z-10 w-full max-w-sm rounded-2xl border border-surface/10 bg-bg-deep p-6 text-center shadow-glow animate-fade-up"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          aria-label="Cerrar"
          className="absolute right-3 top-3 rounded-lg px-2 py-1 text-ink-mute transition-colors hover:bg-surface/10 hover:text-ink"
        >
          ✕
        </button>
        <div className="text-lg font-semibold text-ink">Apoya el proyecto 🙌</div>
        <p className="mt-1 text-xs text-ink-mute">Escanea el QR con Yape o usa el número.</p>

        <div className="mt-4 flex justify-center">
          <div className="rounded-xl bg-white p-3 shadow-glow">
            <img
              src="https://unimauro.github.io/salariosperu/yape.png"
              alt="Yape QR — 940 584 307"
              className="h-56 w-56 rounded-lg object-contain"
            />
          </div>
        </div>

        <div className="mt-4 text-sm font-semibold text-ink">Yape · 940 584 307</div>
        <div className="mt-0.5 text-xs text-ink-mute">Carlos Cárdenas Fernández</div>

        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <a className="btn-ghost" href="https://buymeacoffee.com/unimauro" target="_blank" rel="noreferrer">☕ Coffee</a>
          <a className="btn-ghost" href="https://wa.me/51940584307" target="_blank" rel="noreferrer">💬 WhatsApp</a>
        </div>
      </div>
    </div>
  );
}
