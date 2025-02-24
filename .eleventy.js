const { DateTime } = require("luxon");
const execSync = require('child_process').execSync;

module.exports = function(eleventyConfig) {
    // Passthrough copies
    eleventyConfig.addPassthroughCopy({"src/assets/js": "assets/js"});
    eleventyConfig.addPassthroughCopy({"src/assets/images": "assets/images"});
    eleventyConfig.addPassthroughCopy({"src/styles": "styles"});
    eleventyConfig.addPassthroughCopy("src/admin");
    eleventyConfig.addPassthroughCopy({"src/assets/images": "assets/images"});
    eleventyConfig.addPassthroughCopy({ "src/assets/js/lightbox.js": "assets/js/lightbox.js" });
    eleventyConfig.addPassthroughCopy({ "src/assets/js/navigation.js": "assets/js/navigation.js" });

    eleventyConfig.on('beforeBuild', () => {
        console.log('Site prefix:', eleventyConfig.pathPrefix);
      });

    // Watch targets
    eleventyConfig.addWatchTarget("./src/styles/");
    eleventyConfig.addWatchTarget("./src/assets/js/");

    // Build JavaScript if in production
    if (process.env.ELEVENTY_ENV === 'production') {
        try {
            execSync('npm run build:js');
        } catch (error) {
            console.error('Error building JavaScript:', error);
        }
    }

    // Search-specific filters
    eleventyConfig.addFilter("escape", function(str) {
        if (!str) return "";
        return str
            .replace(/\\/g, '\\\\')
            .replace(/\n/g, '\\n')
            .replace(/\r/g, '\\r')
            .replace(/\t/g, '\\t')
            .replace(/\f/g, '\\f')
            .replace(/"/g, '\\"');
    });

    eleventyConfig.addFilter("isoDate", function(date) {
        if (!date) return "";
        return DateTime.fromJSDate(date).toISO();
    });

    eleventyConfig.addFilter("striptags", function(str) {
        if (!str) return "";
        return String(str).replace(/<[^>]*>/g, '');
    });

    eleventyConfig.addFilter("dump", function(obj) {
        return JSON.stringify(obj || {});
    });

    // Add this with your other filters in .eleventy.js
    eleventyConfig.addFilter("json", function(value) {
        return JSON.stringify(value || "");
    });

    eleventyConfig.addFilter("getRelatedPosts", function(currentPost, allPosts, categories) {
      // Use the categories passed directly
      if (!categories || !Array.isArray(categories) || categories.length === 0) {
        return [];
      }
    
      // Get all posts except the current one
      const otherPosts = allPosts.filter(post => post.url !== currentPost.url);
    
      // Score each post based on category matches
      const scoredPosts = otherPosts.map(post => {
        if (!post.data.categories || !Array.isArray(post.data.categories)) {
          return { post, score: 0 };
        }
        
        const score = post.data.categories.reduce((count, category) => {
          return categories.includes(category) ? count + 1 : count;
        }, 0);
        
        return { post, score };
      });
    
      // Sort by score (highest first) and take top 3
      return scoredPosts
        .filter(item => item.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 3)
        .map(item => item.post);
    });


    // Collections
    eleventyConfig.addCollection("searchData", function(collection) {
        let posts = collection.getFilteredByGlob("src/blog/**/*.md");
        return posts.map(post => ({
            title: post.data.title || "",
            url: post.url,
            description: post.data.description || "",
            categories: post.data.categories || [],
            author: post.data.author || "",
            date: post.date,
            content: post.template?.inputContent || ""
        }));
    });

    eleventyConfig.addCollection("post", function(collection) {
        const posts = collection.getFilteredByGlob("src/blog/**/*.md");
        console.log("Found posts:", posts.length);
        return posts;
    });

    eleventyConfig.addCollection("featuredPosts", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => post.data.featured)
            .sort((a, b) => b.date - a.date)
            .slice(0, 6);
    });

    eleventyConfig.addCollection("homeFeatured", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => post.data.featured)
            .sort((a, b) => b.date - a.date)
            .slice(0, 3);
    });

    eleventyConfig.addCollection("homeRecent", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => !post.data.featured)
            .sort((a, b) => b.date - a.date)
            .slice(0, 9);
    });

    eleventyConfig.addCollection("paginatedPosts", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => !post.data.featured)
            .sort((a, b) => b.date - a.date);
    });

    eleventyConfig.addCollection("categories", function(collection) {
        const posts = collection.getFilteredByGlob("src/blog/**/*.md");
        
        const categoriesSet = new Set();
        posts.forEach(post => {
            if (post.data.categories) {
                post.data.categories.forEach(category => {
                    categoriesSet.add(category);
                });
            }
        });
        
        const categories = Array.from(categoriesSet).sort();
        
        return categories.map(category => {
            const filteredPosts = posts.filter(post => 
                post.data.categories && 
                post.data.categories.includes(category)
            ).sort((a, b) => b.date - a.date);
            
            return {
                title: category,
                slug: category.toLowerCase().replace(/\s+/g, '-'),
                posts: filteredPosts,
                count: filteredPosts.length
            };
        });
    });

    // Shortcodes
    eleventyConfig.addShortcode("categoryUrl", function(category) {
        const slug = category.toLowerCase().replace(/\s+/g, '-');
        return `/travellingtrails1/categories/${slug}/`;
    });

    eleventyConfig.addShortcode("year", () => `${new Date().getFullYear()}`);

    eleventyConfig.addShortcode("blogImage", function(src, alt, caption) {
        return `
          <figure class="single-image" data-lightbox>
            <div class="image-container">
              <img 
                src="/travellingtrails1${src}"
                alt="${alt || ''}"
                class="w-full h-full object-cover cursor-zoom-in"
                loading="lazy"
                data-lightbox-trigger
              />
            </div>
            ${caption ? `
              <figcaption class="mt-2 text-sm text-gray-600 dark:text-gray-400">
                ${caption}
              </figcaption>
            ` : ''}
          </figure>
        `;
      });
      
      eleventyConfig.addShortcode("imageGallery", function(images) {
        if (!images || !Array.isArray(images)) {
          return '';
        }
      
        const galleryHTML = images.map((image, index) => 
          `<div class="gallery-item">
            <div class="gallery-image-wrapper">
              <img
                src="/travellingtrails1${image.src}"
                alt="${image.alt}"
                class="gallery-image"
                loading="lazy"
                data-lightbox-trigger
              />
            </div>
          </div>`
        ).join('');
      
        // Note: Only one lightbox for the entire page
        return `
          <div class="gallery-container" data-lightbox-gallery>
            <div class="gallery-grid">
              ${galleryHTML}
            </div>
          </div>
        `;
      });



    // General filters
    eleventyConfig.addFilter("limit", function (arr, limit) {
        return arr.slice(0, limit);
    });

    eleventyConfig.addFilter("slice", function (arr, start, end) {
        return arr.slice(start, end);
    });

    eleventyConfig.addFilter("postDate", (dateObj) => {
        return DateTime.fromJSDate(dateObj).toLocaleString(DateTime.DATE_MED);
    });

    eleventyConfig.addFilter("date", function(date, format) {
        if (format === "yyyy") {
            return DateTime.now().year;
        }
        if (typeof date === 'string') {
            return DateTime.fromISO(date).toLocaleString(DateTime.DATE_MED);
        }
        return DateTime.fromJSDate(date).toLocaleString(DateTime.DATE_MED);
    });

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