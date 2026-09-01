import asyncio

from playwright.async_api import Locator, Page

from src.mapper import FieldMapping, map_label_to_field, normalize_label, should_skip_field
from src.profile import get_section_value
from src.select_match import fill_candidates, pick_option, text_matches_any, yes_no_candidates
from src.selectors import locator_by_id, locator_label_for

Action = dict[str, str]
FIELD_TIMEOUT_MS = 2_000
REACT_FIELD_TIMEOUT_MS = 10_000
LATE_CONTACT_KEYS = frozenset({
    "email",
    "address_line1",
    "address_line2",
    "city",
    "postal_code",
})
LATE_CONTACT_ORDER = {
    "address_line1": 0,
    "address_line2": 1,
    "city": 2,
    "postal_code": 3,
    "email": 4,
}
TEXT_INPUT_SELECTOR = (
    "input:not([type=radio]):not([type=checkbox]):not([type=hidden]):not([type=submit]):"
    "not([type=button]):not([type=file]):visible, textarea:visible"
)
DROPDOWN_SELECTOR = (
    "select:visible, [role=combobox]:visible, [aria-haspopup=listbox]:visible, "
    "[aria-haspopup=menu]:visible, .select:not(select):visible"
)
EMAIL_INPUT_SELECTOR = (
    "input[type=email]:visible, input[name*='email' i]:visible, "
    "input[id*='email' i]:visible, input[autocomplete='email']:visible"
)


async def safe_attr(element: Locator, name: str) -> str | None:
    try:
        return await element.get_attribute(name, timeout=FIELD_TIMEOUT_MS)
    except Exception:
        return None


async def safe_count(locator: Locator) -> int:
    try:
        return await locator.count()
    except Exception:
        return 0


async def safe_evaluate(element: Locator, expression: str, arg=None):
    try:
        if arg is None:
            return await element.evaluate(expression, timeout=FIELD_TIMEOUT_MS)
        return await element.evaluate(expression, arg, timeout=FIELD_TIMEOUT_MS)
    except Exception:
        return None


def is_weak_label(label: str) -> bool:
    from src.dropdown_fill import is_placeholder_value

    text = label.strip()
    if not text or is_placeholder_value(text):
        return True
    normalized = normalize_label(text)
    if is_placeholder_value(normalized):
        return True
    if len(normalized) < 15 and "?" not in text:
        return True
    return False


async def field_question_label(page: Page, element: Locator) -> str:
    try:
        return await element.evaluate(
            """
            (el) => {
                const container = el.closest(
                    'tr, li, fieldset, [class*="question"], [class*="field"], '
                    + '[class*="form-group"], [class*="form-row"], .row, [data-testid]'
                ) || el.parentElement?.parentElement;
                if (!container) return '';
                const clone = container.cloneNode(true);
                clone.querySelectorAll(
                    'input, select, textarea, button, [role="listbox"], [role="combobox"], '
                    + '[role="button"], svg, img'
                ).forEach((node) => node.remove());
                return (clone.textContent || '').replace(/\\s+/g, ' ').trim();
            }
            """
        )
    except Exception:
        return ""


async def resolve_field_label(page: Page, element: Locator) -> str:
    """Prefer the surrounding question text over control text like 'Please select'."""
    label = await accessible_name(page, element)
    question = await field_question_label(page, element)
    if question and (is_weak_label(label) or len(question) > len(label)):
        return question
    return label


async def accessible_name(page: Page, element: Locator) -> str:
    aria = await safe_attr(element, "aria-label")
    if aria:
        return aria.strip()

    labelledby = await safe_attr(element, "aria-labelledby")
    if labelledby:
        parts: list[str] = []
        for elem_id in labelledby.split():
            part = locator_by_id(page, elem_id)
            if await safe_count(part):
                try:
                    parts.append((await part.first.inner_text(timeout=FIELD_TIMEOUT_MS)).strip())
                except Exception:
                    continue
        if parts:
            return " ".join(parts)

    elem_id = await safe_attr(element, "id")
    if elem_id:
        label = locator_label_for(page, elem_id)
        if await safe_count(label):
            try:
                return (await label.first.inner_text(timeout=FIELD_TIMEOUT_MS)).strip()
            except Exception:
                pass

    parent_label = element.locator("xpath=ancestor::label[1]")
    if await safe_count(parent_label):
        try:
            return (await parent_label.first.inner_text(timeout=FIELD_TIMEOUT_MS)).strip()
        except Exception:
            pass

    field_group = element.locator(
        "xpath=ancestor::*[contains(@class,'form-group') or contains(@class,'field') "
        "or contains(@class,'input') or contains(@class,'question')][1]"
    )
    if await safe_count(field_group):
        group_label = field_group.locator("label").first
        if await safe_count(group_label):
            try:
                return (await group_label.inner_text(timeout=FIELD_TIMEOUT_MS)).strip()
            except Exception:
                pass

    placeholder = await safe_attr(element, "placeholder")
    if placeholder:
        return placeholder.strip()

    name = await safe_attr(element, "name")
    if name:
        return name.strip()

    if elem_id:
        return elem_id

    return ""


def infer_mapping(label: str, input_type: str, elem_id: str, name: str) -> FieldMapping | None:
    mapping = map_label_to_field(label)
    if mapping:
        return mapping

    hints = normalize_label(f"{label} {elem_id} {name}")
    if not hints:
        hints = normalize_label(f"{elem_id} {name}")

    if input_type == "email" or "email" in hints or "e mail" in hints:
        return FieldMapping("contact", "email")
    if input_type == "tel" or ("phone" in hints and "extension" not in hints and "code" not in hints):
        return FieldMapping("contact", "phone")

    return None


async def read_select_options(element: Locator) -> list[tuple[str, str]]:
    options = await element.locator("option").all()
    result: list[tuple[str, str]] = []
    for option in options:
        value = (await option.get_attribute("value") or "").strip()
        text = (await option.inner_text()).strip()
        result.append((value, text))
    return result


async def read_select_display_value(element: Locator) -> str:
    try:
        selected = element.locator("option:checked")
        if await safe_count(selected):
            return (await selected.first.inner_text()).strip()
    except Exception:
        pass
    return ""


async def fill_select_field(element: Locator, mapping: FieldMapping, value: str) -> str:
    options = await read_select_options(element)
    candidates = fill_candidates(mapping.key, value)
    if mapping.section == "screening":
        candidates = yes_no_candidates(value) + candidates

    match = pick_option(options, candidates)
    if not match:
        raise ValueError(
            f"no matching option for {mapping.section}.{mapping.key}={value!r}; "
            f"tried {candidates}; sample options: {options[:5]}"
        )

    option_value, option_text = match
    if option_value:
        await element.select_option(value=option_value)
    else:
        await element.select_option(label=option_text)
    return option_text or option_value


async def set_react_value(element: Locator, value: str) -> None:
    """Set value in a way React/Vue controlled inputs recognize."""
    await element.evaluate(
        """
        (el, value) => {
            el.focus();
            const proto = el.tagName === 'TEXTAREA'
                ? window.HTMLTextAreaElement.prototype
                : window.HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
            const lastValue = el.value;
            if (setter) {
                setter.call(el, value);
            } else {
                el.value = value;
            }
            // React tracks the previous value — reset it so onChange/input fires.
            const tracker = el._valueTracker;
            if (tracker) {
                tracker.setValue(lastValue);
            }
            el.dispatchEvent(new InputEvent('input', {
                bubbles: true,
                cancelable: true,
                inputType: 'insertText',
                data: value,
            }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        value,
    )


async def read_input_value(element: Locator, timeout_ms: int = REACT_FIELD_TIMEOUT_MS) -> str:
    try:
        return (await element.input_value(timeout=timeout_ms)).strip()
    except Exception:
        return ""


async def fill_react_controlled_field(
    page: Page,
    element: Locator,
    value: str,
    timeout_ms: int = REACT_FIELD_TIMEOUT_MS,
) -> None:
    """Fill React controlled inputs — type like a user, wait until value sticks."""
    await element.scroll_into_view_if_needed(timeout=timeout_ms)
    await element.click(timeout=timeout_ms)
    await element.press("ControlOrMeta+a")
    await element.press("Backspace")
    await page.wait_for_timeout(100)
    await element.press_sequentially(value, delay=25)
    await page.wait_for_timeout(150)

    if await read_input_value(element, timeout_ms) != value:
        await set_react_value(element, value)
        await page.wait_for_timeout(150)

    for _ in range(8):
        if await read_input_value(element, timeout_ms) == value:
            await page.wait_for_timeout(200)
            if await read_input_value(element, timeout_ms) == value:
                return
        await element.click(timeout=timeout_ms)
        await element.press("ControlOrMeta+a")
        await element.press("Backspace")
        await element.press_sequentially(value, delay=25)
        await set_react_value(element, value)
        await page.wait_for_timeout(150)

    current = await read_input_value(element, timeout_ms)
    if current != value:
        raise ValueError(f"value did not stick, got {current!r}")


async def fill_text_field(
    page: Page,
    element: Locator,
    value: str,
    timeout_ms: int = REACT_FIELD_TIMEOUT_MS,
) -> str:
    await fill_react_controlled_field(page, element, value, timeout_ms=timeout_ms)
    return value


async def fill_input_or_select(
    page: Page,
    element: Locator,
    mapping: FieldMapping,
    value: str,
) -> str:
    tag = await element.evaluate("el => el.tagName.toLowerCase()")
    if tag == "select":
        return await fill_select_field(element, mapping, value)
    await fill_text_field(page, element, value)
    return value


async def fill_text_and_select_fields(page: Page, profile: dict) -> tuple[list[Action], list[Action]]:
    filled: list[Action] = []
    skipped: list[Action] = []
    count = await safe_count(page.locator(TEXT_INPUT_SELECTOR))

    for i in range(count):
        element = page.locator(TEXT_INPUT_SELECTOR).nth(i)
        try:
            if not await safe_count(element):
                continue

            input_type = (await safe_attr(element, "type") or "").lower()
            role = await safe_attr(element, "role")
            haspopup = await safe_attr(element, "aria-haspopup")
            if role == "combobox" or haspopup in {"listbox", "menu"}:
                continue

            label = await resolve_field_label(page, element)
            skip_reason = should_skip_field(label, profile)
            if skip_reason:
                skipped.append({"label": label, "key": label, "error": skip_reason})
                continue

            from src.experience_mapper import map_education_field, map_work_field

            if map_work_field(label) or map_education_field(label):
                continue

            elem_id = await safe_attr(element, "id") or ""
            name = await safe_attr(element, "name") or ""
            mapping = infer_mapping(label, input_type, elem_id, name)
            if not mapping:
                continue

            # Filled after dropdowns — React forms reset these when country/state changes.
            if mapping.key in LATE_CONTACT_KEYS:
                continue

            value = get_section_value(profile, mapping.section, mapping.key)
            if value is None or value == "":
                continue

            tag = await safe_evaluate(element, "el => el.tagName.toLowerCase()")
            if tag != "select" and mapping.key != "email":
                try:
                    current = await element.input_value(timeout=FIELD_TIMEOUT_MS)
                except Exception:
                    current = ""
                if current.strip() and current.strip().casefold() == str(value).casefold():
                    continue

            key = f"{mapping.section}.{mapping.key}"
            filled_value = await fill_input_or_select(page, element, mapping, str(value))
            filled.append({"label": label, "key": key, "value": filled_value})
        except Exception as exc:
            skipped.append({"label": f"field[{i}]", "key": "?", "error": str(exc)})

    return filled, skipped


async def group_label(page: Page, group: Locator) -> str:
    aria = await group.get_attribute("aria-label")
    if aria:
        return aria.strip()

    labelledby = await group.get_attribute("aria-labelledby")
    if labelledby:
        parts: list[str] = []
        for elem_id in labelledby.split():
            part = locator_by_id(page, elem_id)
            if await part.count():
                parts.append((await part.first.inner_text()).strip())
        if parts:
            return " ".join(parts)

    legend = group.locator("legend")
    if await legend.count():
        return (await legend.first.inner_text()).strip()

    return ""


async def radio_group_question_label(page: Page, group: Locator) -> str:
    label = await group_label(page, group)
    if label:
        return label

    return await group.evaluate(
        """
        (el) => {
            const fieldset = el.closest('fieldset');
            if (fieldset) {
                const legend = fieldset.querySelector('legend');
                if (legend?.textContent?.trim()) return legend.textContent.trim();
            }

            const radiogroup = el.closest('[role=radiogroup]');
            if (radiogroup) {
                const labelledBy = radiogroup.getAttribute('aria-labelledby');
                if (labelledBy) {
                    const parts = labelledBy.split(/\\s+/).map((id) => {
                        const node = document.getElementById(id);
                        return node?.textContent?.trim() || '';
                    }).filter(Boolean);
                    if (parts.length) return parts.join(' ');
                }
                const aria = radiogroup.getAttribute('aria-label');
                if (aria?.trim()) return aria.trim();
            }

            const container = el.closest(
                '[class*=question], [class*=field], [class*=form-group], tr, li, .row, .col'
            ) || el.parentElement?.parentElement;
            if (!container) return '';

            const clone = container.cloneNode(true);
            clone.querySelectorAll('input, button, select, textarea').forEach((node) => node.remove());
            return (clone.textContent || '').replace(/\\s+/g, ' ').trim();
        }
        """
    )


async def fill_radio_group(
    page: Page,
    profile: dict,
    group: Locator,
    label: str,
) -> tuple[Action | None, Action | None]:
    skip_reason = should_skip_field(label, profile)
    if skip_reason:
        return None, {"label": label, "key": label, "error": skip_reason}

    mapping = map_label_to_field(label)
    if not mapping:
        return None, None

    value = get_section_value(profile, mapping.section, mapping.key)
    if value is None or value == "":
        return None, None

    key = f"{mapping.section}.{mapping.key}"
    candidates = yes_no_candidates(str(value)) + [str(value)]
    radios = group.locator("input[type=radio]:visible")
    radio_count = await radios.count()

    for j in range(radio_count):
        radio = radios.nth(j)
        radio_label = await accessible_name(page, radio)
        if not radio_label:
            parent_label = radio.locator("xpath=ancestor::label[1]")
            if await parent_label.count():
                radio_label = (await parent_label.first.inner_text()).strip()

        if text_matches_any(radio_label, candidates):
            await radio.check()
            return {"label": label, "key": key, "value": radio_label}, None

    return None, {
        "label": label,
        "key": key,
        "value": str(value),
        "error": f"no radio option matched {candidates}",
    }


async def fill_radio_groups(page: Page, profile: dict) -> tuple[list[Action], list[Action]]:
    filled: list[Action] = []
    skipped: list[Action] = []
    handled_names: set[str] = set()

    count = await safe_count(
        page.locator("[role=radiogroup]:visible, fieldset:has(input[type=radio]:visible)")
    )

    for i in range(count):
        group = page.locator("[role=radiogroup]:visible, fieldset:has(input[type=radio]:visible)").nth(i)
        try:
            label = await radio_group_question_label(page, group)
            if not label:
                continue

            first_radio = group.locator("input[type=radio]:visible").first
            if await safe_count(first_radio):
                name = await safe_attr(first_radio, "name")
                if name:
                    handled_names.add(name)

            action, skip = await fill_radio_group(page, profile, group, label)
            if action:
                filled.append(action)
            if skip:
                skipped.append(skip)
        except Exception as exc:
            skipped.append({"label": f"radio-group[{i}]", "key": "?", "error": str(exc)})

    radios = page.locator("input[type=radio]:visible")
    radio_count = await safe_count(radios)
    for i in range(radio_count):
        radio = radios.nth(i)
        try:
            name = await safe_attr(radio, "name") or f"__radio_{i}"
            if name in handled_names:
                continue
            handled_names.add(name)

            group = page.locator(f'input[type=radio][name="{name}"]:visible')
            if not await safe_count(group):
                continue

            label = await radio_group_question_label(page, group.first)
            if not label:
                continue

            action, skip = await fill_radio_group(page, profile, group, label)
            if action:
                filled.append(action)
            if skip:
                skipped.append(skip)
        except Exception as exc:
            skipped.append({"label": f"radio[{i}]", "key": "?", "error": str(exc)})

    return filled, skipped


def checkbox_target_state(
    label: str,
    profile: dict,
    mapping: FieldMapping | None,
) -> bool | None:
    if mapping:
        value = get_section_value(profile, mapping.section, mapping.key)
        if isinstance(value, bool):
            return value
        if value is not None and value != "":
            v = str(value).casefold()
            if v in {"true", "yes", "1"}:
                return True
            if v in {"false", "no", "0"}:
                return False

    heard_about = profile.get("heard_about", [])
    if heard_about and text_matches_any(label, heard_about):
        return True

    skills = profile.get("skills", [])
    if skills and text_matches_any(label, skills):
        return True

    return None


async def fill_checkboxes(page: Page, profile: dict) -> tuple[list[Action], list[Action]]:
    filled: list[Action] = []
    skipped: list[Action] = []
    checkboxes = page.locator("input[type=checkbox]:visible")
    count = await checkboxes.count()

    for i in range(count):
        element = checkboxes.nth(i)
        label = await accessible_name(page, element)
        if not label:
            parent_label = element.locator("xpath=ancestor::label[1]")
            if await parent_label.count():
                label = (await parent_label.first.inner_text()).strip()
        if not label:
            continue

        skip_reason = should_skip_field(label, profile)
        if skip_reason:
            skipped.append({"label": label, "key": label, "error": skip_reason})
            continue

        mapping = map_label_to_field(label)
        target = checkbox_target_state(label, profile, mapping)
        if target is None:
            continue

        key = f"{mapping.section}.{mapping.key}" if mapping else label
        try:
            if target:
                await element.check()
                filled.append({"label": label, "key": key, "value": "checked"})
            else:
                await element.uncheck()
                filled.append({"label": label, "key": key, "value": "unchecked"})
        except Exception as exc:
            skipped.append({"label": label, "key": key, "error": str(exc)})

    return filled, skipped


async def fill_custom_dropdowns(page: Page, profile: dict) -> tuple[list[Action], list[Action]]:
    filled: list[Action] = []
    skipped: list[Action] = []
    from src.dropdown_fill import fill_dropdown_field, is_placeholder_value

    count = await safe_count(page.locator(DROPDOWN_SELECTOR))

    for i in range(count):
        trigger = page.locator(DROPDOWN_SELECTOR).nth(i)
        try:
            if not await safe_count(trigger):
                continue

            label = await resolve_field_label(page, trigger)
            skip_reason = should_skip_field(label, profile)
            if skip_reason:
                skipped.append({"label": label, "key": label, "error": skip_reason})
                continue

            elem_id = await safe_attr(trigger, "id") or ""
            name = await safe_attr(trigger, "name") or ""
            input_type = (await safe_attr(trigger, "type") or "").lower()
            mapping = infer_mapping(label, input_type, elem_id, name) or map_label_to_field(label)
            if not mapping:
                continue

            value = get_section_value(profile, mapping.section, mapping.key)
            if value is None or value == "":
                continue

            tag = await safe_evaluate(trigger, "el => el.tagName.toLowerCase()")
            if tag == "select":
                current = await read_select_display_value(trigger)
                if current and not is_placeholder_value(current) and current.casefold() == str(value).casefold():
                    continue

            key = f"{mapping.section}.{mapping.key}"
            fill_key = "source" if mapping.section == "heard_about" else mapping.key
            filled_value = await fill_dropdown_field(page, trigger, fill_key, str(value))
            filled.append({"label": label, "key": key, "value": filled_value})
        except Exception as exc:
            skipped.append({"label": f"dropdown[{i}]", "key": "?", "error": str(exc)})

    return filled, skipped


async def find_late_contact_elements(page: Page) -> list[tuple[str, str, str, Locator]]:
    """Return (profile_key, field_key, label, element) for late-fill contact fields."""
    found: list[tuple[str, str, str, Locator]] = []
    seen: set[str] = set()

    async def add_field(element: Locator, mapping: FieldMapping, label: str) -> None:
        elem_id = await safe_attr(element, "id") or ""
        name = await safe_attr(element, "name") or ""
        dedupe_key = f"{mapping.key}:{elem_id}:{name}"
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        field_key = f"{mapping.section}.{mapping.key}"
        found.append((mapping.key, field_key, label or mapping.key, element))

    count = await safe_count(page.locator(TEXT_INPUT_SELECTOR))
    for i in range(count):
        element = page.locator(TEXT_INPUT_SELECTOR).nth(i)
        try:
            input_type = (await safe_attr(element, "type") or "").lower()
            if input_type in {"hidden", "checkbox", "radio", "file"}:
                continue

            elem_id = await safe_attr(element, "id") or ""
            name = await safe_attr(element, "name") or ""
            label = await accessible_name(page, element)
            mapping = infer_mapping(label, input_type, elem_id, name)
            if mapping and mapping.section == "contact" and mapping.key in LATE_CONTACT_KEYS:
                await add_field(element, mapping, label)
        except Exception:
            continue

    email_count = await safe_count(page.locator(EMAIL_INPUT_SELECTOR))
    for i in range(email_count):
        element = page.locator(EMAIL_INPUT_SELECTOR).nth(i)
        try:
            input_type = (await safe_attr(element, "type") or "").lower()
            if input_type in {"hidden", "checkbox", "radio", "file"}:
                continue
            label = await accessible_name(page, element)
            await add_field(element, FieldMapping("contact", "email"), label)
        except Exception:
            continue

    return found


def late_contact_sort_key(item: tuple[str, str, str, Locator]) -> tuple[int, int, str]:
    profile_key, _, label, _ = item
    order = LATE_CONTACT_ORDER.get(profile_key, 99)
    confirm = 1 if profile_key == "email" and "confirm" in label.casefold() else 0
    return (order, confirm, label)


async def fill_late_contact_fields(page: Page, profile: dict) -> tuple[list[Action], list[Action]]:
    """Fill contact fields that React clears when other inputs or dropdowns change."""
    filled: list[Action] = []
    skipped: list[Action] = []
    await page.wait_for_timeout(500)

    elements = await find_late_contact_elements(page)
    elements.sort(key=late_contact_sort_key)

    targets: list[tuple[str, str, str, Locator]] = []
    for profile_key, field_key, label, element in elements:
        section, key = field_key.split(".", 1)
        value = get_section_value(profile, section, key)
        if value is None or value == "":
            continue
        targets.append((field_key, label, str(value), element))

    for field_key, label, value, element in targets:
        try:
            await fill_react_controlled_field(page, element, value)
            filled.append({"label": label, "key": field_key, "value": value})
        except Exception as exc:
            skipped.append({"label": label, "key": field_key, "value": value, "error": str(exc)})

    await page.wait_for_timeout(300)
    for field_key, label, value, element in targets:
        if await read_input_value(element) == value:
            continue
        try:
            await fill_react_controlled_field(page, element, value)
            if not any(a["key"] == field_key and a["label"] == label for a in filled):
                filled.append({"label": label, "key": field_key, "value": value})
        except Exception as exc:
            skipped.append(
                {"label": label, "key": field_key, "value": value, "error": f"re-verify: {exc}"}
            )

    return filled, skipped


async def fill_email_fields(page: Page, profile: dict) -> tuple[list[Action], list[Action]]:
    """Backward-compatible alias."""
    return await fill_late_contact_fields(page, profile)


def _truncate(text: str, max_len: int = 120) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


async def fill_essay_fields(
    page: Page,
    profile: dict,
    job_description: str = "",
) -> tuple[list[Action], list[Action]]:
    """Fill textarea essay questions using LangChain + Ollama."""
    filled: list[Action] = []
    skipped: list[Action] = []

    if not profile.get("auto_fill", {}).get("essay", True):
        return filled, skipped

    try:
        from src.llm.chain import answer_question
    except ImportError:
        skipped.append(
            {
                "label": "essay fields",
                "key": "llm",
                "error": "install LLM deps: pip install -e '.[llm]'",
            }
        )
        return filled, skipped

    textareas = page.locator("textarea:visible")
    count = await textareas.count()

    for i in range(count):
        element = textareas.nth(i)
        label = await accessible_name(page, element)
        if not label:
            continue

        skip_reason = should_skip_field(label, profile)
        if skip_reason:
            skipped.append({"label": label, "key": label, "error": skip_reason})
            continue

        mapping = map_label_to_field(label)
        if mapping:
            value = get_section_value(profile, mapping.section, mapping.key)
            if value:
                continue

        try:
            current = await element.input_value()
        except Exception:
            current = ""
        if current.strip():
            continue

        question = label.strip()
        print(f"  LLM answering: {question!r} (may take a minute)...")

        try:
            answer = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda q=question: answer_question(q, job_description=job_description),
            )
            await fill_text_field(page, element, answer)
            filled.append(
                {
                    "label": label,
                    "key": "llm.essay",
                    "value": _truncate(answer),
                }
            )
        except Exception as exc:
            skipped.append(
                {
                    "label": label,
                    "key": "llm.essay",
                    "error": str(exc),
                }
            )

    return filled, skipped


def merge_results(*results: tuple[list[Action], list[Action]]) -> tuple[list[Action], list[Action]]:
    filled: list[Action] = []
    skipped: list[Action] = []
    for part_filled, part_skipped in results:
        filled.extend(part_filled)
        skipped.extend(part_skipped)
    return filled, skipped


async def fill_form_fields(
    page: Page,
    profile: dict,
    job_description: str = "",
) -> tuple[list[Action], list[Action]]:
    """Fill contact, screening, work history, education, and LLM essay fields."""
    from src.repeater_fill import fill_education, fill_work_history

    return merge_results(
        await fill_radio_groups(page, profile),
        await fill_checkboxes(page, profile),
        await fill_text_and_select_fields(page, profile),
        await fill_custom_dropdowns(page, profile),
        await fill_work_history(page, profile),
        await fill_education(page, profile),
        await fill_essay_fields(page, profile, job_description=job_description),
        await fill_late_contact_fields(page, profile),
    )


async def fill_contact_fields(page: Page, profile: dict) -> tuple[list[Action], list[Action]]:
    """Backward-compatible alias."""
    return await fill_form_fields(page, profile)
