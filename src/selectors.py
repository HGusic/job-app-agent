"""Safe CSS selectors for element ids with special characters (e.g. brackets)."""

from playwright.async_api import Locator, Page


def css_escape_attr(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def locator_by_id(page: Page, elem_id: str) -> Locator:
    return page.locator(f'[id="{css_escape_attr(elem_id)}"]')


def locator_label_for(page: Page, elem_id: str) -> Locator:
    return page.locator(f'label[for="{css_escape_attr(elem_id)}"]')
