/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#1a1a18",
          muted: "#5c5a54",
        },
        paper: {
          DEFAULT: "#f3f1ec",
          elev: "#faf9f6",
        },
        line: "#d9d5cc",
        accent: {
          DEFAULT: "#0f5c4c",
          soft: "#e4f0ec",
        },
        warn: {
          DEFAULT: "#7a3e1d",
          soft: "#f3ebe4",
        },
      },
      fontFamily: {
        sans: ["var(--font-body)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
