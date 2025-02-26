// src/admin/preview.js
// Simple preview templates for Decap CMS

// Wait for CMS to be loaded
window.addEventListener('load', function() {
    // Make sure CMS is available
    if (!window.CMS) {
      console.error('Decap CMS not loaded');
      return;
    }
  
    // Register a custom preview for blog posts
    CMS.registerPreviewTemplate('blog', function(props) {
      const {entry, widgetFor, getAsset} = props;
      const data = entry.get('data').toJS();
      
      // Get values from the entry
      const title = data.title || 'Untitled Post';
      const date = data.date ? new Date(data.date).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      }) : '';
      const featuredImage = data.featuredImage ? getAsset(data.featuredImage).toString() : '/assets/images/placeholder.jpg';
      const categories = data.categories || [];
      
      // Create the preview HTML
      const html = `
        <div class="preview-container" style="
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
          max-width: 800px;
          margin: 0 auto;
          padding: 20px;
          color: #1f2937;
          background-color: #f9fafb;
        ">
          <article style="
            background-color: white; 
            border-radius: 8px; 
            padding: 24px; 
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
          ">
            <header style="margin-bottom: 24px;">
              <h1 style="font-size: 2rem; font-weight: bold; margin-bottom: 8px; color: #0284c7;">
                ${title}
              </h1>
              
              <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; color: #6b7280; font-size: 0.875rem;">
                ${data.author ? `<span>By ${data.author}</span>` : ''}
                ${date ? `<span>• ${date}</span>` : ''}
              </div>
              
              ${categories.length > 0 ? `
                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px;">
                  ${categories.map(category => `
                    <span style="
                      background-color: #e0f2fe; 
                      color: #0284c7;
                      padding: 4px 12px;
                      border-radius: 9999px;
                      font-size: 0.75rem;
                      font-weight: 500;
                    ">
                      ${category}
                    </span>
                  `).join('')}
                </div>
              ` : ''}
            </header>
            
            ${featuredImage ? `
              <figure style="margin-bottom: 24px;">
                <img 
                  src="${featuredImage}" 
                  alt="${data.imageAlt || title}"
                  style="
                    width: 100%; 
                    height: auto; 
                    border-radius: 6px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                  " 
                />
                ${data.imageAlt ? `
                  <figcaption style="
                    text-align: center; 
                    color: #6b7280; 
                    margin-top: 8px; 
                    font-size: 0.875rem;
                  ">
                    ${data.imageAlt}
                  </figcaption>
                ` : ''}
              </figure>
            ` : ''}
            
            <div class="blog-content" style="line-height: 1.7;">
              ${widgetFor('body')}
            </div>
            
            ${data.gallery && data.gallery.length > 0 ? `
              <div style="margin-top: 32px;">
                <h2 style="font-size: 1.5rem; font-weight: bold; margin-bottom: 16px;">Gallery</h2>
                <div style="
                  display: grid; 
                  grid-template-columns: repeat(2, 1fr); 
                  gap: 16px;
                  margin-top: 16px;
                ">
                  ${data.gallery.map(item => `
                    <div style="
                      border-radius: 6px; 
                      overflow: hidden;
                      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    ">
                      <img 
                        src="${getAsset(item.src).toString()}" 
                        alt="${item.alt}" 
                        style="width: 100%; height: 200px; object-fit: cover;" 
                      />
                    </div>
                  `).join('')}
                </div>
              </div>
            ` : ''}
          </article>
        </div>
      `;
      
      // Create a div to hold the preview
      const div = document.createElement('div');
      div.innerHTML = html;
      return div;
    });
  
    // Register the default preview CSS
    CMS.registerPreviewStyle('/styles/main.css');
  });