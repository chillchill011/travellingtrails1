console.log('ELEVENTY_ENV:', process.env.ELEVENTY_ENV);
console.log('NODE_ENV:', process.env.NODE_ENV);

module.exports = {
  plugins: [
    require('postcss-import'),
    require('tailwindcss/nesting'),
    require('tailwindcss'),
    require('autoprefixer'),
    process.env.ELEVENTY_ENV === 'production' && require('cssnano')({
      preset: 'default'
    })
  ].filter(Boolean)
};