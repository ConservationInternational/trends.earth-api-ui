(function () {
    if (typeof document === "undefined") {
        return;
    }

    var nonce = null;

    var getNonce = function () {
        if (nonce) {
            return nonce;
        }

        var body = document.body;
        if (body && body.getAttribute("data-csp-nonce")) {
            nonce = body.getAttribute("data-csp-nonce");
            return nonce;
        }

        var meta = document.querySelector('meta[name="dash-csp-nonce"]');
        if (meta && meta.getAttribute("content")) {
            nonce = meta.getAttribute("content");
        }

        return nonce;
    };

    var ensureNonce = function (element) {
        if (!element || !element.tagName || element.nonce) {
            return;
        }

        if (element.tagName.toUpperCase() !== "SCRIPT") {
            return;
        }

        var currentNonce = getNonce();
        if (!currentNonce) {
            return;
        }

        element.setAttribute("nonce", currentNonce);
    };

    nonce = getNonce();
    if (!nonce) {
        return;
    }

    window.__dash_csp_nonce__ = nonce;

    document.querySelectorAll('script:not([nonce])').forEach(ensureNonce);

    var originalCreateElement = Document.prototype.createElement;
    if (!originalCreateElement.__cspNonceWrapped) {
        Document.prototype.createElement = function () {
            var el = originalCreateElement.apply(this, arguments);
            ensureNonce(el);
            return el;
        };
        Document.prototype.createElement.__cspNonceWrapped = true;
    }

    var originalAppendChild = Node.prototype.appendChild;
    if (!originalAppendChild.__cspNonceWrapped) {
        Node.prototype.appendChild = function (child) {
            ensureNonce(child);
            return originalAppendChild.call(this, child);
        };
        Node.prototype.appendChild.__cspNonceWrapped = true;
    }

    var observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            mutation.addedNodes.forEach(function (node) {
                if (!node || node.nodeType !== 1) {
                    return;
                }

                ensureNonce(node);

                if (typeof node.querySelectorAll === "function") {
                    node.querySelectorAll('script:not([nonce])').forEach(ensureNonce);
                }
            });
        });
    });

    observer.observe(document.documentElement, { childList: true, subtree: true });
})();
