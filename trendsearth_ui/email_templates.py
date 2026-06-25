"""Email templates for the Trends.Earth bulk email composer.

Each template provides a subject line and full HTML body using table-based
layout for maximum email client compatibility.  The HTML contains the
SparkPost substitution variables ``{{name}}``, ``{{email}}``, and the
raw-HTML variable ``{{{unsubscribe_footer}}}`` which is automatically
injected by the API at send time.

Public API
----------
render_news(...)          â€” render the news & updates template
render_engagement(...)    â€” render the user engagement template
render_system_update(...) â€” render the system update / maintenance template

TEMPLATES        â€” dict of template metadata (subject, default html, subscription_type)
TEMPLATE_OPTIONS â€” list of (value, label) pairs for dropdowns
"""

# ---------------------------------------------------------------------------
# Shared branding constants
# ---------------------------------------------------------------------------

_LOGO_URL = (
    "https://s3.dualstack.us-east-1.amazonaws.com/trends.earth/sharing/logos/"
    "trends_earth_logo_print_colored.png"
)
_PRIMARY_RED = "#c8272a"
_HEADER_BG = "#495057"
_WEBSITE_URL = "https://trends.earth"
_PRIVACY_URL = "https://www.conservation.org/policies/privacy"
_TERMS_URL = "https://www.conservation.org/policies/terms-of-use"

# ---------------------------------------------------------------------------
# Shared HTML fragments
# ---------------------------------------------------------------------------

_HEADER_HTML = f"""
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:{_HEADER_BG}; margin-bottom:24px;">
    <tr>
      <td align="center" style="padding:20px 30px;">
        <a href="{_WEBSITE_URL}" target="_blank" style="text-decoration:none;">
          <img src="{_LOGO_URL}" alt="Trends.Earth"
               width="360" style="max-width:100%; height:auto; display:block;">
        </a>
      </td>
    </tr>
  </table>
"""

_FOOTER_HTML = f"""
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="margin-top:32px; border-top:1px solid #dee2e6;">
    <tr>
      <td align="center" style="padding:16px; font-family:Arial,sans-serif;
          font-size:12px; color:#6c757d; line-height:1.6;">
        <a href="{_WEBSITE_URL}" target="_blank"
           style="color:{_PRIMARY_RED}; text-decoration:none;">trends.earth</a>
        &nbsp;&bull;&nbsp;
        <a href="{_PRIVACY_URL}" target="_blank"
           style="color:{_PRIMARY_RED}; text-decoration:none;">Privacy Policy</a>
        &nbsp;&bull;&nbsp;
        <a href="{_TERMS_URL}" target="_blank"
           style="color:{_PRIMARY_RED}; text-decoration:none;">Terms of Use</a>
      </td>
    </tr>
  </table>
"""

# ---------------------------------------------------------------------------
# Default structured content
# ---------------------------------------------------------------------------

_DEFAULT_NEWS_ITEMS = [
    {
        "title": "[News Item Title]",
        "summary": "[Summary of news item. Replace with your content.]",
        "url": _WEBSITE_URL,
        "image_url": "",
        "image_alt": "",
    }
]

_DEFAULT_IMPACT_ITEMS = [
    "[Impact item 1]",
    "[Impact item 2]",
    "All data will remain intact.",
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _news_item_html(item: dict) -> str:
    """Render a single news item row for the HTML table."""
    title = item.get("title") or "[News Item Title]"
    summary = item.get("summary") or "[Summary of news item.]"
    url = item.get("url") or _WEBSITE_URL
    image_url = (item.get("image_url") or "").strip()
    image_alt = (item.get("image_alt") or "").strip()

    img_html = ""
    if image_url:
        img_html = (
            f'<img src="{image_url}" alt="{image_alt}" width="100%"'
            ' style="display:block;max-width:100%;height:auto;margin-bottom:12px;">'
        )

    return (
        "<tr>"
        '<td style="padding:12px 0; border-bottom:1px solid #dee2e6;">'
        + img_html
        + f'<h3 style="font-family:Arial,sans-serif; font-size:15px; color:#212529;'
        f' font-weight:700; margin:0 0 6px 0;">{title}</h3>'
        f'<p style="font-family:Arial,sans-serif; font-size:14px; color:#495057;'
        f' line-height:1.6; margin:0 0 8px 0;">{summary}</p>'
        f'<a href="{url}" target="_blank"'
        f' style="font-family:Arial,sans-serif; font-size:14px; color:{_PRIMARY_RED};'
        f' text-decoration:none; font-weight:600;">Read more &rarr;</a>'
        "</td>"
        "</tr>"
    )


def _impact_item_html(text: str) -> str:
    return f"<li>{text or '[Impact item]'}</li>"


# ---------------------------------------------------------------------------
# Template: News and updates
# ---------------------------------------------------------------------------


def render_news(
    issue_date: str = "[Month Year]",
    intro: str = "Here is the latest news from the Trends.Earth community.",
    highlight_title: str = "Highlight",
    highlight_body: str = "[Add your main highlight here.]",
    highlight_image_url: str | None = None,
    news_items: list | None = None,
    cta_url: str | None = None,
    cta_label: str = "Visit Trends.Earth",
) -> str:
    """Render the News & Updates HTML email template.

    Parameters
    ----------
    issue_date:          e.g. "January 2025"
    intro:               Opening paragraph after "Dear {{name}}"
    highlight_title:     Title inside the red highlight box
    highlight_body:      Body text inside the red highlight box
    highlight_image_url: Optional image URL shown above the highlight text
    news_items:          List of dicts with keys title, summary, url, image_url, image_alt
    cta_url:             Call-to-action button URL
    cta_label:           Call-to-action button label
    """
    if news_items is None:
        news_items = _DEFAULT_NEWS_ITEMS
    if not cta_url:
        cta_url = _WEBSITE_URL

    news_items_html = "\n".join(_news_item_html(item) for item in news_items)

    _highlight_image_html = ""
    if highlight_image_url:
        _highlight_image_html = f"""
                <tr>
                  <td style="padding:0; text-align:center; line-height:0; font-size:0;">
                    <img src="{highlight_image_url}" alt=""
                         style="width:100%; max-width:100%; height:auto; display:block;
                                border-radius:4px 4px 0 0;">
                  </td>
                </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trends.Earth News &amp; Updates</title></head>
<body style="margin:0; padding:0; background-color:#f8f9fa;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f8f9fa;">
    <tr>
      <td align="center" style="padding:24px 16px;">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="background-color:#ffffff; border-radius:4px;
                      box-shadow:0 1px 3px rgba(0,0,0,0.12);">
          <tr><td>
            {_HEADER_HTML}
          </td></tr>
          <tr>
            <td style="padding:0 32px 24px;">
              <h1 style="font-family:Arial,sans-serif; font-size:22px; color:#212529;
                          font-weight:700; margin:0 0 8px 0;">
                Trends.Earth News &amp; Updates
              </h1>
              <p style="font-family:Arial,sans-serif; font-size:15px; color:#6c757d;
                         margin:0 0 24px 0;">
                {issue_date}
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 16px 0;">
                Dear {{{{name}}}},
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 24px 0;">
                {intro}
              </p>

              <!-- Section: Highlight -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background-color:{_PRIMARY_RED}; border-radius:4px;
                            margin-bottom:24px;">{_highlight_image_html}
                <tr>
                  <td style="padding:20px 24px;">
                    <h2 style="font-family:Arial,sans-serif; font-size:17px;
                                color:#ffffff; font-weight:700; margin:0 0 8px 0;">
                      {highlight_title}
                    </h2>
                    <p style="font-family:Arial,sans-serif; font-size:14px;
                               color:#f8f9fa; line-height:1.6; margin:0;">
                      {highlight_body}
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Section: News items -->
              <h2 style="font-family:Arial,sans-serif; font-size:17px; color:#212529;
                          font-weight:700; margin:0 0 12px 0; border-bottom:2px solid {_PRIMARY_RED};
                          padding-bottom:8px;">
                Latest News
              </h2>

              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:20px;">
                {news_items_html}
              </table>

              <!-- Call to action -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-top:24px; margin-bottom:8px;">
                <tr>
                  <td align="center">
                    <a href="{cta_url}" target="_blank"
                       style="display:inline-block; background-color:{_PRIMARY_RED};
                              color:#ffffff; font-family:Arial,sans-serif; font-size:15px;
                              font-weight:700; text-decoration:none; padding:12px 28px;
                              border-radius:4px;">
                      {cta_label}
                    </a>
                  </td>
                </tr>
              </table>

            </td>
          </tr>
          <tr><td style="padding:0 32px;">
            {_FOOTER_HTML}
          </td></tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Template: User Engagement
# ---------------------------------------------------------------------------


def render_engagement(
    intro: str = (
        "As a valued member of the Trends.Earth community, your feedback helps "
        "us improve the tools and resources we provide to land degradation "
        "researchers and practitioners worldwide."
    ),
    topic: str = "[Survey / Feedback Topic]",
    description: str = (
        "[Describe what you want users to do or share. Keep it brief and actionable.]"
    ),
    button_label: str = "[Action Button Label]",
    button_url: str = "#",
) -> str:
    """Render the User Engagement HTML email template."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trends.Earth Community</title></head>
<body style="margin:0; padding:0; background-color:#f8f9fa;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f8f9fa;">
    <tr>
      <td align="center" style="padding:24px 16px;">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="background-color:#ffffff; border-radius:4px;
                      box-shadow:0 1px 3px rgba(0,0,0,0.12);">
          <tr><td>
            {_HEADER_HTML}
          </td></tr>
          <tr>
            <td style="padding:0 32px 24px;">
              <h1 style="font-family:Arial,sans-serif; font-size:22px; color:#212529;
                          font-weight:700; margin:0 0 24px 0;">
                We&rsquo;d love your input
              </h1>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 16px 0;">
                Dear {{{{name}}}},
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 24px 0;">
                {intro}
              </p>

              <!-- Engagement block -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background-color:#fde8e8; border-left:4px solid {_PRIMARY_RED};
                            border-radius:0 4px 4px 0; margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <h2 style="font-family:Arial,sans-serif; font-size:16px;
                                color:#212529; font-weight:700; margin:0 0 8px 0;">
                      {topic}
                    </h2>
                    <p style="font-family:Arial,sans-serif; font-size:14px;
                               color:#495057; line-height:1.6; margin:0 0 16px 0;">
                      {description}
                    </p>
                    <a href="{button_url}" target="_blank"
                       style="display:inline-block; background-color:{_PRIMARY_RED};
                              color:#ffffff; font-family:Arial,sans-serif; font-size:14px;
                              font-weight:700; text-decoration:none; padding:10px 22px;
                              border-radius:4px;">
                      {button_label}
                    </a>
                  </td>
                </tr>
              </table>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 24px 0;">
                Thank you for being part of our community.
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0;">
                The Trends.Earth Team
              </p>

            </td>
          </tr>
          <tr><td style="padding:0 32px;">
            {_FOOTER_HTML}
          </td></tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Template: System Update / Maintenance
# ---------------------------------------------------------------------------


def render_system_update(
    date_time: str = "[Date &amp; Time]",
    intro: str = ("We want to let you know about an upcoming change to the Trends.Earth platform."),
    datetime_utc: str = "[YYYY-MM-DD HH:MM UTC]",
    duration: str = "[Estimated duration]",
    impact: str = "[Services affected]",
    impact_items: list | None = None,
) -> str:
    """Render the System Update / Maintenance HTML email template."""
    if impact_items is None:
        impact_items = _DEFAULT_IMPACT_ITEMS

    impact_items_html = "\n".join(_impact_item_html(item) for item in impact_items)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trends.Earth System Update</title></head>
<body style="margin:0; padding:0; background-color:#f8f9fa;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f8f9fa;">
    <tr>
      <td align="center" style="padding:24px 16px;">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="background-color:#ffffff; border-radius:4px;
                      box-shadow:0 1px 3px rgba(0,0,0,0.12);">
          <tr><td>
            {_HEADER_HTML}
          </td></tr>
          <tr>
            <td style="padding:0 32px 24px;">
              <h1 style="font-family:Arial,sans-serif; font-size:22px; color:#212529;
                          font-weight:700; margin:0 0 8px 0;">
                System Update Notice
              </h1>
              <p style="font-family:Arial,sans-serif; font-size:14px; color:#6c757d;
                         margin:0 0 24px 0;">
                {date_time}
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 16px 0;">
                Dear {{{{name}}}},
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 24px 0;">
                {intro}
              </p>

              <!-- Alert box -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background-color:#fff3cd; border:1px solid #ffc107;
                            border-radius:4px; margin-bottom:24px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <h2 style="font-family:Arial,sans-serif; font-size:16px;
                                color:#664d03; font-weight:700; margin:0 0 8px 0;">
                      &#9888; Scheduled Maintenance
                    </h2>
                    <table width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="font-family:Arial,sans-serif; font-size:14px;
                                   color:#664d03; padding:2px 0;
                                   width:120px; vertical-align:top; font-weight:600;">
                          Date &amp; Time:
                        </td>
                        <td style="font-family:Arial,sans-serif; font-size:14px;
                                   color:#664d03; padding:2px 0;">
                          {datetime_utc}
                        </td>
                      </tr>
                      <tr>
                        <td style="font-family:Arial,sans-serif; font-size:14px;
                                   color:#664d03; padding:2px 0;
                                   width:120px; vertical-align:top; font-weight:600;">
                          Duration:
                        </td>
                        <td style="font-family:Arial,sans-serif; font-size:14px;
                                   color:#664d03; padding:2px 0;">
                          {duration}
                        </td>
                      </tr>
                      <tr>
                        <td style="font-family:Arial,sans-serif; font-size:14px;
                                   color:#664d03; padding:2px 0;
                                   width:120px; vertical-align:top; font-weight:600;">
                          Impact:
                        </td>
                        <td style="font-family:Arial,sans-serif; font-size:14px;
                                   color:#664d03; padding:2px 0;">
                          {impact}
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Details -->
              <h2 style="font-family:Arial,sans-serif; font-size:17px; color:#212529;
                          font-weight:700; margin:0 0 12px 0; border-bottom:2px solid {_PRIMARY_RED};
                          padding-bottom:8px;">
                What to Expect
              </h2>
              <ul style="font-family:Arial,sans-serif; font-size:14px; color:#495057;
                          line-height:1.8; margin:0 0 24px 0; padding-left:20px;">
                {impact_items_html}
              </ul>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 24px 0;">
                We apologize for any inconvenience. If you have questions, please
                contact us at
                <a href="mailto:trends.earth@conservation.org"
                   style="color:{_PRIMARY_RED};">trends.earth@conservation.org</a>.
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0;">
                The Trends.Earth Team
              </p>

            </td>
          </tr>
          <tr><td style="padding:0 32px;">
            {_FOOTER_HTML}
          </td></tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

TEMPLATES = {
    "news": {
        "label": "News and updates",
        "subject": "[Trends.Earth] News and updates — [Month Year]",
        "html": render_news(),
        "subscription_type": "news",
    },
    "engagement": {
        "label": "User Engagement",
        "subject": "We'd love your input - Trends.Earth Community",
        "html": render_engagement(),
        "subscription_type": "engagement",
    },
    "system_update": {
        "label": "System Update / Maintenance",
        "subject": "[Trends.Earth] Scheduled Maintenance Notice",
        "html": render_system_update(),
        "subscription_type": "system_updates",
    },
}

#: List of (value, label) pairs suitable for dbc.Select options.
TEMPLATE_OPTIONS = [{"label": v["label"], "value": k} for k, v in TEMPLATES.items()]
