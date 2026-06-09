/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: { base: "rgb(var(--bg-base) / <alpha-value>)", deep: "rgb(var(--bg-deep) / <alpha-value>)" },
        ink: {
          DEFAULT: "rgb(var(--ink) / <alpha-value>)",
          soft: "rgb(var(--ink-soft) / <alpha-value>)",
          mute: "rgb(var(--ink-mute) / <alpha-value>)",
          faint: "rgb(var(--ink-faint) / <alpha-value>)",
        },
        surface: "rgb(var(--surface) / <alpha-value>)",
        peru: { red: "#e11d2a", redsoft: "rgb(var(--peru-soft) / <alpha-value>)" },
        accent: { blue: "#4f8cff", violet: "#a78bfa", cyan: "#1aa3c0", amber: "#d97706" },
        conf: { high: "#16a34a", mid: "#d97706", low: "#6b7280" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"], display: ["Inter", "system-ui", "sans-serif"] },
      boxShadow: {
        glow: "0 10px 40px -16px rgba(225,29,42,0.35)",
        card: "0 1px 0 rgb(var(--surface) / 0.04) inset, 0 12px 40px -24px rgba(0,0,0,0.6)",
      },
      keyframes: {
        "fade-up": { "0%": { opacity: "0", transform: "translateY(8px)" }, "100%": { opacity: "1", transform: "none" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
      },
      animation: { "fade-up": "fade-up .5s ease both" },
    },
  },
  plugins: [],
};
