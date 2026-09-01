"""Robust dropdown filling for native <select> and custom combobox widgets."""

from playwright.async_api import Locator, Page

from src.select_match import fill_candidates, pick_option, pick_option_for_degree, text_matches_any, yes_no_candidates

PLACEHOLDER_LABELS = {
    "",
    "please select",
    "select",
    "select...",
    "choose",
    "choose one",
    "select one",
    "--",
    "-",
}


def is_placeholder_value(value: str) -> bool:
    return value.strip().casefold() in PLACEHOLDER_LABELS


def candidates_for_field(key: str, value: str, entry: dict | None = None) -> list[str]:
    """Build ordered candidate list for a dropdown field."""
    seen: set[str] = set()
    ordered: list[str] = []

    def add(*items: str) -> None:
        for item in items:
            if item and item.casefold() not in seen:
                seen.add(item.casefold())
                ordered.append(item)

    add(value)
    if str(value).casefold() in {"yes", "no", "true", "false"}:
        add(*yes_no_candidates(str(value)))
    add(*fill_candidates(key, value))

    if key in {"specialization", "field_of_study"} and entry:
        degree = str(entry.get("degree", "") or "")
        if "computer science" in degree.casefold():
            add("Computer Science", "CS", "Computer Science and Engineering")
        if entry.get("specialization"):
            add(*fill_candidates("specialization", str(entry["specialization"])))

    return ordered


async def read_select_options(element: Locator) -> list[tuple[str, str]]:
    options = await element.locator("option").all()
    result: list[tuple[str, str]] = []
    for option in options:
        value = (await option.get_attribute("value") or "").strip()
        text = (await option.inner_text()).strip()
        result.append((value, text))
    return result


async def pick_from_visible_options(
    page: Page,
    candidates: list[str],
    key: str = "",
    profile_value: str = "",
) -> str | None:
    option_locator = page.locator(
        "[role=listbox]:visible [role=option], "
        "[role=menu]:visible [role=menuitem], "
        "[role=listbox]:visible li:visible, "
        ".dropdown-menu:visible li:visible, "
        ".dropdown-menu:visible a:visible, "
        "ul[role='listbox'] li:visible"
    )
    count = await option_locator.count()
    options: list[tuple[Locator, str]] = []
    for i in range(count):
        option = option_locator.nth(i)
        option_text = (await option.inner_text()).strip()
        if is_placeholder_value(option_text):
            continue
        options.append((option, option_text))

    if key == "degree" and profile_value:
        value_cf = profile_value.casefold()
        is_bachelor = "bachelor" in value_cf or "b.s" in value_cf
        is_master = "master" in value_cf or "m.s" in value_cf
        if is_bachelor:
            options = [(opt, text) for opt, text in options if "bachelor" in text.casefold()]
        elif is_master:
            options = [(opt, text) for opt, text in options if "master" in text.casefold()]

    for option, option_text in options:
        if text_matches_any(option_text, candidates):
            await option.click()
            return option_text
    return None


async def fill_native_select(element: Locator, candidates: list[str], key: str = "", profile_value: str = "") -> str:
    options = await read_select_options(element)
    usable = [
        (v, t)
        for v, t in options
        if not is_placeholder_value(t) and not is_placeholder_value(v)
    ]
    if key == "degree" and profile_value:
        match = pick_option_for_degree(usable, candidates, profile_value)
    else:
        match = pick_option(usable, candidates)
    if not match:
        sample = [t for _, t in usable[:8]]
        raise ValueError(f"no matching option; tried {candidates}; options: {sample}")

    option_value, option_text = match
    if option_value:
        await element.select_option(value=option_value)
    else:
        await element.select_option(label=option_text)
    return option_text or option_value


async def fill_custom_dropdown(
    page: Page,
    element: Locator,
    candidates: list[str],
    key: str = "",
    profile_value: str = "",
) -> str:
    await element.scroll_into_view_if_needed()
    await element.click()
    await page.wait_for_timeout(400)

    picked = await pick_from_visible_options(page, candidates, key=key, profile_value=profile_value)
    if picked:
        return picked

    # Typeahead: type the first candidate into focused input
    for candidate in candidates:
        try:
            await element.fill(candidate)
            await page.wait_for_timeout(400)
            picked = await pick_from_visible_options(page, candidates, key=key, profile_value=profile_value)
            if picked:
                return picked
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(100)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(200)
            current = await element.input_value() if await element.evaluate("el => 'value' in el") else ""
            if current.strip():
                return current.strip()
        except Exception:
            continue

    await page.keyboard.press("Escape")
    raise ValueError(f"no custom dropdown option matched; tried {candidates}")


async def fill_dropdown_field(
    page: Page,
    element: Locator,
    key: str,
    value: str,
    entry: dict | None = None,
) -> str:
    from src.filler import fill_text_field

    candidates = candidates_for_field(key, value, entry=entry)
    tag = await element.evaluate("el => el.tagName.toLowerCase()")

    if tag == "select":
        return await fill_native_select(element, candidates, key=key, profile_value=value)

    role = await element.get_attribute("role")
    haspopup = await element.get_attribute("aria-haspopup")
    input_type = (await element.get_attribute("type") or "").lower()

    if role == "combobox" or haspopup in {"listbox", "menu"} or input_type in {"text", "search"}:
        try:
            return await fill_custom_dropdown(page, element, candidates, key=key, profile_value=value)
        except Exception:
            # Some widgets are plain text autocompletes
            for candidate in candidates:
                try:
                    await fill_text_field(page, element, candidate)
                    return candidate
                except Exception:
                    continue
            raise

    # Hidden select's visible button — look for a select in the same container
    parent = element.locator(
        "xpath=ancestor::*[contains(@class,'form-group') or contains(@class,'field') "
        "or contains(@class,'input')][1]"
    )
    if await parent.count():
        select = parent.locator("select").first
        if await select.count():
            return await fill_native_select(select, candidates, key=key, profile_value=value)

    return await fill_text_field(page, element, str(candidates[0]))
