document.addEventListener('DOMContentLoaded', function() {
    // Get TOC elements
    const tocToggle = document.getElementById('toc-toggle');
    const tocContent = document.getElementById('toc-content');
    const tocLinks = document.querySelectorAll('.toc-link');

    // Toggle TOC on mobile
    if (tocToggle && tocContent) {
        console.log("Found TOC toggle element:", tocToggle);
        
        // Initially collapse TOC on mobile if the screen width is small
        if (window.innerWidth < 768) {
            tocContent.classList.add('collapsed');
            tocContent.classList.remove('expanded');
        }
        
        tocToggle.addEventListener('click', function() {
            console.log("TOC toggle clicked");
            
            // Check current state and explicitly change to the opposite state
            if (tocContent.classList.contains('collapsed')) {
                tocContent.classList.remove('collapsed');
                tocContent.classList.add('expanded');
            } else {
                tocContent.classList.remove('expanded');
                tocContent.classList.add('collapsed');
            }
            
            // Toggle the arrow icon
            const svg = tocToggle.querySelector('svg');
            if (svg) {
                svg.classList.toggle('rotate-180');
            }
        });
    }    

    // Scroll spy functionality
    if (tocLinks.length > 0) {
        // Get all section elements that correspond to TOC links
        const sections = Array.from(tocLinks).map(link => {
            const id = link.getAttribute('href').substring(1);
            return document.getElementById(id);
        }).filter(Boolean);
        
        // Highlight the current section in the TOC
        const highlightCurrentSection = () => {
            // Get current scroll position
            const scrollY = window.scrollY;
            
            // Find the current section
            let currentSection = null;
            
            for (let i = 0; i < sections.length; i++) {
                const section = sections[i];
                const sectionTop = section.offsetTop - 100; // Offset for better UX
                
                if (scrollY >= sectionTop) {
                    currentSection = section;
                } else {
                    break;
                }
            }
            
            // Remove active class from all links
            tocLinks.forEach(link => {
                link.classList.remove('active');
            });
            
            // Add active class to current link
            if (currentSection) {
                const currentId = currentSection.id;
                const currentLink = document.querySelector(`.toc-link[href="#${currentId}"]`);
                
                if (currentLink) {
                    currentLink.classList.add('active');
                }
            }
        };
        
        // Add scroll event listener
        window.addEventListener('scroll', highlightCurrentSection);
        
        // Run once on load
        highlightCurrentSection();
        
        // Add smooth scrolling to TOC links
        tocLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                const targetId = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    // Scroll to the target element
                    window.scrollTo({
                        top: targetElement.offsetTop - 80,
                        behavior: 'smooth'
                    });
                    
                    // Update URL hash without scrolling
                    history.pushState(null, null, `#${targetId}`);
                }
            });
        });
    }
});