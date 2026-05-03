"""Email templates for the Trends.Earth bulk email composer.

Each template provides a subject line and full HTML body using table-based
layout for maximum email client compatibility.  The HTML contains the
SparkPost substitution variables ``{{name}}``, ``{{email}}``, and the
raw-HTML variable ``{{{unsubscribe_footer}}}`` which is automatically
injected by the API at send time.
"""

# ---------------------------------------------------------------------------
# Shared branding constants
# ---------------------------------------------------------------------------

_LOGO_URL = (
    "https://s3.dualstack.us-east-1.amazonaws.com/trends.earth/sharing/logos/"
    "trends_earth_logo_print_colored.png"
)
_PRIMARY_GREEN = "#3a7d44"
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
           style="color:{_PRIMARY_GREEN}; text-decoration:none;">trends.earth</a>
        &nbsp;&bull;&nbsp;
        <a href="{_PRIVACY_URL}" target="_blank"
           style="color:{_PRIMARY_GREEN}; text-decoration:none;">Privacy Policy</a>
        &nbsp;&bull;&nbsp;
        <a href="{_TERMS_URL}" target="_blank"
           style="color:{_PRIMARY_GREEN}; text-decoration:none;">Terms of Use</a>
        <br><br>
        {{{{unsubscribe_footer}}}}
      </td>
    </tr>
  </table>
"""

# ---------------------------------------------------------------------------
# Template: News and updates
# ---------------------------------------------------------------------------

_NEWS_HTML = f"""<!DOCTYPE html>
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
                [Month Year]
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 16px 0;">
                Dear {{{{name}}}},
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 24px 0;">
                Here is the latest news from the Trends.Earth community.
              </p>

              <!-- Section: Highlight -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background-color:{_PRIMARY_GREEN}; border-radius:4px;
                            margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <h2 style="font-family:Arial,sans-serif; font-size:17px;
                                color:#ffffff; font-weight:700; margin:0 0 8px 0;">
                      Highlight
                    </h2>
                    <p style="font-family:Arial,sans-serif; font-size:14px;
                               color:#f8f9fa; line-height:1.6; margin:0;">
                      [Add your main highlight here.]
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Section: News items -->
              <h2 style="font-family:Arial,sans-serif; font-size:17px; color:#212529;
                          font-weight:700; margin:0 0 12px 0; border-bottom:2px solid {_PRIMARY_GREEN};
                          padding-bottom:8px;">
                Latest News
              </h2>

              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:20px;">
                <tr>
                  <td style="padding:12px 0; border-bottom:1px solid #dee2e6;">
                    <h3 style="font-family:Arial,sans-serif; font-size:15px; color:#212529;
                                font-weight:700; margin:0 0 6px 0;">
                      [News Item Title]
                    </h3>
                    <p style="font-family:Arial,sans-serif; font-size:14px; color:#495057;
                               line-height:1.6; margin:0 0 8px 0;">
                      [Summary of news item. Replace with your content.]
                    </p>
                    <a href="{_WEBSITE_URL}" target="_blank"
                       style="font-family:Arial,sans-serif; font-size:14px;
                              color:{_PRIMARY_GREEN}; text-decoration:none; font-weight:600;">
                      Read more &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Call to action -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-top:24px; margin-bottom:8px;">
                <tr>
                  <td align="center">
                    <a href="{_WEBSITE_URL}" target="_blank"
                       style="display:inline-block; background-color:{_PRIMARY_GREEN};
                              color:#ffffff; font-family:Arial,sans-serif; font-size:15px;
                              font-weight:700; text-decoration:none; padding:12px 28px;
                              border-radius:4px;">
                      Visit Trends.Earth
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

_ENGAGEMENT_HTML = f"""<!DOCTYPE html>
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
                As a valued member of the Trends.Earth community, your feedback helps
                us improve the tools and resources we provide to land degradation
                researchers and practitioners worldwide.
              </p>

              <!-- Engagement block -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background-color:#f0f7f1; border-left:4px solid {_PRIMARY_GREEN};
                            border-radius:0 4px 4px 0; margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <h2 style="font-family:Arial,sans-serif; font-size:16px;
                                color:#212529; font-weight:700; margin:0 0 8px 0;">
                      [Survey / Feedback Topic]
                    </h2>
                    <p style="font-family:Arial,sans-serif; font-size:14px;
                               color:#495057; line-height:1.6; margin:0 0 16px 0;">
                      [Describe what you want users to do or share. Keep it brief
                       and actionable.]
                    </p>
                    <a href="#" target="_blank"
                       style="display:inline-block; background-color:{_PRIMARY_GREEN};
                              color:#ffffff; font-family:Arial,sans-serif; font-size:14px;
                              font-weight:700; text-decoration:none; padding:10px 22px;
                              border-radius:4px;">
                      [Action Button Label]
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

_SYSTEM_UPDATE_HTML = f"""<!DOCTYPE html>
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
                [Date &amp; Time]
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 16px 0;">
                Dear {{{{name}}}},
              </p>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 24px 0;">
                We want to let you know about an upcoming change to the Trends.Earth
                platform.
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
                          [YYYY-MM-DD HH:MM UTC]
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
                          [Estimated duration]
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
                          [Services affected]
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Details -->
              <h2 style="font-family:Arial,sans-serif; font-size:17px; color:#212529;
                          font-weight:700; margin:0 0 12px 0; border-bottom:2px solid {_PRIMARY_GREEN};
                          padding-bottom:8px;">
                What to Expect
              </h2>
              <ul style="font-family:Arial,sans-serif; font-size:14px; color:#495057;
                          line-height:1.8; margin:0 0 24px 0; padding-left:20px;">
                <li>[Impact item 1]</li>
                <li>[Impact item 2]</li>
                <li>All data will remain intact.</li>
              </ul>

              <p style="font-family:Arial,sans-serif; font-size:15px; color:#495057;
                         line-height:1.6; margin:0 0 24px 0;">
                We apologize for any inconvenience. If you have questions, please
                contact us at
                <a href="mailto:trends.earth@conservation.org"
                   style="color:{_PRIMARY_GREEN};">trends.earth@conservation.org</a>.
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
        "subject": "[Trends.Earth] News and updates – [Month Year]",
        "html": _NEWS_HTML,
        "subscription_type": "news",
    },
    "engagement": {
        "label": "User Engagement",
        "subject": "We'd love your input — Trends.Earth Community",
        "html": _ENGAGEMENT_HTML,
        "subscription_type": "engagement",
    },
    "system_update": {
        "label": "System Update / Maintenance",
        "subject": "[Trends.Earth] Scheduled Maintenance Notice",
        "html": _SYSTEM_UPDATE_HTML,
        "subscription_type": "system_updates",
    },
}

#: List of (value, label) pairs suitable for dbc.Select options.
TEMPLATE_OPTIONS = [{"label": v["label"], "value": k} for k, v in TEMPLATES.items()]
