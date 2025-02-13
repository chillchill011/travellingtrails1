// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get the mobile menu button and menu elements
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const mobileMenu = document.querySelector('.mobile-menu');

    // Add click event listener to mobile menu button
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            // Toggle the 'hidden' class on the mobile menu
            mobileMenu.classList.toggle('hidden');
        });
    }
});