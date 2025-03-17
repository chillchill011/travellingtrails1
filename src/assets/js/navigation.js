// src/assets/js/navigation.js
document.addEventListener('DOMContentLoaded', function() {
  const backToTopButton = document.getElementById('back-to-top');
  const progressBar = document.getElementById('progress-bar');
  
  if (backToTopButton && progressBar) {
      // Back to Top functionality
      window.addEventListener('scroll', () => {
          // Show button when user scrolls down 200px
          if (window.scrollY > 200) {
              backToTopButton.classList.remove('translate-y-24', 'opacity-0');
              backToTopButton.classList.add('translate-y-0', 'opacity-100');
          } else {
              backToTopButton.classList.add('translate-y-24', 'opacity-0');
              backToTopButton.classList.remove('translate-y-0', 'opacity-100');
          }
          
          // Update progress bar
          const windowHeight = document.documentElement.scrollHeight - window.innerHeight;
          const scrolled = (window.scrollY / windowHeight) * 100;
          progressBar.style.width = `${scrolled}%`;
      });
  
      // Smooth scroll to top when button is clicked
      backToTopButton.addEventListener('click', () => {
          window.scrollTo({
              top: 0,
              behavior: 'smooth'
          });
      });
  
      // Initial progress bar width
      progressBar.style.width = '0%';
  }
  
  // Mobile menu functionality
  const mobileMenuButton = document.querySelector('.mobile-menu-button');
  const mobileMenu = document.querySelector('.mobile-menu');
  
  if (mobileMenuButton && mobileMenu) {
      console.log('Mobile menu button found:', mobileMenuButton);
      console.log('Mobile menu found:', mobileMenu);
      
      mobileMenuButton.addEventListener('click', function(e) {
          console.log('Mobile menu button clicked');
          e.preventDefault(); // Prevent any default action
          
          // CHANGE: Instead of toggling hidden class, use open class
          mobileMenu.classList.toggle('open');
          
          // CHANGE: Set inline style to ensure visibility
          if (mobileMenu.classList.contains('open')) {
              mobileMenu.style.display = 'block';
          } else {
              mobileMenu.style.display = 'none';
          }
          
          console.log('Menu toggled, current classes:', mobileMenu.className);
      });
  } else {
      console.log('Mobile menu button or menu not found');
  }
  
  // Mobile dropdowns
  const mobileDropdownButtons = document.querySelectorAll('.mobile-dropdown button');
  
  if (mobileDropdownButtons && mobileDropdownButtons.length > 0) {
      console.log('Found mobile dropdown buttons:', mobileDropdownButtons.length);
      
      mobileDropdownButtons.forEach(button => {
          button.addEventListener('click', function(e) {
              console.log('Dropdown button clicked');
              e.preventDefault(); // Prevent any default action
              
              // Find the dropdown content associated with this button
              const dropdownContent = this.nextElementSibling;
              console.log('Dropdown content found:', dropdownContent);
              
              // Toggle visibility
              dropdownContent.classList.toggle('hidden');
              
              // CHANGE: Set display style explicitly
              if (dropdownContent.classList.contains('hidden')) {
                  dropdownContent.style.display = 'none';
              } else {
                  dropdownContent.style.display = 'block';
              }
              
              // Toggle icon rotation
              const icon = this.querySelector('.mobile-dropdown-icon');
              if (icon) {
                  icon.classList.toggle('rotate-180');
              }
          });
      });
  } else {
      console.log('No mobile dropdown buttons found');
  }
});