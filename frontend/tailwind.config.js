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
        surface: {
          bg: '#080c14',
          card: '#0d131f',
          'card-hover': '#121b2b',
          panel: '#0a0f19',
          elevated: '#141e30',
          border: '#1a2436',
          'border-subtle': '#151d2c',
          'border-active': '#26354d',
        },
        accent: {
          cyan: '#0ea5e9',
          sky: '#38bdf8',
          blue: '#3b82f6',
          indigo: '#6366f1',
          purple: '#8b5cf6',
          emerald: '#10b981',
          amber: '#f59e0b',
          rose: '#f43f5e',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      boxShadow: {
        'subtle': '0 1px 2px 0 rgba(0, 0, 0, 0.4)',
        'panel': '0 4px 20px -2px rgba(0, 0, 0, 0.5)',
        'halo-amber': '0 0 0 1px rgba(245, 158, 11, 0.3), 0 0 20px -3px rgba(245, 158, 11, 0.25)',
        'halo-cyan': '0 0 0 1px rgba(14, 165, 233, 0.3), 0 0 20px -3px rgba(14, 165, 233, 0.25)',
        'halo-rose': '0 0 0 1px rgba(244, 63, 94, 0.3), 0 0 20px -3px rgba(244, 63, 94, 0.25)',
      }
    },
  },
  plugins: [],
}

