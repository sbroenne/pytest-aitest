/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./report.html",
    "./partials/**/*.html",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // mkdocs-material "slate" scheme with indigo primary
        // https://squidfunk.github.io/mkdocs-material/setup/changing-the-colors/
        primary: {
          DEFAULT: '#4051b5',  // material indigo primary
          50: '#e8eaf6',
          100: '#c5cae9',
          200: '#9fa8da',
          300: '#7986cb',
          400: '#5c6bc0',
          500: '#4051b5',      // main primary
          600: '#3949ab',
          700: '#303f9f',
          800: '#283593',
          900: '#1a237e',
        },
        // Slate dark mode colors from mkdocs-material
        surface: {
          DEFAULT: '#1e2129',  // --md-default-bg-color (slate)
          card: '#282c34',     // slightly elevated
          elevated: '#2d323c', // more elevated (tooltips, dropdowns)
          code: '#1c1f26',     // code blocks
        },
        // Text colors
        text: {
          DEFAULT: '#bfc7d5',  // --md-default-fg-color (slate)
          muted: '#8b949e',    // secondary text
          light: '#c9d1d9',    // slightly brighter
        },
        // Accent colors matching material
        accent: {
          DEFAULT: '#526cfe',  // indigo accent
          hover: '#6b7eff',
        },
      },
      fontFamily: {
        sans: ['Roboto', 'system-ui', 'sans-serif'],
        mono: ['Roboto Mono', 'monospace'],
      },
      boxShadow: {
        'material': '0 2px 4px -1px rgba(0,0,0,.2), 0 4px 5px 0 rgba(0,0,0,.14), 0 1px 10px 0 rgba(0,0,0,.12)',
        'material-lg': '0 5px 5px -3px rgba(0,0,0,.2), 0 8px 10px 1px rgba(0,0,0,.14), 0 3px 14px 2px rgba(0,0,0,.12)',
      },
      borderRadius: {
        'material': '4px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
