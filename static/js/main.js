/**
 * Main - Tooltips + Avatar Preview + Auto-close Alerts + Form Validation
 */

document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap tooltips
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });
    
    // Avatar preview (упрощённая версия)
    const avatarInput = document.querySelector('#id_avatar');
    if (avatarInput) {
        avatarInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = e => {
                const img = document.querySelector('#avatar-preview-img');
                const placeholder = document.querySelector('#avatar-placeholder');
                if (img) {
                    img.src = e.target.result;
                    img.style.display = 'block';
                }
                if (placeholder) placeholder.style.display = 'none';
            };
            reader.readAsDataURL(file);
        });
    }
    
    // Auto-close alerts
    document.querySelectorAll('.alert-dismissible').forEach(alert => {
        const delay = parseInt(alert.getAttribute('data-auto-close')) || 10000;
        if (delay > 0) {
            setTimeout(() => {
                const bsAlert = bootstrap.Alert.getInstance(alert);
                if (bsAlert) bsAlert.close();
            }, delay);
        }
    });
    
    // Form validation
    document.querySelectorAll('.needs-validation').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Password match
    const p1 = document.querySelector('input[name="new_password1"]');
    const p2 = document.querySelector('input[name="new_password2"]');
    if (p1 && p2) {
        const check = () => {
            if (p1.value && p2.value) {
                p2.setCustomValidity(p1.value !== p2.value ? 'Пароли не совпадают' : '');
            }
        };
        p1.addEventListener('input', check);
        p2.addEventListener('input', check);
    }
});
