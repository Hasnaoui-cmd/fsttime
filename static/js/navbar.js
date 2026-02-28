/**
 * FSTTIME Navigation Bar JavaScript
 * Handles dropdowns, mobile menu, and keyboard navigation
 */

(function() {
    'use strict';

    // DOM Elements
    const navbar = document.getElementById('mainNavbar');
    const mobileToggle = document.getElementById('mobileToggle');
    const mobileMenu = document.getElementById('mobileMenu');
    const mobileClose = document.getElementById('mobileClose');
    const mobileOverlay = document.getElementById('mobileOverlay');
    
    // State
    let activeDropdown = null;
    let isMobileMenuOpen = false;

    /**
     * Initialize navbar functionality
     */
    function init() {
        if (!navbar) return;

        setupDesktopDropdowns();
        setupMobileMenu();
        setupMobileSubmenus();
        setupKeyboardNavigation();
        setupClickOutside();
    }

    /**
     * Desktop dropdown hover and click functionality
     */
    function setupDesktopDropdowns() {
        const dropdownItems = navbar.querySelectorAll('.nav-item.has-dropdown, .notification-dropdown, .user-dropdown');

        dropdownItems.forEach(item => {
            const toggle = item.querySelector('.nav-link, .nav-icon-btn, .user-menu-btn');
            const menu = item.querySelector('.dropdown-menu');

            if (!toggle || !menu) return;

            // Hover events (desktop)
            item.addEventListener('mouseenter', () => {
                if (window.innerWidth > 1024) {
                    openDropdown(item, toggle);
                }
            });

            item.addEventListener('mouseleave', () => {
                if (window.innerWidth > 1024) {
                    closeDropdown(item, toggle);
                }
            });

            // Click event (for mobile and accessibility)
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                if (item.classList.contains('open')) {
                    closeDropdown(item, toggle);
                } else {
                    // Close other dropdowns
                    closeAllDropdowns();
                    openDropdown(item, toggle);
                }
            });

            // Keyboard: Enter/Space to toggle
            toggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggle.click();
                }
            });
        });
    }

    /**
     * Open a dropdown menu
     */
    function openDropdown(item, toggle) {
        item.classList.add('open');
        toggle.setAttribute('aria-expanded', 'true');
        activeDropdown = item;
    }

    /**
     * Close a dropdown menu
     */
    function closeDropdown(item, toggle) {
        item.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        if (activeDropdown === item) {
            activeDropdown = null;
        }
    }

    /**
     * Close all dropdown menus
     */
    function closeAllDropdowns() {
        const openItems = navbar.querySelectorAll('.has-dropdown.open, .notification-dropdown.open, .user-dropdown.open');
        openItems.forEach(item => {
            const toggle = item.querySelector('[aria-expanded]');
            if (toggle) {
                closeDropdown(item, toggle);
            }
        });
    }

    /**
     * Mobile menu open/close functionality
     */
    function setupMobileMenu() {
        if (!mobileToggle || !mobileMenu) return;

        mobileToggle.addEventListener('click', () => {
            if (isMobileMenuOpen) {
                closeMobileMenu();
            } else {
                openMobileMenu();
            }
        });

        if (mobileClose) {
            mobileClose.addEventListener('click', closeMobileMenu);
        }

        if (mobileOverlay) {
            mobileOverlay.addEventListener('click', closeMobileMenu);
        }

        // Handle escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (isMobileMenuOpen) {
                    closeMobileMenu();
                } else if (activeDropdown) {
                    closeAllDropdowns();
                }
            }
        });
    }

    /**
     * Open mobile menu
     */
    function openMobileMenu() {
        isMobileMenuOpen = true;
        mobileMenu.classList.add('open');
        mobileMenu.setAttribute('aria-hidden', 'false');
        mobileToggle.classList.add('active');
        mobileToggle.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
        
        // Focus first interactive element
        const firstLink = mobileMenu.querySelector('a, button');
        if (firstLink) {
            setTimeout(() => firstLink.focus(), 300);
        }
    }

    /**
     * Close mobile menu
     */
    function closeMobileMenu() {
        isMobileMenuOpen = false;
        mobileMenu.classList.remove('open');
        mobileMenu.setAttribute('aria-hidden', 'true');
        mobileToggle.classList.remove('active');
        mobileToggle.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
        mobileToggle.focus();
    }

    /**
     * Mobile submenu accordion functionality
     */
    function setupMobileSubmenus() {
        const submenuToggles = document.querySelectorAll('.mobile-submenu-toggle');

        submenuToggles.forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                const parent = toggle.closest('.has-submenu');
                
                if (parent.classList.contains('open')) {
                    parent.classList.remove('open');
                } else {
                    // Close other open submenus
                    document.querySelectorAll('.mobile-nav-item.has-submenu.open').forEach(item => {
                        if (item !== parent) {
                            item.classList.remove('open');
                        }
                    });
                    parent.classList.add('open');
                }
            });
        });
    }

    /**
     * Keyboard navigation for dropdowns
     */
    function setupKeyboardNavigation() {
        navbar.addEventListener('keydown', (e) => {
            if (!activeDropdown) return;

            const menu = activeDropdown.querySelector('.dropdown-menu');
            if (!menu) return;

            const links = menu.querySelectorAll('.dropdown-link:not([hidden])');
            const currentIndex = Array.from(links).indexOf(document.activeElement);

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    if (currentIndex < links.length - 1) {
                        links[currentIndex + 1].focus();
                    } else {
                        links[0].focus();
                    }
                    break;
                    
                case 'ArrowUp':
                    e.preventDefault();
                    if (currentIndex > 0) {
                        links[currentIndex - 1].focus();
                    } else {
                        links[links.length - 1].focus();
                    }
                    break;
                    
                case 'Tab':
                    // Let default tab behavior work, but close dropdown when leaving
                    setTimeout(() => {
                        if (!activeDropdown.contains(document.activeElement)) {
                            closeAllDropdowns();
                        }
                    }, 0);
                    break;
            }
        });
    }

    /**
     * Close dropdowns when clicking outside
     */
    function setupClickOutside() {
        document.addEventListener('click', (e) => {
            if (!navbar.contains(e.target)) {
                closeAllDropdowns();
            }
        });
    }

    /**
     * Handle scroll behavior (optional: shrink navbar)
     */
    function handleScroll() {
        const scrolled = window.scrollY > 50;
        navbar.classList.toggle('scrolled', scrolled);
    }

    // Optional: Add scroll listener for shrinking effect
    // window.addEventListener('scroll', handleScroll, { passive: true });

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
