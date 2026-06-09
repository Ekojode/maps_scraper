import os
import json
import platform
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

load_dotenv()

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_playwright = None

def launch_browser(use_proxy=None):
    global _playwright
    _playwright = sync_playwright().start()

    if use_proxy is None:
        use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"

    headless = os.getenv("HEADLESS", "false").lower() == "true"
    import platform
    launch_args = ["--disable-http2"]
    if platform.system() == "Linux":
        launch_args += ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    browser = _playwright.chromium.launch(headless=headless, args=launch_args)

    context_args = {
        "viewport": {"width": 1280, "height": 800},
        "locale": "en-US",
        "user_agent": USER_AGENT,
    }

    if use_proxy:
        context_args["proxy"] = {
            "server": f"http://{os.getenv('DECODO_HOST')}:{os.getenv('DECODO_PORT')}",
            "username": os.getenv("DECODO_USER"),
            "password": os.getenv("DECODO_PASS"),
        }

    context = browser.new_context(**context_args)
    # Block known heavyweight resources that carry no scraping value:
    # map tile images, street view pixels, Google Fonts, and static map assets.
    # Blocking by exact URL pattern (not resource_type) avoids accidentally
    # aborting XHR/fetch responses that Google may label as "image" internally.
    context.route(
        "**/maps/vt**",
        lambda route: route.abort()
    )
    context.route(
        "**streetviewpixels**",
        lambda route: route.abort()
    )
    context.route(
        "**fonts.gstatic.com/**",
        lambda route: route.abort()
    )
    context.route(
        "**maps.gstatic.com/mapfiles/**",
        lambda route: route.abort()
    )
    page = context.new_page()
    page.set_default_navigation_timeout(60000)

    Stealth(
        navigator_platform_override="MacIntel",
        navigator_user_agent_override=USER_AGENT,
    ).apply_stealth_sync(page)

    return browser, page


def handle_consent(page):
    """Dismiss Google's cookie consent dialog if it appears."""
    try:
        accept_btn = page.locator("button:has-text('Accept all'), button:has-text('Reject all')").first
        accept_btn.wait_for(timeout=20000)
        accept_btn.click()
        time.sleep(3)
    except Exception:
        pass  # No consent dialog present


def check_ip(page):
    """Return the public IP address the browser is using."""
    page.goto("https://api.ipify.org?format=json", wait_until="domcontentloaded")
    data = json.loads(page.locator("body").inner_text())
    return data["ip"]


def check_proxy_health():
    """
    Launches a temporary browser with proxy and verifies the IP differs
    from the real machine IP. Returns True if proxy is working, False if not.
    """
    import subprocess
    try:
        real_ip = subprocess.check_output(
            ["curl", "-s", "--max-time", "5", "https://api.ipify.org"],
            timeout=10
        ).decode().strip()
    except Exception:
        return True  # Can't get real IP — don't block the run

    browser, page = None, None
    try:
        browser, page = launch_browser(use_proxy=True)
        proxy_ip = check_ip(page)
        return proxy_ip != real_ip
    except Exception:
        return False
    finally:
        if browser:
            close_browser(browser)


def close_browser(browser):
    global _playwright
    browser.close()
    if _playwright:
        _playwright.stop()
        _playwright = None


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)

    real_ip = subprocess.check_output(["curl", "-s", "https://api.ipify.org"]).decode().strip()
    print(f"Real machine IP:  {real_ip}")

    browser, page = launch_browser(use_proxy=True)
    proxy_ip = check_ip(page)
    print(f"Browser proxy IP: {proxy_ip}")

    if proxy_ip == real_ip:
        print("Stage 3 FAILED — proxy IP matches real IP, proxy not working")
        close_browser(browser)
        exit(1)

    screenshot_path = Path("logs/stage3_proxy_test.png")
    page.screenshot(path=str(screenshot_path), timeout=10000)
    close_browser(browser)

    print("Stage 3 passed — proxy working (IP routing confirmed)")
