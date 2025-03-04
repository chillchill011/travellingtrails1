---
permalink: /sitemap.xsl
eleventyExcludeFromCollections: true
---
<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
                xmlns:html="http://www.w3.org/TR/REC-html40"
                xmlns:sitemap="http://www.sitemaps.org/schemas/sitemap/0.9"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head>
        <title>XML Sitemap | Travelling Trails</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <style type="text/css">
          :root {
            --primary-color: #0284c7;
            --secondary-color: #0ea5e9;
            --background-color: #f3f4f6;
            --text-color: #1f2937;
            --header-bg: #ffffff;
            --border-color: #e5e7eb;
            --hover-color: #f9fafb;
          }
          
          @media (prefers-color-scheme: dark) {
            :root {
              --primary-color: #0ea5e9;
              --secondary-color: #38bdf8;
              --background-color: #1f2937;
              --text-color: #f9fafb;
              --header-bg: #111827;
              --border-color: #374151;
              --hover-color: #374151;
            }
          }
          
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 16px;
            color: var(--text-color);
            background-color: var(--background-color);
            margin: 0;
            padding: 0;
          }
          
          a {
            color: var(--primary-color);
            text-decoration: none;
          }
          
          a:hover {
            text-decoration: underline;
          }
          
          h1 {
            font-size: 24px;
            font-weight: bold;
            margin: 0;
            padding: 0;
          }
          
          #header {
            background-color: var(--header-bg);
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            position: sticky;
            top: 0;
            z-index: 100;
          }
          
          .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
          }
          
          .intro {
            margin-bottom: 20px;
          }
          
          .table-wrapper {
            overflow-x: auto;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
          }
          
          table {
            width: 100%;
            border-collapse: collapse;
            background-color: var(--header-bg);
          }
          
          th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
          }
          
          th {
            background-color: var(--header-bg);
            font-weight: bold;
            position: sticky;
            top: 61px;
            box-shadow: 0 1px 0 var(--border-color);
          }
          
          tr:hover {
            background-color: var(--hover-color);
          }
          
          .url-cell {
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          
          .priority-high {
            background-color: rgba(16, 185, 129, 0.1);
          }
          
          .priority-medium {
            background-color: rgba(245, 158, 11, 0.1);
          }
          
          .priority-low {
            background-color: rgba(239, 68, 68, 0.1);
          }
          
          .footer {
            text-align: center;
            padding: 20px;
            font-size: 14px;
            color: #6b7280;
            border-top: 1px solid var(--border-color);
          }
          
          .meta {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            font-size: 14px;
            color: #6b7280;
          }
          
          .count {
            background-color: var(--primary-color);
            color: white;
            border-radius: 9999px;
            padding: 2px 8px;
            font-size: 12px;
            margin-left: 8px;
          }
          
          @media (max-width: 768px) {
            th, td {
              padding: 8px 10px;
            }
            
            .hidden-mobile {
              display: none;
            }
          }
        </style>
      </head>
      <body>
        <div id="header">
          <div class="container">
            <h1>Travelling Trails XML Sitemap</h1>
          </div>
        </div>
        
        <div class="container">
          <div class="intro">
            <p>This is the XML sitemap for Travelling Trails, automatically generated to help search engines index this website.</p>
          </div>
          
          <div class="meta">
            <div>
              <strong>Total URLs: <span class="count"><xsl:value-of select="count(sitemap:urlset/sitemap:url)"/></span></strong>
            </div>
            <div>
              <a href="/sitemap/">View HTML Sitemap</a>
            </div>
          </div>
          
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>URL</th>
                  <th>Priority</th>
                  <th class="hidden-mobile">Last Modified</th>
                  <th class="hidden-mobile">Change Frequency</th>
                </tr>
              </thead>
              <tbody>
                <xsl:for-each select="sitemap:urlset/sitemap:url">
                  <xsl:variable name="priorityClass">
                    <xsl:choose>
                      <xsl:when test="sitemap:priority &gt;= 0.8">priority-high</xsl:when>
                      <xsl:when test="sitemap:priority &gt;= 0.5">priority-medium</xsl:when>
                      <xsl:otherwise>priority-low</xsl:otherwise>
                    </xsl:choose>
                  </xsl:variable>
                  
                  <tr class="{$priorityClass}">
                    <td class="url-cell">
                      <a href="{sitemap:loc}">
                        <xsl:value-of select="sitemap:loc"/>
                      </a>
                    </td>
                    <td>
                      <xsl:value-of select="sitemap:priority"/>
                    </td>
                    <td class="hidden-mobile">
                      <xsl:value-of select="substring(sitemap:lastmod, 0, 11)"/>
                    </td>
                    <td class="hidden-mobile">
                      <xsl:value-of select="sitemap:changefreq"/>
                    </td>
                  </tr>
                </xsl:for-each>
              </tbody>
            </table>
          </div>
        </div>
        
        <div class="footer">
          <p>Generated by Eleventy for Travelling Trails © <xsl:value-of select="substring(sitemap:urlset/sitemap:url[1]/sitemap:lastmod, 0, 5)"/></p>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>