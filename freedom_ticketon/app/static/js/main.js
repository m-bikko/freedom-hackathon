// Main JavaScript for Freedom Ticketon

document.addEventListener('DOMContentLoaded', function() {
    // Initialize file input handlers
    initFileInputs();
    
    // Initialize any tooltips
    initTooltips();
    
    // Add responsive navigation toggler for mobile
    initMobileNav();
});

// Handle file input displays
function initFileInputs() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const fileName = this.files[0] ? this.files[0].name : 'No file selected';
            const fileInfoElement = this.nextElementSibling.querySelector('.file-name');
            
            if (fileInfoElement) {
                fileInfoElement.textContent = fileName;
                
                // Add a visual indicator that file is selected
                const fileInfoContainer = this.nextElementSibling;
                if (this.files[0]) {
                    fileInfoContainer.classList.add('file-selected');
                } else {
                    fileInfoContainer.classList.remove('file-selected');
                }
            }
        });
    });
}

// Initialize tooltips
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        // Create tooltip element
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = element.getAttribute('data-tooltip');
        
        // Add event listeners
        element.addEventListener('mouseenter', () => {
            document.body.appendChild(tooltip);
            
            // Position the tooltip
            const rect = element.getBoundingClientRect();
            tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
            
            // Show tooltip with a delay
            setTimeout(() => {
                tooltip.classList.add('show');
            }, 200);
        });
        
        element.addEventListener('mouseleave', () => {
            tooltip.classList.remove('show');
            
            // Remove after animation
            setTimeout(() => {
                if (tooltip.parentNode) {
                    tooltip.parentNode.removeChild(tooltip);
                }
            }, 200);
        });
    });
}

// Mobile navigation toggle
function initMobileNav() {
    const navToggler = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('nav ul');
    
    if (navToggler && navMenu) {
        navToggler.addEventListener('click', () => {
            navMenu.classList.toggle('show');
        });
    }
}