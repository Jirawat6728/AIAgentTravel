/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Noto Sans Thai", "system-ui", "ui-sans-serif", "sans-serif"],
      },
    },
  },
  plugins: [],
}

