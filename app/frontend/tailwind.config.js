/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#0ea5e9',
        dark: '#0b1221',
        panel: '#0f172a',
      },
    },
  },
  plugins: [],
}

