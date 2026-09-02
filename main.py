import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import Page, async_playwright

from src.filler import fill_form_fields
from src.job_description import load_job_description
from src.profile import load_profile

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"


def launch_kwargs() -> dict:
    headless = os.environ.get("HEADLESS", "").lower() in {"1", "true", "yes"}
    kwargs: dict = {
        "headless": headless,
        "args": [
            "--start-maximized",
            "--window-size=1400,900",
            "--window-position=0,0",
        ],
    }

    if os.geteuid() == 0:
        print(
            "WARNING: Running as root — the browser tile may be blank on i3.\n"
            "         Run as your normal user instead:  su - cifra\n"
            "         Or use HEADLESS=1 and open data/last-run.png\n"
        )
        kwargs["args"].append("--no-sandbox")

    if os.environ.get("DISPLAY") in (None, ""):
        print("Warning: DISPLAY is not set. GUI browser may not appear.")

    return kwargs


async def launch_browser(playwright):
    kwargs = launch_kwargs()

    for channel in ("chrome", "chromium", None):
        try:
            if channel:
                browser = await playwright.chromium.launch(channel=channel, **kwargs)
                print(f"Launched browser: {channel}")
            else:
                browser = await playwright.chromium.launch(**kwargs)
                print("Launched browser: playwright chromium")
            return browser
        except Exception as exc:
            if channel is None:
                raise
            print(f"Could not launch {channel}: {exc}")

    raise RuntimeError("No browser could be launched")


def print_actions(filled: list, skipped: list) -> None:
    if filled:
        print("Filled fields:")
        for action in filled:
            print(f"  [{action['key']}] {action['label']!r} = {action['value']!r}")
    else:
        print("No fields filled on this page.")

    if skipped:
        print("\nSkipped fields:")
        for action in skipped:
            detail = action.get("error", "unknown")
            print(f"  [{action.get('key', '?')}] {action['label']!r}: {detail}")


async def wait_for_user_next(page_num: int, max_pages: int) -> bool:
    """Pause so the user can review and click Next manually. Returns False to stop."""
    if page_num >= max_pages:
        return False

    print("\n" + "-" * 50)
    print("Review the form in the browser.")
    print("Click Next when ready, then press Enter here to fill the next page.")
    print("Type 'q' + Enter to stop.")
    print("-" * 50)

    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: input("> ").strip().lower()
    )
    return response != "q"


async def fill_all_pages(
    page: Page,
    profile: dict,
    job_description: str,
    max_pages: int,
) -> tuple[list, list]:
    all_filled: list = []
    all_skipped: list = []

    for page_num in range(1, max_pages + 1):
        print(f"\n{'=' * 50}")
        print(f"Page {page_num}")
        print(f"{'=' * 50}")

        filled, skipped = await fill_form_fields(page, profile, job_description=job_description)
        all_filled.extend(filled)
        all_skipped.extend(skipped)
        print_actions(filled, skipped)

        if not await wait_for_user_next(page_num, max_pages):
            print("\nStopping — review and submit manually in the browser.")
            break

    return all_filled, all_skipped


async def run(url: str, job_path: Path | None = None, max_pages: int = 10) -> None:
    load_dotenv()
    profile = load_profile()
    job_description = load_job_description(job_path)
    contact = profile["contact"]
    print(f"Loaded profile for {contact.get('full_name', contact.get('first_name', 'unknown'))}")
    if job_description:
        print("Job description loaded for LLM context")
    print(f"Opening {url}")
    print(f"Max pages: {max_pages} (you click Next — script never auto-clicks)\n")

    if not os.environ.get("HEADLESS"):
        print("If you don't see the browser on i3, check other workspaces (Mod+1..9) or Mod+j/k.\n")

    async with async_playwright() as p:
        browser = await launch_browser(p)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto(url, wait_until="domcontentloaded")
        await page.bring_to_front()
        await page.wait_for_timeout(2000)

        all_filled, all_skipped = await fill_all_pages(
            page, profile, job_description, max_pages=max_pages
        )

        print(f"\n{'=' * 50}")
        print(f"Done — filled {len(all_filled)} fields across all pages")
        print(f"{'=' * 50}")

        screenshot_path = DATA_DIR / "last-run.png"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"\nScreenshot saved to {screenshot_path}")
        except OSError as exc:
            fallback = Path("/tmp/job-app-agent-last-run.png")
            await page.screenshot(path=str(fallback), full_page=True)
            print(f"\nCould not write {screenshot_path} ({exc})")
            print(f"Screenshot saved to {fallback}")

        if os.environ.get("HEADLESS"):
            print("HEADLESS mode — open the screenshot to review the form.")
        else:
            print("\nBrowser left open for review. Press Enter to close.")
            await asyncio.get_event_loop().run_in_executor(None, input)

        await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-fill job application forms")
    parser.add_argument("url", help="Job application form URL")
    parser.add_argument(
        "--job",
        type=Path,
        help="Job description text file for LLM essay answers (default: data/job-description.txt)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Maximum pages to fill (default: 10). Never clicks Submit.",
    )
    args = parser.parse_args()
    asyncio.run(run(args.url, job_path=args.job, max_pages=args.max_pages))


if __name__ == "__main__":
    main()
