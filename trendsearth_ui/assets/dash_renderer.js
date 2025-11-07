(function () {
    if (typeof window === "undefined") {
        return;
    }

    var setupNonceGuards = function (nonce) {
        var ensureNonce = function (element) {
            if (!nonce || !element || element.nonce) {
                return;
            }

            if (typeof element.tagName !== "string" || element.tagName.toUpperCase() !== "SCRIPT") {
                return;
            }

            element.setAttribute("nonce", nonce);
        };

        if (nonce && typeof Document !== "undefined" && typeof Node !== "undefined") {
            var originalCreateElement = Document.prototype.createElement;
            if (!originalCreateElement.__dashNonceWrapped) {
                Document.prototype.createElement = function () {
                    var el = originalCreateElement.apply(this, arguments);
                    ensureNonce(el);
                    return el;
                };
                Document.prototype.createElement.__dashNonceWrapped = true;
            }

            var originalAppendChild = Node.prototype.appendChild;
            if (!originalAppendChild.__dashNonceWrapped) {
                Node.prototype.appendChild = function (child) {
                    ensureNonce(child);
                    return originalAppendChild.call(this, child);
                };
                Node.prototype.appendChild.__dashNonceWrapped = true;
            }
        }

        if (nonce && typeof document !== "undefined") {
            var existingScripts = document.querySelectorAll('script:not([nonce])');
            existingScripts.forEach(ensureNonce);
        }

        return ensureNonce;
    };

    var getNonce = function () {
        if (typeof document === "undefined") {
            return null;
        }

        var body = document.body;
        if (body && body.getAttribute("data-csp-nonce")) {
            return body.getAttribute("data-csp-nonce");
        }

        var meta = document.querySelector('meta[name="dash-csp-nonce"]');
        if (meta) {
            var value = meta.getAttribute("content");
            if (value) {
                return value;
            }
        }

        return null;
    };

    var initialized = false;

    var initialize = function () {
        if (initialized) {
            return;
        }

        if (typeof window.DashRenderer !== "function") {
            setTimeout(initialize, 0);
            return;
        }

        var nonce = getNonce();
        var ensureNonce = setupNonceGuards(nonce);

        if (nonce) {
            window.__dash_csp_nonce__ = nonce;
        }

        var renderer = new window.DashRenderer();
        window.__dash_renderer__ = renderer;
        window._dash_renderer = renderer;

        if (ensureNonce && typeof document !== "undefined" && typeof MutationObserver !== "undefined") {
            var observer = new MutationObserver(function (records) {
                records.forEach(function (record) {
                    var nodes = record.addedNodes || [];
                    for (var i = 0; i < nodes.length; i += 1) {
                        ensureNonce(nodes[i]);
                    }
                });
            });
            observer.observe(document.documentElement, { childList: true, subtree: true });
        }

        initialized = true;
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize, { once: true });
    } else {
        initialize();
    }
})();
