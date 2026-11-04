SELENIUM_INSTALL_HINT = (
    "Selenium support is not installed. Run: pip install \"hltv-async-api[selenium]\" "
    "(Google Chrome is required)."
)

BLOCKED_HINT = (
    "HLTV answered 403 / Cloudflare challenge, plain HTTP requests are being blocked. "
    "Install the optional browser driver with: pip install \"hltv-async-api[selenium]\" "
    "and create the client with Hltv(selenium=True)."
)
