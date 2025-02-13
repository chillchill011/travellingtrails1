module.exports = {
  darkMode: 'class',
  content: [
    './src/**/*.{njk,md,html,js}',
  ],
  theme: {
    extend: {
      colors: {
        'travel': {
          50: '#f8fafc',
          100: '#f1f5f9',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a'
        }
      }
    }
  },
  plugins: [
    require('@tailwindcss/typography'),
  ]
};