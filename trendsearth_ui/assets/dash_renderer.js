(function () {
    if (typeof window === "undefined" || typeof window.DashRenderer !== "function") {
        return;
    }

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

    var nonce = getNonce();

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

    if (nonce) {
        window.__dash_csp_nonce__ = nonce;
        if (typeof document !== "undefined") {
            var existingScripts = document.querySelectorAll('script:not([nonce])');
            existingScripts.forEach(ensureNonce);
        }
    }

    var renderer = new window.DashRenderer();
    window.__dash_renderer__ = renderer;
    window._dash_renderer = renderer;
})();
