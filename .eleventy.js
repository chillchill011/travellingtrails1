const { DateTime } = require("luxon");
const execSync = require('child_process').execSync;
const markdownIt = require("markdown-it");
const cheerio = require('cheerio');

module.exports = function(eleventyConfig) {
    // Passthrough copies
    eleventyConfig.addPassthroughCopy({"src/assets/js": "assets/js"});
    eleventyConfig.addPassthroughCopy({"src/assets/images": "assets/images"});
    eleventyConfig.addPassthroughCopy({"src/styles": "styles"});
    eleventyConfig.addPassthroughCopy("src/admin");
    eleventyConfig.addPassthroughCopy({"src/assets/favicon": "assets/favicon"});
    eleventyConfig.addPassthroughCopy({"src/assets/images/logo.svg": "assets/images/logo.svg"});
    eleventyConfig.addPassthroughCopy({"src/assets/images/logo.png": "assets/images/logo.png"});
    eleventyConfig.addPassthroughCopy({"src/assets/images/logo-white.svg": "assets/images/logo-white.svg"});
    eleventyConfig.addPassthroughCopy({"src/assets/images/logo-white.png": "assets/images/logo-white.png"});
    eleventyConfig.addPassthroughCopy({"src/assets/js/logo-switcher.js": "assets/js/logo-switcher.js"});
    eleventyConfig.addPassthroughCopy({"src/assets/js/navigation.js": "assets/js/navigation.js"});
    eleventyConfig.addPassthroughCopy({"src/assets/js/analytics-enhancement.js": "assets/js/analytics-enhancement.js"});
    eleventyConfig.addPassthroughCopy({"src/assets/js/map-handler.js": "assets/js/map-handler.js"});
    eleventyConfig.addPassthroughCopy({"src/assets/js/toc.js": "assets/js/toc.js"});

    // Add authorPages collection to generate author pages
    eleventyConfig.addCollection("authorPages", function(collectionApi) {
      // Get authors from the global data we defined earlier
      let authors = [];
      
      const fs = require('fs');
      const path = require('path');
      
      // Read authors directly from files
      const authorsDir = path.join(__dirname, 'src/_data/authors');
      if (fs.existsSync(authorsDir)) {
        try {
          const files = fs.readdirSync(authorsDir);
          files.forEach(file => {
            if (file.endsWith('.json')) {
              try {
                const authorData = JSON.parse(fs.readFileSync(path.join(authorsDir, file), 'utf8'));
                if (authorData.slug) {
                  authors.push(authorData);
                } else {
                  // Add slug if missing
                  authors.push({
                    ...authorData,
                    slug: file.replace('.json', '')
                  });
                }
              } catch (error) {
                console.warn(`Error reading author file ${file}:`, error);
              }
            }
          });
        } catch (error) {
          console.warn('Error reading authors directory:', error);
        }
      }
      
      return authors.map((author, index) => {
        return {
          ...author,
          permalink: `authors/${author.slug}/index.html`
        };
      });
    });


    // Add this to your list of filters
    eleventyConfig.addFilter("getAuthorName", function(authorSlug, authors) {
      if (!authorSlug) return "";
      
      const author = authors.find(author => author.slug === authorSlug);
      return author ? author.name : authorSlug;
    });

    // Create authors data from individual files
    const fs = require('fs');
    const path = require('path');

    eleventyConfig.addGlobalData("authors", function() {
      let authors = [];
      
      // Then try to read from the authors directory
      const authorsDir = path.join(__dirname, 'src/_data/authors');
      if (fs.existsSync(authorsDir)) {
        try {
          const files = fs.readdirSync(authorsDir);
          files.forEach(file => {
            if (file.endsWith('.json')) {
              try {
                const authorData = JSON.parse(fs.readFileSync(path.join(authorsDir, file), 'utf8'));
                
                // Check if the author data is valid
                if (!authorData.slug) {
                  console.warn(`Warning: Author file ${file} is missing a slug property`);
                  // Add a default slug based on the filename
                  authorData.slug = file.replace('.json', '');
                }
                
                // Add additional properties to help with filtering
                authorData.sourceFile = file;
                
                // Check for duplicate slugs
                const existingAuthor = authors.find(author => author.slug === authorData.slug);
                if (existingAuthor) {
                  console.warn(`Warning: Duplicate author slug "${authorData.slug}" found in files ${existingAuthor.sourceFile} and ${file}`);
                  // Make the slug unique by appending a number
                  authorData.slug = `${authorData.slug}-${authors.length + 1}`;
                  console.log(`  • Changed slug to "${authorData.slug}" to avoid conflicts`);
                }
                
                authors.push(authorData);
              } catch (error) {
                console.warn(`Error reading author file ${file}:`, error);
              }
            }
          });
        } catch (error) {
          console.warn('Error reading authors directory:', error);
        }
      }
      
      // Fallback to authors.json (legacy approach)
      if (authors.length === 0) {
        const authorsJsonPath = path.join(__dirname, 'src/_data/authors.json');
        if (fs.existsSync(authorsJsonPath)) {
          try {
            authors = JSON.parse(fs.readFileSync(authorsJsonPath, 'utf8'));
          } catch (error) {
            console.warn('Error reading authors.json:', error);
          }
        }
      }
      
      // Log author info for debugging
      if (authors.length > 0) {
        console.log(`Author slugs: ${authors.map(a => a.slug).join(', ')}`);
        // Verify all authors have slugs
        const authorsWithoutSlugs = authors.filter(a => !a.slug);
        if (authorsWithoutSlugs.length > 0) {
          console.warn(`Warning: ${authorsWithoutSlugs.length} authors are missing slugs`);
        }
      }
      
      console.log(`Loaded ${authors.length} authors`);
      return authors;
    });

    // Configure markdown parser with enhanced image rendering
    const md = markdownIt({
      html: true,
      breaks: false,
      linkify: true
    });

    eleventyConfig.addFilter("extractHeadings", function(content) {
      const $ = cheerio.load(content);
      const headings = [];
      
      // Select all h2 and h3 elements
      $('h2, h3, h4').each(function(i, elem) {
        const $elem = $(elem);
        const level = parseInt(elem.tagName.substring(1));
        const text = $elem.text();
        
        // Create ID from heading text
        const id = text
          .toLowerCase()
          .replace(/[^\w\s-]/g, '')
          .replace(/\s+/g, '-');
        
        // Add id attribute to the heading element
        $elem.attr('id', id);
        
        headings.push({
          level: level,
          text: text,
          id: id
        });
      });
      
      // Return both the extracted headings and the modified content
      return {
        headings: headings,
        content: $.html()
      };
    });
    
    // Add this to process content and add ids to headings
    eleventyConfig.addFilter("addHeadingIds", function(content) {
      const $ = cheerio.load(content);
      
      $('h2, h3, h4').each(function(i, elem) {
        const $elem = $(elem);
        const text = $elem.text();
        
        // Create ID from heading text
        const id = text
          .toLowerCase()
          .replace(/[^\w\s-]/g, '')
          .replace(/\s+/g, '-');
        
        // Add id attribute to the heading element
        $elem.attr('id', id);
      });
      
      return $.html();
    });


    // Add this in the module.exports
    eleventyConfig.addFilter("findAuthor", function(authorSlug, authors) {
      return authors.find(author => author.slug === authorSlug);
    });

    // Improved filter function with case insensitivity and data type handling
    eleventyConfig.addFilter("filter", function(array, property, value) {
      // Make sure array is an array
      if (!Array.isArray(array)) {
        return [];
      }
      
      // Convert value to lowercase for case-insensitive comparison
      const searchValue = typeof value === 'string' ? value.toLowerCase() : value;
      
      return array.filter(item => {
        if (!item.data || item.data[property] === undefined) return false;
        
        const itemValue = item.data[property];
        
        // Handle different data types for the comparison
        if (typeof itemValue === 'string') {
          return itemValue.toLowerCase() === searchValue;
        } else if (Array.isArray(itemValue)) {
          return itemValue.some(val => 
            typeof val === 'string' ? val.toLowerCase() === searchValue : val === searchValue
          );
        } else {
          return itemValue === searchValue;
        }
      });
    });

    // Custom renderer for images that converts them to figures with captions
    const defaultImageRenderer = md.renderer.rules.image;
    md.renderer.rules.image = function(tokens, idx, options, env, self) {
      const token = tokens[idx];
      const altText = token.content;
      const title = token.attrGet('title');
      
      if (title) {
        // Get the src attribute
        const srcIndex = token.attrIndex('src');
        const src = token.attrs[srcIndex][1];
        const pathPrefix = process.env.ELEVENTY_ENV === "production" ? "" : "/travellingtrails1";
        
        // Return a figure with caption - using compact format to avoid markdown processing issues
        return `<figure class="single-image" style="margin: 2rem 0;"><div class="image-container" style="position: relative; overflow: hidden; border-radius: 0.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);"><img src="${src}" alt="${altText || ''}" class="w-full object-cover" loading="lazy" style="width: 100%; height: auto; display: block; margin: 0;"></div><figcaption style="margin-top: 0.25rem; font-size: 0.875rem; color: #4B5563; text-align: center; padding: 0;">${title}</figcaption></figure>`;
      }
  
      // If no title, use the default renderer
      return defaultImageRenderer(tokens, idx, options, env, self);
    };

    eleventyConfig.setLibrary("md", md);

    // Add transform to clean up unwanted paragraph tags
    eleventyConfig.addTransform("cleanupHtml", function(content, outputPath) {
      if (outputPath && outputPath.endsWith(".html")) {
        // Remove empty paragraphs
        content = content.replace(/<p><\/p>/g, '');
        
        // Fix figure + figcaption structure by removing p tags
        content = content.replace(/<\/div><p>(\s*)<\/p>/g, '</div>');
        content = content.replace(/<p>(\s*)<\/p><figcaption/g, '<figcaption');
        
        // Remove any br tags
        content = content.replace(/<br\s*\/?>/g, '');
        
        // Clean up multiple paragraphs 
        content = content.replace(/<p>(\s*)<\/p>\s*<p>(\s*)<\/p>/g, '');
      }
      return content;
    });

    // Debug function to log author information and post relationships
    eleventyConfig.on('beforeBuild', () => {
      console.log('Site prefix:', eleventyConfig.pathPrefix);
      
      // This will run at the start of the build process
      console.log('=== Debugging Author Information ===');
      
      // Get a list of all author files
      const fs = require('fs');
      const path = require('path');
      const authorsDir = path.join(__dirname, 'src/_data/authors');
      
      if (fs.existsSync(authorsDir)) {
        const files = fs.readdirSync(authorsDir);
        console.log(`Found ${files.length} author files`);
        
        files.forEach(file => {
          if (file.endsWith('.json')) {
            try {
              const authorData = JSON.parse(fs.readFileSync(path.join(authorsDir, file), 'utf8'));
              console.log(`- Author: ${authorData.name}, Slug: ${authorData.slug || file.replace('.json', '')}`);
            } catch (error) {
              console.warn(`  Error reading ${file}: ${error.message}`);
            }
          }
        });
      } else {
        console.log('Authors directory not found at:', authorsDir);
      }
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

    eleventyConfig.addFilter("json", function(value) {
        return JSON.stringify(value || "");
    });

    // Updated getRelatedPosts to handle string categories
    eleventyConfig.addFilter("getRelatedPosts", function(currentPost, allPosts, categories) {
      // Handle single category case
      if (typeof categories === 'string') {
        categories = [categories];
      }
      
      // Use the categories passed directly
      if (!categories || !Array.isArray(categories) || categories.length === 0) {
        return [];
      }
    
      // Get all posts except the current one
      const otherPosts = allPosts.filter(post => post.url !== currentPost.url);
    
      // Score each post based on category matches
      const scoredPosts = otherPosts.map(post => {
        if (!post.data.categories) {
          return { post, score: 0 };
        }
        
        let score = 0;
        if (typeof post.data.categories === 'string') {
          // Handle single category (string)
          score = categories.includes(post.data.categories) ? 1 : 0;
        } else if (Array.isArray(post.data.categories)) {
          // Handle multiple categories (array)
          score = post.data.categories.reduce((count, category) => {
            return categories.includes(category) ? count + 1 : count;
          }, 0);
        }
        
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

    // Updated categories collection to handle string categories
    eleventyConfig.addCollection("categories", function(collection) {
        const posts = collection.getFilteredByGlob("src/blog/**/*.md")
            // Filter out draft posts in production
            .filter(post => process.env.ELEVENTY_ENV !== "production" || !post.data.draft);
        
        const categoriesSet = new Set();
        posts.forEach(post => {
            if (post.data.categories) {
                if (typeof post.data.categories === 'string') {
                    // Handle single category (string)
                    categoriesSet.add(post.data.categories);
                } else if (Array.isArray(post.data.categories)) {
                    // Handle multiple categories (array)
                    post.data.categories.forEach(category => {
                        categoriesSet.add(category);
                    });
                }
            }
        });
        
        const categories = Array.from(categoriesSet).sort();
        
        return categories.map(category => {
            // Updated to handle string categories
            const filteredPosts = posts.filter(post => {
                if (!post.data.categories) return false;
                
                if (typeof post.data.categories === 'string') {
                    return post.data.categories === category;
                } else if (Array.isArray(post.data.categories)) {
                    return post.data.categories.includes(category);
                }
                
                return false;
            }).sort((a, b) => b.date - a.date);
            
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
      return `<figure class="single-image" style="margin: 2rem 0;"><div class="image-container" style="position: relative; overflow: hidden; border-radius: 0.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);"><img src="${pathPrefix}${src}" alt="${alt || ''}" class="w-full object-cover" loading="lazy" style="width: 100%; height: auto; display: block; margin: 0;"></div>${caption ? `<figcaption style="margin-top: 0.25rem; font-size: 0.875rem; color: #4B5563; text-align: center; padding: 0;">${caption}</figcaption>` : ''}</figure>`;
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

    // Add map data filter
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