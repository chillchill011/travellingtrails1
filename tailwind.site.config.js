// Match the previous public CDN setup; also scan generated HTML for dynamic classes.
const base = require('./tailwind.config.js');
module.exports = { ...base, plugins: [], content: [...base.content, './.eleventy.js', './public/**/*.html'] };
