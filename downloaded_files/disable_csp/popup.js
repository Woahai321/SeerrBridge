document.addEventListener('DOMContentLoaded', function() {
    const statusElement = document.getElementById('status');

    chrome.storage.sync.get(['disableCSP'], function(result) {
        if (result.disableCSP) {
            statusElement.textContent = 'Enabled';
            statusElement.classList.add('enabled');
        } else {
            statusElement.textContent = 'Disabled';
            statusElement.classList.add('disabled');
        }
    });
});
