---
title: Test Post
description: This is a test post
date: 2025-02-13
layout: article.njk
featured: true
author: John Doe 
featuredImage: /assets/images/featured.jpg
imageAlt: Mountain landscape
gallery:
  - src: /assets/images/gallery-1.jpg
    alt: Mountain vista
    caption: Beautiful sunrise
    credit: John Doe
  - src: /assets/images/gallery-2.jpg
    alt: Forest trail
    caption: Hidden path
    credit: Jane Smith
  - src: /assets/images/gallery-3.jpg
    alt: Forest trail
    caption: Hidden path
    credit: Jane Smith
  - src: /assets/images/gallery-4.jpg
    alt: Forest trail
    caption: Hidden path
    credit: Jane Smith
---

This is a test post.
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur quis metus justo. Sed dignissim aliquam consequat. Maecenas et posuere lacus. Mauris nisi metus, mollis quis turpis eget, venenatis vestibulum risus. Phasellus vel turpis mi. Cras egestas vel mauris a cursus. Morbi justo enim, malesuada et nibh imperdiet, pretium iaculis augue.

Here is the normal image:

{% blogImage "/assets/images/placeholder.jpg", "Placeholder", "Placeholder" %}

#### Photo Gallery
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur quis metus justo. Sed dignissim aliquam consequat. Maecenas et posuere lacus. Mauris nisi metus, mollis quis turpis eget, venenatis vestibulum risus. Phasellus vel turpis mi. Cras egestas vel mauris a cursus. Morbi justo enim, malesuada et nibh imperdiet, pretium iaculis augue.


{% imageGallery gallery %}