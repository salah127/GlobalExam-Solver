"""
agent/browser.py
Handles browser lifecycle and login.
Uses JavaScript injection to fill login fields — bypasses any visibility/
clickability issues that break Selenium's send_keys approach.
"""

import random
import time
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import config

logger = logging.getLogger(__name__)

LOGIN_URL = "https://auth.global-exam.com/login"


def build_driver() -> webdriver.Chrome:
    """Create and return a configured Chrome WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument("log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if config.HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options,
    )

    # Hide the navigator.webdriver flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )

    if not config.HEADLESS:
        driver.maximize_window()

    return driver


def _js_fill(driver: webdriver.Chrome, element, value: str) -> None:
    """Fill an input via JavaScript — works regardless of visibility state."""
    driver.execute_script(
        """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input',  {bubbles: true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
        """,
        element,
        value,
    )


def _dismiss_cookie_banner(driver: webdriver.Chrome) -> None:
    """Try to close any cookie/GDPR consent popup (no wait — instant check)."""
    selectors = [
        "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
        "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accepter')]",
        "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree')]",
        "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ok')]",
        "//button[@id='onetrust-accept-btn-handler']",
        "//button[contains(@class,'cookie')]",
    ]
    for xpath in selectors:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            btn.click()
            logger.info("Cookie banner dismissed.")
            time.sleep(0.8)
            return
        except Exception:
            continue
    logger.info("No cookie banner found — skipping.")


def login(driver: webdriver.Chrome, email: str, password: str) -> bool:
    """
    Navigate to the login page and authenticate.
    Returns True on success, False on failure.
    Uses JS injection so the field selector issue never blocks execution.
    """
    logger.info("🌐 Navigating to login page...")
    driver.get(LOGIN_URL)
    time.sleep(random.uniform(2.0, 3.0))

    logger.info("🍪 Checking for cookie/GDPR banner...")
    _dismiss_cookie_banner(driver)

    # Scan all inputs and identify email/password fields via JS
    logger.info("🔍 Scanning page for login fields...")
    all_inputs = driver.find_elements(By.TAG_NAME, "input")

    email_field = None
    password_field = None
    for inp in all_inputs:
        try:
            t = driver.execute_script("return arguments[0].getAttribute('type');", inp) or ""
            n = driver.execute_script("return arguments[0].getAttribute('name');", inp) or ""
            if t == "email" or n == "email":
                email_field = inp
            elif t == "password" or n == "password":
                password_field = inp
        except Exception:
            continue

    if email_field is None:
        logger.error("❌ Email field not found on page!")
        return False
    logger.info("  📧 Email field found")

    if password_field is None:
        logger.error("❌ Password field not found on page!")
        return False
    logger.info("  🔑 Password field found")

    # Fill credentials via JavaScript injection
    logger.info("✏️  Filling credentials...")
    _js_fill(driver, email_field, email)
    time.sleep(random.uniform(0.3, 0.6))
    _js_fill(driver, password_field, password)
    time.sleep(random.uniform(0.3, 0.6))

    # Submit the form
    logger.info("🚀 Submitting login form...")
    submit = _find_submit(driver)
    if submit is None:
        logger.error("❌ Submit button not found!")
        return False
    submit.click()

    # Wait for redirect away from login page
    try:
        WebDriverWait(driver, config.WAIT_TIMEOUT).until(
            EC.url_changes(LOGIN_URL)
        )
        logger.info("✅ LOGIN SUCCESSFUL  →  %s", driver.current_url)
        return True
    except Exception:
        logger.error("❌ Login FAILED — still on: %s", driver.current_url)
        try:
            errors = driver.find_elements(
                By.XPATH,
                "//*[contains(@class,'error') or contains(@class,'alert') or contains(@class,'invalid')]",
            )
            for e in errors[:3]:
                if e.text.strip():
                    logger.error("  ⚠️  Page says: %r", e.text.strip())
        except Exception:
            pass
        return False


def _find_submit(driver: webdriver.Chrome):
    """Try multiple selectors to locate the login submit button."""
    fast_wait = WebDriverWait(driver, 5)
    strategies = [
        (By.XPATH, "//button[@type='submit']"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//form//button[last()]"),
        (By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'connect')]"),
        (By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'login')]"),
        (By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign')]"),
    ]
    for by, selector in strategies:
        try:
            el = fast_wait.until(EC.element_to_be_clickable((by, selector)))
            return el
        except Exception:
            continue
    return None
