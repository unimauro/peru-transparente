/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        peru: { red: "#D91023", dark: "#0b0f17", panel: "#111827" },
        conf: { high: "#16a34a", mid: "#d97706", low: "#6b7280" },
      },
      fontFamily: { sans: ["Inter", "IBM Plex Sans", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
