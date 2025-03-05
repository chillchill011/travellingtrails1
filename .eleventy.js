const { DateTime } = require("luxon");
const execSync = require('child_process').execSync;

module.exports = function(eleventyConfig) {
    // Passthrough copies
    eleventyConfig.addPassthroughCopy({"src/assets/js": "assets/js"});
    eleventyConfig.addPassthroughCopy({"src/assets/images": "assets/images"});
    eleventyConfig.addPassthroughCopy({"src/styles": "styles"});
    eleventyConfig.addPassthroughCopy("src/admin");
    eleventyConfig.addPassthroughCopy({"src/assets/images": "assets/images"});
    eleventyConfig.addPassthroughCopy({ "src/assets/js/navigation.js": "assets/js/navigation.js" });
    eleventyConfig.addPassthroughCopy({"src/assets/js/analytics-enhancement.js": "assets/js/analytics-enhancement.js"});
    eleventyConfig.addPassthroughCopy({"src/assets/favicon": "assets/favicon"});
    eleventyConfig.addPassthroughCopy({"src/assets/images/logo.svg": "assets/images/logo.svg"});
    eleventyConfig.addPassthroughCopy({"src/assets/images/logo.png": "assets/images/logo.png"});
    eleventyConfig.addPassthroughCopy({"src/assets/images/logo-white.svg": "assets/images/logo-white.svg"});
    eleventyConfig.addPassthroughCopy({"src/assets/images/logo-white.png": "assets/images/logo-white.png"});
    eleventyConfig.addPassthroughCopy({"src/assets/js/logo-switcher.js": "assets/js/logo-switcher.js"});
    eleventyConfig.addPassthroughCopy({"src/assets/js/map-handler.js": "assets/js/map-handler.js"});

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
        let posts = collection.getFilteredByGlob("src/blog/**/*.md")
            // Filter out draft posts in production
            .filter(post => process.env.ELEVENTY_ENV !== "production" || !post.data.draft);
            
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
        const posts = collection.getFilteredByGlob("src/blog/**/*.md")
            // Filter out draft posts in production
            .filter(post => process.env.ELEVENTY_ENV !== "production" || !post.data.draft);
        
        console.log("Found posts:", posts.length);
        return posts;
    });

    eleventyConfig.addCollection("featuredPosts", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => post.data.featured)
            // Filter out draft posts in production
            .filter(post => process.env.ELEVENTY_ENV !== "production" || !post.data.draft)
            .sort((a, b) => b.date - a.date)
            .slice(0, 6);
    });

    eleventyConfig.addCollection("homeFeatured", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => post.data.featured)
            // Filter out draft posts in production
            .filter(post => process.env.ELEVENTY_ENV !== "production" || !post.data.draft)
            .sort((a, b) => b.date - a.date)
            .slice(0, 3);
    });

    eleventyConfig.addCollection("homeRecent", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => !post.data.featured)
            // Filter out draft posts in production
            .filter(post => process.env.ELEVENTY_ENV !== "production" || !post.data.draft)
            .sort((a, b) => b.date - a.date)
            .slice(0, 9);
    });

    eleventyConfig.addCollection("paginatedPosts", function(collection) {
        return collection.getFilteredByGlob("src/blog/**/*.md")
            .filter(post => !post.data.featured)
            // Filter out draft posts in production
            .filter(post => process.env.ELEVENTY_ENV !== "production" || !post.data.draft)
            .sort((a, b) => b.date - a.date);
    });

    eleventyConfig.addCollection("categories", function(collection) {
        const posts = collection.getFilteredByGlob("src/blog/**/*.md")
            // Filter out draft posts in production
            .filter(post => process.env.ELEVENTY_ENV !== "production" || !post.data.draft);
        
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
      const pathPrefix = process.env.ELEVENTY_ENV === "production" ? "" : "/travellingtrails1";
      return `${pathPrefix}/categories/${slug}/`;
    });

    eleventyConfig.addShortcode("year", () => `${new Date().getFullYear()}`);

    eleventyConfig.addShortcode("blogImage", function(src, alt, caption) {
        const pathPrefix = process.env.ELEVENTY_ENV === "production" ? "" : "/travellingtrails1";
        return `
          <figure class="single-image" style="margin: 2rem 0;">
            <div class="image-container" style="position: relative; overflow: hidden; border-radius: 0.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
              <img 
                src="${pathPrefix}${src}"
                alt="${alt || ''}"
                class="w-full h-full object-cover"
                loading="lazy"
                style="width: 100%; height: auto;"
              />
            </div>
            ${caption ? `
              <figcaption style="margin-top: 0.5rem; font-size: 0.875rem; color: #4B5563; text-align: center;">
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
        
        const pathPrefix = process.env.ELEVENTY_ENV === "production" ? "" : "/travellingtrails1";
        
        const galleryHTML = images.map((image, index) => 
          `<div class="gallery-item">
            <div class="gallery-image-wrapper">
              <img
                src="${pathPrefix}${image.src}"
                alt="${image.alt}"
                class="gallery-image"
                loading="lazy"
              />
            </div>
          </div>`
        ).join('');
        
        return `
          <div class="gallery-container">
            <div class="gallery-grid" style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.5rem; width: 100%; padding: 1rem;">
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


    // Add destinations collection
    eleventyConfig.addCollection("destinations", function(collection) {
      const posts = collection.getFilteredByGlob("src/blog/**/*.md")
          // Filter out draft posts in production
          .filter(post => process.env.ELEVENTY_ENV !== "production" || !post.data.draft);
      
      const destinationsSet = new Set();
      
      posts.forEach(post => {
          if (post.data.destination) {
              destinationsSet.add(post.data.destination);
          }
      });
      
      const destinations = Array.from(destinationsSet).sort();
      
      return destinations.map(destination => {
          const filteredPosts = posts.filter(post => 
              post.data.destination === destination
          ).sort((a, b) => b.date - a.date);
          
          return {
              title: destination,
              slug: destination.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]+/g, ''),
              posts: filteredPosts,
              count: filteredPosts.length
          };
      });
    });

    // Add map data filter with corrected implementation
    eleventyConfig.addFilter("getDestinationsMapData", function(destinations) {
      if (!destinations || !Array.isArray(destinations)) {
        return [];
      }
      
      return destinations.map(destination => {
        // Find first post with coordinates
        const postWithCoordinates = destination.posts.find(post => 
          post.data.coordinates && 
          post.data.coordinates.latitude && 
          post.data.coordinates.longitude
        );
        
        const coordinates = postWithCoordinates?.data?.coordinates || {};
        const pathPrefix = process.env.ELEVENTY_ENV === "production" ? "" : "/travellingtrails1";
        
        return {
          title: destination.title,
          lat: coordinates.latitude,
          lng: coordinates.longitude,
          count: destination.count,
          url: `${pathPrefix}/destinations/${destination.slug}/`
        };
      }).filter(d => d.lat && d.lng); // Only include destinations with coordinates
    });

    // Function to parse duration
    eleventyConfig.addFilter("durationToDays", function(duration) {
      if (typeof duration === "number") return duration;
      
      if (typeof duration === "string") {
          const daysMatch = duration.match(/(\d+)\s*day/i);
          if (daysMatch && daysMatch[1]) {
              return parseInt(daysMatch[1]);
          }
          
          const weeksMatch = duration.match(/(\d+)\s*week/i);
          if (weeksMatch && weeksMatch[1]) {
              return parseInt(weeksMatch[1]) * 7;
          }
          
          if (/^\d+$/.test(duration)) {
              return parseInt(duration);
          }
      }
      
      return 0;
    });

    return {
        dir: {
            input: "src",
            output: "public",
            includes: "_includes",
            layouts: "_includes"
        },
        pathPrefix: process.env.ELEVENTY_ENV === "production" ? "" : "/travellingtrails1/",
        templateFormats: ["md", "njk", "html"],
        markdownTemplateEngine: "njk",
        htmlTemplateEngine: "njk",
        dataTemplateEngine: "njk"
    };
};