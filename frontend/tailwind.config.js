/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        climate: {
          blue: '#0ea5e9',
          dark: '#0284c7',
          light: '#38bdf8',
          green: '#10b981',
          'dark-green': '#059669',
          gray: '#6b7280',
        }
      }
    },
  },
  plugins: [],
}