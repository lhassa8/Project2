/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: '#C96442',
          light: '#FEF3EE',
          dark: '#A84E30',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          secondary: '#F7F5F2',
        },
        border: {
          DEFAULT: '#E8E5E0',
          strong: '#D4D0CA',
        },
        page: '#FAF9F7',
        text: {
          primary: '#1A1A1A',
          secondary: '#6B6B6B',
          tertiary: '#9B9B9B',
        },
      },
      fontFamily: {
        sans: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"SF Mono"', '"Fira Code"', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
