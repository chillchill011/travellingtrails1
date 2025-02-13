const { DateTime } = require("luxon");

module.exports = function(eleventyConfig) {
    // Passthrough file copies
    eleventyConfig.addPassthroughCopy({"src/assets/js": "assets/js"});
    eleventyConfig.addPassthroughCopy({"src/assets/images": "assets/images"});
    eleventyConfig.addPassthroughCopy({"src/styles": "styles"});
    eleventyConfig.addPassthroughCopy("src/admin");

    // Watch targets
    eleventyConfig.addWatchTarget("./src/styles/");
    eleventyConfig.addWatchTarget("./src/assets/js/");

    // Collections
    eleventyConfig.addCollection("post", function(collection) {
        const posts = collection.getFilteredByGlob("src/blog/**/*.md");
        console.log("Found posts:", posts.length);
        return posts;
    });

    // Filters
    eleventyConfig.addFilter("limit", function (arr, limit) {
        return arr.slice(0, limit);
    });

    eleventyConfig.addFilter("postDate", (dateObj) => {
        return DateTime.fromJSDate(dateObj).toLocaleString(DateTime.DATE_MED);
    });

    eleventyConfig.addFilter("date", (dateObj, format) => {
        if (format === "yyyy") {
            return DateTime.now().year;
        }
        return DateTime.fromJSDate(dateObj).toLocaleString(DateTime.DATE_MED);
    });

    // Add the year shortcode
    eleventyConfig.addShortcode("year", () => `${new Date().getFullYear()}`);

    let pathPrefix = "";
    if (process.env.ELEVENTY_ENV === 'production') {
        pathPrefix = "/travellingtrails1/";
    }

    return {
        dir: {
            input: "src",
            output: "public",
            includes: "_includes",
            layouts: "_includes"
        },
        pathPrefix: "/travellingtrails1/",
        templateFormats: ["md", "njk", "html"],
        markdownTemplateEngine: "njk",
        htmlTemplateEngine: "njk",
        dataTemplateEngine: "njk"
    };
};