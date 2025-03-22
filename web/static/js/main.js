// web/static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if Bootstrap is used
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Handle search form submissions
    const searchForms = document.querySelectorAll('form[action*="search"]');
    searchForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const query = form.querySelector('input[name="query"]').value.trim();
            if (!query) {
                e.preventDefault();
                alert('Please enter a search term');
            }
        });
    });

    // Fix any broken images by replacing with no-poster image
    document.querySelectorAll('img').forEach(img => {
        img.addEventListener('error', function() {
            if (!this.src.includes('no-poster.jpg')) {
                this.src = '/static/images/no-poster.jpg';
            }
        });
    });
});