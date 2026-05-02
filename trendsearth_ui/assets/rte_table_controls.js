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
// Mantine RTE renders a <textarea> inside the editor container when source
// mode is active. We watch for that textarea being added and format its content.
(function () {
    const VOID_TAGS = /^(area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)$/i;

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

    function formatTextarea(textarea) {
        if (!textarea || !textarea.value.trim()) return;
        const formatted = prettyPrintHtml(textarea.value);
        if (formatted === textarea.value) return;

        // Update value in a way that React's synthetic event system picks up
        const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value'
        ).set;
        nativeSetter.call(textarea, formatted);
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    }

    new MutationObserver(function (mutations) {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType !== 1) continue;

                const candidates = node.tagName === 'TEXTAREA'
                    ? [node]
                    : Array.from(node.querySelectorAll ? node.querySelectorAll('textarea') : []);

                for (const ta of candidates) {
                    if (ta.closest('[class*="RichTextEditor"]')) {
                        // Small delay to let Mantine finish populating the textarea
                        setTimeout(() => formatTextarea(ta), 0);
                    }
                }
            }
        }
    }).observe(document.body, { childList: true, subtree: true });
}());
