/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: { base: "#070b12", deep: "#05080e" },
        ink: { DEFAULT: "#e6edf6", soft: "#aab6c6", mute: "#6b7888", faint: "#454f5e" },
        peru: { red: "#e11d2a", redsoft: "#ff5d6c" },
        accent: { blue: "#4f8cff", violet: "#a78bfa", cyan: "#22d3ee", amber: "#f59e0b" },
        conf: { high: "#22c55e", mid: "#f59e0b", low: "#6b7280" },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(255,255,255,0.05), 0 20px 60px -20px rgba(225,29,42,0.25)",
        card: "0 1px 0 rgba(255,255,255,0.04) inset, 0 12px 40px -24px rgba(0,0,0,0.8)",
      },
      backgroundImage: {
        mesh:
          "radial-gradient(60% 60% at 85% 8%, rgba(225,29,42,0.18) 0%, rgba(225,29,42,0) 60%), radial-gradient(50% 50% at 10% 100%, rgba(79,140,255,0.10) 0%, rgba(79,140,255,0) 60%)",
        grid:
          "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
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
