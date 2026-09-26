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
          'blue-dark': '#0284c7',
          'blue-light': '#38bdf8',
          green: '#10b981',
          'green-dark': '#059669',
          gray: '#6b7280',
          // Aliases kept for backwards-compat with existing class names
          dark: '#0284c7',
          light: '#38bdf8',
          'dark-green': '#059669',
        },
        pit: {
          DEFAULT: '#0b0e11',
          2: '#12161b',
          3: '#1a2027',
        },
        paper: '#ede8dc',
        signal: '#e5484d',
        moss: '#3d8b5f',
        amberx: '#d98e32',
      }
    },
  },
  plugins: [],
}