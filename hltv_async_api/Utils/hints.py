SELENIUM_INSTALL_HINT = (
    "Selenium support is not installed. Run: pip install \"hltv-async-api[selenium]\" "
    "(Google Chrome is required)."
)

LIVE_INSTALL_HINT = (
    "Live match support is not installed. Run: pip install \"hltv-async-api[live]\"."
)

LIVE_BLOCKED_HINT = (
    "The HLTV scorebot socket refused the connection (usually a 403 from Cloudflare). "
    "Create the client with Hltv(selenium=True) and open a page first, so the browser's own cookies and "
    "User-Agent are used, or pass cookies=... copied from your own browser."
)

BLOCKED_HINT = (
    "HLTV answered 403 / Cloudflare challenge, plain HTTP requests are being blocked. \n"
    "Think about using proxy with Hltv(proxy"
    "Install the optional browser driver with: pip install \"hltv-async-api[selenium]\" "
    "and create the client with Hltv(selenium=True)."
)
