"""Multi-page form navigation — find and click Next, never Submit."""

import re

from playwright.async_api import Locator, Page

NEXT_KEYWORDS = ("next", "continue", "save and continue", "proceed", "save & continue")
SUBMIT_KEYWORDS = (
    "submit",
    "submit application",
    "apply now",
    "send application",
    "complete application",
    "finish application",
    "review and submit",
)


def button_text(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.lower().strip())


def is_next_label(text: str) -> bool:
    t = button_text(text)
    if not t:
        return False
    if is_submit_label(t):
        return False
    return any(keyword in t for keyword in NEXT_KEYWORDS)


def is_submit_label(text: str) -> bool:
    t = button_text(text)
    return any(keyword in t for keyword in SUBMIT_KEYWORDS)


async def read_button_label(element: Locator) -> str:
    aria = await element.get_attribute("aria-label")
    if aria:
        return aria.strip()

    try:
        text = (await element.inner_text()).strip()
    except Exception:
        text = ""
    if text:
        return text

    value = await element.get_attribute("value")
    return (value or "").strip()


async def is_clickable(element: Locator) -> bool:
    if not await element.is_visible():
        return False
    disabled = await element.get_attribute("disabled")
    if disabled is not None:
        return False
    aria_disabled = await element.get_attribute("aria-disabled")
    if aria_disabled and aria_disabled.lower() == "true":
        return False
    return True


async def log_visible_buttons(page: Page) -> None:
    """Print visible buttons to help debug when Next isn't found."""
    selectors = "button, input[type=submit], input[type=button], [role=button]"
    elements = page.locator(selectors)
    count = await elements.count()
    labels: list[str] = []

    for i in range(count):
        element = elements.nth(i)
        if not await element.is_visible():
            continue
        label = await read_button_label(element)
        if label:
            labels.append(label)

    if labels:
        print("Visible buttons on page:")
        for label in labels[:15]:
            print(f"  - {label!r}")
    else:
        print("No visible buttons found (may need to scroll or form uses custom UI).")


async def find_next_button(page: Page) -> Locator | None:
    """Find a visible Next/Continue button. Never returns Submit."""
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(500)

    # Playwright role/text shortcuts (works well on Phenom/Toyota)
    quick_selectors = [
        page.get_by_role("button", name=re.compile(r"next", re.I)),
        page.get_by_role("button", name=re.compile(r"continue", re.I)),
        page.get_by_role("button", name=re.compile(r"save and continue", re.I)),
        page.locator('button:visible:has-text("Next")'),
        page.locator('button:visible:has-text("Continue")'),
        page.locator('a:visible:has-text("Next")'),
    ]

    for locator in quick_selectors:
        if await locator.count():
            element = locator.first
            label = await read_button_label(element)
            if is_next_label(label) and await is_clickable(element):
                return element

    selectors = [
        "button:visible",
        "input[type=submit]:visible",
        "input[type=button]:visible",
        "a:visible",
        "[role=button]:visible",
    ]

    for selector in selectors:
        elements = page.locator(selector)
        count = await elements.count()
        for i in range(count):
            element = elements.nth(i)
            if not await is_clickable(element):
                continue
            label = await read_button_label(element)
            if is_next_label(label):
                return element

    return None


async def click_next(page: Page, button: Locator) -> bool:
    """Click Next and wait for the next page to load. Returns False if navigation stalls."""
    label = await read_button_label(button)
    if is_submit_label(label):
        return False

    old_url = page.url
    await button.scroll_into_view_if_needed()
    await button.click()

    for _ in range(30):
        await page.wait_for_timeout(500)
        if page.url != old_url:
            break
    else:
        await page.wait_for_timeout(2000)

    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(1500)
    return True
