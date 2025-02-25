// src/_data/site.js
module.exports = {
    title: "Travelling Trails",
    description: "Discover amazing travel stories and adventures from around the world. Travel tips, guides, and inspiration for your next journey.",
    url: process.env.ELEVENTY_ENV === "production" 
      ? "https://travellingtrails.in"
      : "http://localhost:8080",
    author: "Travelling Trails Team",
    authorTwitter: "@traveltrails",
    buildTime: new Date(),
    language: "en",
    navigation: [
      { text: "Home", url: "/" },
      { text: "Blog", url: "/blog/" },
      { text: "Categories", url: "/categories/" },
      { text: "About", url: "/about/" },
      { text: "Contact", url: "/contact/" }
    ],
    basePathPrefix: process.env.ELEVENTY_ENV === "production" ? "" : "/travellingtrails1/"
  };