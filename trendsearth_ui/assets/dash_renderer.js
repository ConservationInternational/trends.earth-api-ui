(function () {
    if (typeof window === "undefined" || typeof window.DashRenderer !== "function") {
        return;
    }

    var renderer = new window.DashRenderer();
    window.__dash_renderer__ = renderer;
    window._dash_renderer = renderer;
})();
