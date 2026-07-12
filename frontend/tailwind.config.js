/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        agora: {
          50:  "#f0f4ff",
          100: "#dce6ff",
          200: "#b8ccff",
          300: "#85a8ff",
          400: "#4d7fff",
          500: "#2563eb",
          600: "#1d4ed8",
          700: "#1e3a8a",
          800: "#1e2d6b",
          900: "#0f1a45",
        },
        teal: {
          50:  "#f0fdfa",
          400: "#2dd4bf",
          600: "#0d9488",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};
