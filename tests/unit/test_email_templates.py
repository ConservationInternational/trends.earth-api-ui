from trendsearth_ui.email_templates import _format_text_field, render_news


def test_news_highlight_renders_markdown_mailto_link():
    html = render_news(
        highlight_body="Contact [our team](mailto:team@example.com?subject=Hello%20there).",
    )

    assert (
        '<a href="mailto:team@example.com?subject=Hello%20there" '
        'target="_blank" rel="noopener noreferrer" '
        'style="color:#ffffff; text-decoration:underline;">our team</a>'
    ) in html
    assert "[our team](mailto:" not in html


def test_markdown_mailto_and_web_links_do_not_enable_other_schemes():
    text = "[Email](mailto:team@example.com) [Site](https://example.com) [Unsafe](javascript:alert)"

    result = _format_text_field(text)

    assert 'href="mailto:team@example.com"' in result
    assert 'href="https://example.com"' in result
    assert "[Unsafe](javascript:alert)" in result
    assert result.count("<a ") == 2
