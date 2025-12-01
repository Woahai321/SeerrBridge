let isCSPDisabled = false;
let isInitializing = true;
let ignoreNextStorageChange = false;

chrome.storage.sync.get(['disableCSP'], function(result) {
    isCSPDisabled = result.disableCSP || true;
    updateRule().then(() => {
        updateIcon();
        isInitializing = false;
    });
});

chrome.storage.onChanged.addListener(function(changes, namespace) {
    if (isInitializing) {
        return;
    }
    if (ignoreNextStorageChange) {
        ignoreNextStorageChange = false;
        return;
    }
    if (changes.disableCSP) {
        isCSPDisabled = changes.disableCSP.newValue;
        updateRule().then(updateIcon);
    }
});

chrome.action.onClicked.addListener((tab) => {
    isCSPDisabled = !isCSPDisabled;
    ignoreNextStorageChange = true;
    chrome.storage.sync.set({disableCSP: isCSPDisabled}, function() {
        updateRule().then(updateIcon);
    });
});

function updateRule() {
    const ruleId = 1;

    return new Promise((resolve, reject) => {
        chrome.declarativeNetRequest.getDynamicRules(function(rules) {
            const ruleExists = rules.some(rule => rule.id === ruleId);

            if (ruleExists) {
                chrome.declarativeNetRequest.updateDynamicRules({
                    removeRuleIds: [ruleId]
                }, function() {
                    if (chrome.runtime.lastError) {
                        reject(chrome.runtime.lastError);
                    } else {
                        addRuleIfNeeded(resolve, reject);
                    }
                });
            } else {
                addRuleIfNeeded(resolve, reject);
            }
        });
    });
}

function addRuleIfNeeded(resolve, reject) {
    if (isCSPDisabled) {
        const ruleId = 1;
        chrome.declarativeNetRequest.updateDynamicRules({
            addRules: [{
                id: ruleId,
                priority: 1,
                action: {
                    type: "modifyHeaders",
                    responseHeaders: [
                        { header: "content-security-policy", operation: "remove" },
                        { header: "x-content-security-policy", operation: "remove" },
                        { header: "x-webkit-csp", operation: "remove" }
                    ]
                },
                condition: {
                    urlFilter: "*",
                    resourceTypes: ["main_frame", "sub_frame"]
                }
            }]
        }, function() {
            if (chrome.runtime.lastError) {
                reject(chrome.runtime.lastError);
            } else {
                resolve();
            }
        });
    } else {
        resolve();
    }
}

function updateIcon() {
    const iconPath = isCSPDisabled ? 'icons/icon_enabled.png' : 'icons/icon_disabled.png';
    chrome.action.setIcon({ path: iconPath }, function() { });
}
