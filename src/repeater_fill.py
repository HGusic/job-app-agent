"""Fill repeating work history and education sections."""

import re
from collections.abc import Callable

from playwright.async_api import Locator, Page

from src.experience_mapper import (
    education_entry_value,
    map_education_field,
    map_work_field,
    work_entry_value,
)

Action = dict[str, str]

REPEATER_FIELD_SELECTOR = (
    "input:visible, textarea:visible, select:visible, "
    "[role=combobox]:visible, [aria-haspopup=listbox]:visible"
)

WORK_ADD_KEYWORDS = (
    "add experience",
    "add employment",
    "add work",
    "add job",
    "add another position",
    "add position",
)
EDUCATION_ADD_KEYWORDS = (
    "add education",
    "add school",
    "add degree",
    "add another education",
)


def normalize_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().strip())


def values_match(expected: str, actual: str) -> bool:
    a = normalize_value(expected)
    b = normalize_value(actual)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def entry_already_on_page(
    entry: dict,
    primary_values: list[str],
    secondary_values: list[str],
    primary_key: str,
    secondary_key: str,
) -> bool:
    """True if resume autofill (or a prior pass) already has this entry."""
    primary = str(entry.get(primary_key, "") or "")
    secondary = str(entry.get(secondary_key, "") or "")
    if not primary:
        return False

    for index, on_page_primary in enumerate(primary_values):
        if not values_match(primary, on_page_primary):
            continue
        on_page_secondary = secondary_values[index] if index < len(secondary_values) else ""
        if not secondary or not on_page_secondary or values_match(secondary, on_page_secondary):
            return True
    return False


async def read_button_label(element: Locator) -> str:
    from src.filler import safe_attr

    try:
        text = (await element.inner_text()).strip()
    except Exception:
        text = ""
    if text:
        return text
    aria = await safe_attr(element, "aria-label")
    return (aria or "").strip()


async def click_add_button(page: Page, keywords: tuple[str, ...]) -> bool:
    from src.filler import safe_count

    selectors = ["button:visible", "a:visible", "[role=button]:visible", "input[type=button]:visible"]
    for selector in selectors:
        count = await safe_count(page.locator(selector))
        for i in range(count):
            element = page.locator(selector).nth(i)
            try:
                label = (await read_button_label(element)).lower()
                if any(keyword in label for keyword in keywords):
                    await element.scroll_into_view_if_needed()
                    await element.click()
                    await page.wait_for_timeout(1500)
                    return True
            except Exception:
                continue
    return False


async def read_element_value(element: Locator) -> str:
    from src.filler import safe_count, safe_evaluate

    tag = await safe_evaluate(element, "el => el.tagName.toLowerCase()")
    if not tag:
        return ""
    if tag == "select":
        selected = element.locator("option:checked")
        if await safe_count(selected):
            try:
                return (await selected.first.inner_text()).strip()
            except Exception:
                return ""
        return ""
    try:
        return (await element.input_value()).strip()
    except Exception:
        return ""


async def element_is_empty(element: Locator) -> bool:
    from src.dropdown_fill import is_placeholder_value
    from src.filler import safe_attr

    value = await read_element_value(element)
    input_type = (await safe_attr(element, "type") or "").lower()
    if input_type == "checkbox":
        try:
            return not await element.is_checked()
        except Exception:
            return True
    if is_placeholder_value(value):
        return True
    return not value.strip()


async def page_has_repeater_fields(page: Page, map_func: Callable[[str], str | None]) -> bool:
    from src.filler import accessible_name, safe_count

    count = await safe_count(page.locator(REPEATER_FIELD_SELECTOR))
    for i in range(count):
        element = page.locator(REPEATER_FIELD_SELECTOR).nth(i)
        try:
            if not await safe_count(element):
                continue
            label = await accessible_name(page, element)
            if map_func(label):
                return True
        except Exception:
            continue
    return False


async def get_filled_field_values(
    page: Page,
    map_func: Callable[[str], str | None],
    field_key: str,
) -> list[str]:
    from src.filler import accessible_name, safe_attr, safe_count, safe_evaluate

    values: list[str] = []
    count = await safe_count(page.locator(REPEATER_FIELD_SELECTOR))

    for i in range(count):
        element = page.locator(REPEATER_FIELD_SELECTOR).nth(i)
        try:
            if not await safe_count(element):
                continue

            tag = await safe_evaluate(element, "el => el.tagName.toLowerCase()")
            if not tag:
                continue
            input_type = (await safe_attr(element, "type") or "").lower()
            if tag != "select" and input_type in {"hidden", "submit", "button", "radio", "file", "checkbox"}:
                continue

            label = await accessible_name(page, element)
            key = map_func(label)
            if key != field_key:
                continue

            value = await read_element_value(element)
            if value.strip():
                values.append(value.strip())
        except Exception:
            continue

    return values


async def fill_field_element(
    page: Page,
    element: Locator,
    key: str,
    value: str,
    entry: dict | None = None,
) -> str:
    from src.dropdown_fill import fill_dropdown_field
    from src.filler import fill_text_field, safe_attr, safe_evaluate

    tag = await safe_evaluate(element, "el => el.tagName.toLowerCase()")
    role = await safe_attr(element, "role")
    haspopup = await safe_attr(element, "aria-haspopup")

    is_dropdown = (
        tag == "select"
        or role == "combobox"
        or haspopup in {"listbox", "menu"}
        or key in {"degree", "specialization", "field_of_study"}
    )

    if is_dropdown:
        return await fill_dropdown_field(page, element, key, value, entry=entry)

    return await fill_text_field(page, element, str(value))


async def fill_entry_fields(
    page: Page,
    entry: dict,
    map_func: Callable[[str], str | None],
    value_func: Callable[[dict, str], str | bool],
    section: str,
    entry_index: int,
) -> tuple[list[Action], list[Action]]:
    from collections import defaultdict

    from src.filler import accessible_name, safe_attr, safe_count, safe_evaluate

    filled: list[Action] = []
    skipped: list[Action] = []
    key_occurrence: dict[str, int] = defaultdict(int)

    count = await safe_count(page.locator(REPEATER_FIELD_SELECTOR))

    for i in range(count):
        element = page.locator(REPEATER_FIELD_SELECTOR).nth(i)
        try:
            if not await safe_count(element):
                continue

            tag = await safe_evaluate(element, "el => el.tagName.toLowerCase()")
            if not tag:
                continue
            input_type = (await safe_attr(element, "type") or "").lower()
            if tag != "select" and input_type in {"hidden", "submit", "button", "radio", "file"}:
                continue

            label = await accessible_name(page, element)
            key = map_func(label)
            if not key:
                continue

            occurrence = key_occurrence[key]
            key_occurrence[key] += 1

            # Fill only the Nth block — entry 0 → 0th degree field, entry 1 → 1st degree field.
            if occurrence != entry_index:
                continue

            value = value_func(entry, key)
            if key != "current" and (value is None or value == "" or value is False):
                continue

            if key != "current":
                current = await read_element_value(element)
                if current.strip() and values_match(str(value), current):
                    continue

            field_key = f"{section}[{entry_index}].{key}"
            if key == "current":
                if value:
                    await element.check()
                    filled.append({"label": label, "key": field_key, "value": "checked"})
                else:
                    await element.uncheck()
                    filled.append({"label": label, "key": field_key, "value": "unchecked"})
            else:
                filled_value = await fill_field_element(page, element, key, str(value), entry=entry)
                filled.append({"label": label, "key": field_key, "value": filled_value})
        except Exception as exc:
            skipped.append(
                {
                    "label": f"{section}[{entry_index}]",
                    "key": f"{section}[{entry_index}]",
                    "error": str(exc),
                }
            )

    return filled, skipped


async def fill_repeater_section(
    page: Page,
    profile: dict,
    section: str,
    map_func: Callable[[str], str | None],
    value_func: Callable[[dict, str], str | bool],
    add_keywords: tuple[str, ...],
    primary_key: str,
    secondary_key: str,
) -> tuple[list[Action], list[Action]]:
    entries = profile.get(section, [])
    if not entries:
        return [], []

    if not await page_has_repeater_fields(page, map_func):
        return [], []

    filled: list[Action] = []
    skipped: list[Action] = []

    for index, entry in enumerate(entries):
        primary_values = await get_filled_field_values(page, map_func, primary_key)
        secondary_values = await get_filled_field_values(page, map_func, secondary_key)

        if entry_already_on_page(entry, primary_values, secondary_values, primary_key, secondary_key):
            label = f"{entry.get(primary_key, '')} / {entry.get(secondary_key, '')}".strip(" /")
            filled.append(
                {
                    "label": label,
                    "key": f"{section}[{index}]",
                    "value": "skipped — already on page",
                }
            )
            continue

        blocks_on_page = len(primary_values)

        if blocks_on_page > index:
            part_filled, part_skipped = await fill_entry_fields(
                page, entry, map_func, value_func, section, index
            )
            filled.extend(part_filled)
            skipped.extend(part_skipped)
            continue

        if blocks_on_page == index:
            if index > 0:
                added = await click_add_button(page, add_keywords)
                if not added:
                    skipped.append(
                        {
                            "label": section,
                            "key": section,
                            "error": f"could not find Add button for entry {index + 1}",
                        }
                    )
                    break

            part_filled, part_skipped = await fill_entry_fields(
                page, entry, map_func, value_func, section, index
            )
            filled.extend(part_filled)
            skipped.extend(part_skipped)

    return filled, skipped


async def fill_work_history(page: Page, profile: dict) -> tuple[list[Action], list[Action]]:
    return await fill_repeater_section(
        page,
        profile,
        "work_history",
        map_work_field,
        work_entry_value,
        WORK_ADD_KEYWORDS,
        primary_key="company",
        secondary_key="title",
    )


async def fill_education(page: Page, profile: dict) -> tuple[list[Action], list[Action]]:
    return await fill_repeater_section(
        page,
        profile,
        "education",
        map_education_field,
        education_entry_value,
        EDUCATION_ADD_KEYWORDS,
        primary_key="school",
        secondary_key="degree",
    )
