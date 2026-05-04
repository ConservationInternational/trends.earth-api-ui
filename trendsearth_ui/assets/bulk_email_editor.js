/**
 * Monaco Editor integration for the bulk-email raw-HTML editor.
 *
 * Monaco is the engine that powers VS Code — actively maintained by Microsoft.
 *
 * WHY DYNAMIC LOADING:
 *   Monaco's loader.js installs a global AMD `define()` at page load. Dash
 *   component libraries (dash-mantine-components, react-leaflet) are UMD
 *   bundles: they check `typeof define === 'function' && define.amd` and try
 *   to register themselves anonymously. Monaco's loader rejects more than one
 *   anonymous define per script, causing:
 *     "Can only have one anonymous define call per script file"
 *   and the entire app crashes.
 *
 *   Fix: inject loader.js as a <script> tag only when the Raw HTML tab opens,
 *   AFTER all Dash component suites have already run. No AMD conflict is
 *   possible because those bundles have already executed their UMD factories
 *   via the non-AMD (global object) path by then.
 *
 * Strategy:
 *  - A MutationObserver watches for #bulk-email-cm-container to enter the DOM.
 *    Dash renders tab panels lazily, so the div doesn't exist until the
 *    "Raw HTML" tab is first opened.
 *  - On detection, loader.js is injected once, then Monaco is initialised.
 *  - CM→Dash: every model change fires a synthetic React "input" event on the
 *    hidden #bulk-email-html-source <textarea>, keeping Dash callbacks in sync.
 *  - Dash→Monaco: a Dash clientside_callback calls window._bulkEmailEditor
 *    .setValue() when Python sets the textarea value.
 *  - Format: the "Format HTML" button's clientside callback calls Monaco's
 *    built-in editor.action.formatDocument.
 */

(function () {
    "use strict";

    var CONTAINER_ID = "bulk-email-cm-container";
    var TEXTAREA_ID = "bulk-email-html-source";
    var MONACO_VS = "https://cdn.jsdelivr.net/npm/monaco-editor@0.55.1/min/vs";

    // Monaco language workers are blob: URLs; MonacoEnvironment must be set
    // before require(['vs/editor/editor.main']) runs.
    window.MonacoEnvironment = {
        getWorkerUrl: function (moduleId, label) {
            var workerPath;
            if (label === "html" || label === "handlebars" || label === "razor") {
                workerPath = MONACO_VS + "/language/html/html.worker.min.js";
            } else if (label === "css" || label === "scss" || label === "less") {
                workerPath = MONACO_VS + "/language/css/css.worker.min.js";
            } else if (label === "json") {
                workerPath = MONACO_VS + "/language/json/json.worker.min.js";
            } else if (label === "javascript" || label === "typescript") {
                workerPath = MONACO_VS + "/language/typescript/ts.worker.min.js";
            } else {
                workerPath = MONACO_VS + "/base/worker/workerMain.min.js";
            }
            return "data:text/javascript;charset=utf-8," + encodeURIComponent(
                "self.MonacoEnvironment={baseUrl:'" + MONACO_VS + "/'};" +
                "importScripts('" + workerPath + "');"
            );
        }
    };

    // Obtain React's internal textarea value setter so synthetic events
    // propagate correctly through React's controlled-component machinery.
    var nativeTextAreaSetter = Object.getOwnPropertyDescriptor
        ? Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")
        : null;

    function triggerReactChange(textarea, newValue) {
        if (!textarea) return;
        if (nativeTextAreaSetter && nativeTextAreaSetter.set) {
            nativeTextAreaSetter.set.call(textarea, newValue);
        } else {
            textarea.value = newValue;
        }
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
        textarea.dispatchEvent(new Event("change", { bubbles: true }));
    }

    /**
     * Inject loader.js once, then hand the scoped require to callback.
     * Saves Monaco's require as window._monacoRequire so subsequent calls
     * skip the script injection.
     */
    function loadMonacoLoader(callback) {
        if (window._monacoRequire) {
            callback(window._monacoRequire);
            return;
        }
        var script = document.createElement("script");
        script.src = MONACO_VS + "/loader.js";
        script.onload = function () {
            var monacoRequire = window.require;
            window._monacoRequire = monacoRequire;
            monacoRequire.config({ paths: { vs: MONACO_VS } });
            callback(monacoRequire);
        };
        document.head.appendChild(script);
    }

    function initMonaco(container) {
        if (window._bulkEmailEditor) {
            try { window._bulkEmailEditor.dispose(); } catch (_) {}
            window._bulkEmailEditor = null;
        }

        var textarea = document.getElementById(TEXTAREA_ID);
        var initialValue = textarea ? (textarea.value || "") : "";

        loadMonacoLoader(function (monacoRequire) {
            monacoRequire(["vs/editor/editor.main"], function () {
                var editor = monaco.editor.create(container, {
                    value: initialValue,
                    language: "html",
                    theme: "vs",
                    minimap: { enabled: false },
                    wordWrap: "on",
                    automaticLayout: true,
                    scrollBeyondLastLine: false,
                    fontSize: 13,
                    tabSize: 2,
                    insertSpaces: true,
                    formatOnPaste: true,
                });

                // Monaco → Dash: debounced sync on every content change.
                var syncTimer = null;
                editor.onDidChangeModelContent(function () {
                    clearTimeout(syncTimer);
                    syncTimer = setTimeout(function () {
                        var ta = document.getElementById(TEXTAREA_ID);
                        triggerReactChange(ta, editor.getValue());
                    }, 150);
                });

                window._bulkEmailEditor = editor;
            });
        });
    }

    function observeForContainer() {
        var observer = new MutationObserver(function (mutations) {
            for (var i = 0; i < mutations.length; i++) {
                var added = mutations[i].addedNodes;
                for (var j = 0; j < added.length; j++) {
                    var node = added[j];
                    if (!node.querySelector) continue;
                    var target = (node.id === CONTAINER_ID)
                        ? node
                        : node.querySelector("#" + CONTAINER_ID);
                    if (target && !window._bulkEmailEditor) {
                        setTimeout(function (el) {
                            return function () { initMonaco(el); };
                        }(target), 50);
                    }
                }
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });

        // Handle case where tab is already active on page load.
        var existing = document.getElementById(CONTAINER_ID);
        if (existing) {
            setTimeout(function () { initMonaco(existing); }, 50);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", observeForContainer);
    } else {
        observeForContainer();
    }
})();
