/* Custom RichTextEditor table control functions for bulk email composer.
 * These are referenced by the CustomControl onClick handlers in the toolbar.
 * DMC's CustomControl looks up onClick functions in window.dashMantineFunctions.
 * DMC passes the Mantine RichTextEditor context object { editor, ... }, so we
 * access ctx.editor to get the underlying Tiptap editor instance.
 */

window.dashMantineFunctions = window.dashMantineFunctions || {};

window.dashMantineFunctions.insertTable = function(ctx) {
    ctx.editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
};

window.dashMantineFunctions.addColumnBefore = function(ctx) {
    ctx.editor.chain().focus().addColumnBefore().run();
};

window.dashMantineFunctions.addColumnAfter = function(ctx) {
    ctx.editor.chain().focus().addColumnAfter().run();
};

window.dashMantineFunctions.deleteColumn = function(ctx) {
    ctx.editor.chain().focus().deleteColumn().run();
};

window.dashMantineFunctions.addRowAfter = function(ctx) {
    ctx.editor.chain().focus().addRowAfter().run();
};

window.dashMantineFunctions.deleteRow = function(ctx) {
    ctx.editor.chain().focus().deleteRow().run();
};

window.dashMantineFunctions.deleteTable = function(ctx) {
    ctx.editor.chain().focus().deleteTable().run();
};

// Pretty-print HTML when the SourceCode toolbar button is toggled on.
// Mantine's RTE does NOT render a real <textarea> element in the DOM.  When
// source-code mode is activated it calls Tiptap's setContent('<textarea>HTML
// </textarea>'), which causes Tiptap/ProseMirror to store the HTML as plain
// text inside the .ProseMirror contenteditable div.
//
// We intercept the button click in capture phase (before React/Mantine):
//  - Switching TO source: after Mantine sets content, pretty-print the HTML
//    text and constrain the editor height so it scrolls instead of resizing.
//  - Switching FROM source: minify the HTML text (strip our pretty-print
//    whitespace) before Mantine reads it via getText(), which prevents the
//    whitespace from leaking into the rendered document.
(function () {
    const VOID_TAGS = /^(area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)$/i;
    const SOURCE_LABEL = 'Switch between text/source code';

    function prettyPrintHtml(html) {
        const tab = '  ';
        let indent = 0;
        const out = [];

        const tokens = html
            .replace(/>\s+</g, '><')   // collapse whitespace between tags
            .replace(/></g, '>\n<')    // one tag per line
            .split('\n');

        for (let token of tokens) {
            token = token.trim();
            if (!token) continue;

            const closeMatch = token.match(/^<\/([a-z][a-z0-9]*)/i);
            const openMatch  = token.match(/^<([a-z][a-z0-9]*)/i);

            if (closeMatch) {
                indent = Math.max(0, indent - 1);
                out.push(tab.repeat(indent) + token);
            } else if (openMatch) {
                out.push(tab.repeat(indent) + token);
                const tag = openMatch[1];
                const isSelfClose = token.endsWith('/>');
                // Indent children unless it's a void element, self-closing, or
                // the opening and closing tags are on the same token (e.g. <p>text</p>)
                if (!VOID_TAGS.test(tag) && !isSelfClose &&
                        !token.match(new RegExp('<\\/' + tag + '>', 'i'))) {
                    indent++;
                }
            } else {
                out.push(tab.repeat(indent) + token);
            }
        }

        return out.join('\n');
    }

    // Collapse pretty-print whitespace to produce minified HTML on one line.
    function minifyHtml(html) {
        return html
            .replace(/[ \t]*\n[ \t]*/g, '')  // strip newlines and their indentation
            .replace(/>\s+</g, '><')           // collapse remaining whitespace between tags
            .trim();
    }

    // Walk up from an element to find the nearest ancestor that contains a
    // .ProseMirror child (i.e. the RTE root wrapper).
    function findRteRoot(startEl) {
        let el = startEl;
        while (el && el !== document.body) {
            if (el.querySelector('.ProseMirror')) return el;
            el = el.parentElement;
        }
        return null;
    }

    // Replace the ProseMirror editor's text content with the given string.
    // ProseMirror monitors input events on the contenteditable div, so
    // selectAll + execCommand('insertText') is the safest way to update it
    // from outside React/Tiptap.
    function setEditorText(pmEl, text) {
        pmEl.focus();
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(pmEl);
        sel.removeAllRanges();
        sel.addRange(range);
        document.execCommand('insertText', false, text);
    }

    // Use event delegation at the document level (capture phase) so we see
    // the click before Mantine's React handler runs.  At the moment the click
    // fires, the button's data-active attribute reflects the CURRENT state:
    //   no data-active  → switching INTO source mode
    //   data-active     → switching OUT OF source mode
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('button[aria-label="' + SOURCE_LABEL + '"]');
        if (!btn) return;

        const rteRoot = findRteRoot(btn);
        if (!rteRoot) return;
        const pmEl = rteRoot.querySelector('.ProseMirror');
        if (!pmEl) return;

        if (!btn.hasAttribute('data-active')) {
            // Switching TO source mode.
            // Capture current height before Mantine changes content so we can
            // constrain the editor to that size (scrollbar instead of resize).
            const capturedHeight = pmEl.offsetHeight;
            setTimeout(function () {
                const raw = pmEl.textContent;
                if (!raw.trim()) return;
                const formatted = prettyPrintHtml(raw.trim());
                if (formatted === raw.trim()) return;

                // Lock the editor height before inserting the taller content.
                pmEl.style.maxHeight = Math.max(100, capturedHeight) + 'px';
                pmEl.style.overflowY = 'auto';

                setEditorText(pmEl, formatted);
            }, 30);
        } else {
            // Switching FROM source mode.
            // Minify the HTML text BEFORE Mantine reads it via getText(), so
            // that the pretty-print whitespace does not leak into the rendered
            // document as extra newlines / blank lines.
            const raw = pmEl.textContent;
            const minified = minifyHtml(raw);
            if (minified !== raw.trim()) {
                setEditorText(pmEl, minified);
            }

            // Remove the scroll/height constraint.
            pmEl.style.maxHeight = '';
            pmEl.style.overflowY = '';
        }
    }, true /* capture */);
}());
