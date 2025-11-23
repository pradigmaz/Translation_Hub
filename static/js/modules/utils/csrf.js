/**
 * CSRF Token для AJAX
 */

window.getCSRFToken = function() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') return decodeURIComponent(value);
    }
    const input = document.querySelector('[name="csrfmiddlewaretoken"]');
    return input ? input.value : null;
};
