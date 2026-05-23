/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        survivor: {
          orange: '#E8521A',
          dark: '#1A1A2E',
          gold: '#F0A500',
        },
      },
    },
  },
  plugins: [],
}
