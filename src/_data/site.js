// src/_data/site.js
module.exports = {
  title: "Travelling Trails",
  description: "First-person motorcycle rides, weekend escapes and honest travel stories from Maharashtra, with photographs, route notes and moments worth remembering.",
  socialImage: "/assets/images/logo.png",
  socialImageAlt: "Travelling Trails logo",
  isPreview: ["deploy-preview", "branch-deploy"].includes(process.env.CONTEXT || ""),
  url: process.env.ELEVENTY_ENV === "production" 
    ? "https://travellingtrails.in"
    : "http://localhost:8080",
  author: "Travelling Trails Team",
  buildTime: new Date(),
  language: "en",
  navigation: [
    { text: "Home", url: "/" },
    { text: "Blog", url: "/blog/" },
    { text: "Explore", url: "/explore/" },
    { text: "Categories", url: "/categories/" },
    { text: "Team", url: "/team/" },
    { text: "About", url: "/about/" },
    { text: "Contact", url: "/contact/" }
  ],
  footerNavigation: [
    { text: "Privacy Policy", url: "/privacy-policy/" },
    { text: "Sitemap", url: "/sitemap/" },
    { text: "XML Sitemap", url: "/sitemap.xml" }
  ],
  basePathPrefix: process.env.ELEVENTY_ENV === "production" ? "" : "/travellingtrails1/",
  analyticsId: process.env.ELEVENTY_ENV === "production" ? "G-M9Y3FC1B03" : ""
};