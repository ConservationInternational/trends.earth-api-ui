/* Custom RichTextEditor table control functions for bulk email composer.
 * These are referenced by the CustomControl onClick handlers in the toolbar.
 * Each function receives the Tiptap editor instance as its first argument.
 */

function insertTable(editor) {
    editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
}

function addColumnBefore(editor) {
    editor.chain().focus().addColumnBefore().run();
}

function addColumnAfter(editor) {
    editor.chain().focus().addColumnAfter().run();
}

function deleteColumn(editor) {
    editor.chain().focus().deleteColumn().run();
}

function addRowAfter(editor) {
    editor.chain().focus().addRowAfter().run();
}

function deleteRow(editor) {
    editor.chain().focus().deleteRow().run();
}

function deleteTable(editor) {
    editor.chain().focus().deleteTable().run();
}
