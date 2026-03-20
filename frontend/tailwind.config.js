/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    borderRadius: {
      none: '0',
      DEFAULT: '0',
      sm: '0',
      md: '0',
      lg: '0',
      xl: '0',
      '2xl': '0',
      '3xl': '0',
      full: '0',
    },
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      colors: {
        t: {
          base: 'var(--bg-base)',
          surface: 'var(--bg-surface)',
          elevated: 'var(--bg-elevated)',
          border: 'var(--border)',
          'border-active': 'var(--border-active)',
          'text-primary': 'var(--text-primary)',
          'text-secondary': 'var(--text-secondary)',
          'text-muted': 'var(--text-muted)',
          cyan: 'var(--accent-cyan)',
          green: 'var(--accent-green)',
          red: 'var(--accent-red)',
          yellow: 'var(--accent-yellow)',
          blue: 'var(--accent-blue)',
        },
      },
    },
  },
  plugins: [],
}
