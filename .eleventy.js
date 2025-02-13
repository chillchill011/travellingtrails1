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

    // Featured posts collection
    eleventyConfig.addCollection("featuredPosts", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => post.data.featured)
            .sort((a, b) => b.date - a.date)
            .slice(0, 6);
    });
    
    // Homepage featured posts (latest 3)
    eleventyConfig.addCollection("homeFeatured", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => post.data.featured)
            .sort((a, b) => b.date - a.date)
            .slice(0, 3);
    });

    // Homepage recent posts (latest 9 non-featured)
    eleventyConfig.addCollection("homeRecent", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => !post.data.featured)
            .sort((a, b) => b.date - a.date)
            .slice(0, 9);
    });

    // All non-featured posts for pagination
    eleventyConfig.addCollection("paginatedPosts", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => !post.data.featured)
            .sort((a, b) => b.date - a.date);
    });

    // Filters
    eleventyConfig.addFilter("limit", function (arr, limit) {
        return arr.slice(0, limit);
    });

    eleventyConfig.addFilter("slice", function (arr, start, end) {
        return arr.slice(start, end);
    });

    eleventyConfig.addFilter("postDate", (dateObj) => {
        return DateTime.fromJSDate(dateObj).toLocaleString(DateTime.DATE_MED);
    });

    // Date formatting filter
    eleventyConfig.addFilter("date", function(date, format) {
        if (format === "yyyy") {
            return DateTime.now().year;
        }
        if (typeof date === 'string') {
            return DateTime.fromISO(date).toLocaleString(DateTime.DATE_MED);
        }
        return DateTime.fromJSDate(date).toLocaleString(DateTime.DATE_MED);
    });

    // Add the year shortcode
    eleventyConfig.addShortcode("year", () => `${new Date().getFullYear()}`);

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