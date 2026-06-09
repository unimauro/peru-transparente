import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [light, setLight] = useState(() =>
    typeof document !== "undefined" && document.documentElement.classList.contains("light")
  );

  useEffect(() => {
    const el = document.documentElement;
    el.classList.toggle("light", light);
    try { localStorage.setItem("pt-theme", light ? "light" : "dark"); } catch { /* ignore */ }
  }, [light]);

  return (
    <button
      onClick={() => setLight((v) => !v)}
      title={light ? "Cambiar a modo noche" : "Cambiar a modo día"}
      aria-label="Cambiar tema"
      className="rounded-lg border border-surface/10 bg-surface/[0.03] px-2.5 py-1.5 text-sm text-ink-soft transition-colors hover:border-surface/20 hover:text-ink"
    >
      {light ? "🌙" : "☀️"}
    </button>
  );
}
