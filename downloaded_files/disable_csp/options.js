document.addEventListener('DOMContentLoaded', function() {
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(element => {
        const messageKey = element.getAttribute('data-i18n');
        element.textContent = chrome.i18n.getMessage(messageKey);
    });
});
