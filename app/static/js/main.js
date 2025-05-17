// Main JavaScript for Freedom Ticketon Recommendation System

document.addEventListener('DOMContentLoaded', function() {
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            } else {
                // Show loading state
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    const spinner = submitBtn.querySelector('.spinner-border');
                    if (spinner) {
                        spinner.classList.remove('d-none');
                    }
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = 'Processing...';
                }
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // File input validation
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', () => {
            const files = input.files;
            if (files.length) {
                const file = files[0];
                const fileType = file.name.split('.').pop().toLowerCase();
                
                // Check file type
                if (fileType !== 'csv') {
                    input.value = '';
                    alert('Only CSV files are allowed.');
                    return;
                }
                
                // Check file size (max 100MB)
                if (file.size > 100 * 1024 * 1024) {
                    input.value = '';
                    alert('File size should be less than 100MB.');
                    return;
                }
            }
        });
    });
});