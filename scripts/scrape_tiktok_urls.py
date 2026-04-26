import sys
import re
import argparse
import asyncio
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

def normalize_profile_url(raw_url: str) -> tuple[str, str]:
    """
    Normalizes a variety of TikTok profile URL formats into a standard format.
    Returns a tuple of (normalized_url, username).
    """
    # Regex explains: Look for tiktok.com/, optional @, then capture the username
    match = re.search(r'tiktok\.com/(?:@)?([\w.-]+)', raw_url)
    if not match:
        raise ValueError(f"Could not extract TikTok username from: {raw_url}")
    
    username = match.group(1)
    normalized_url = f"https://www.tiktok.com/@{username}"
    return normalized_url, username

def clean_video_url(url: str) -> str:
    """
    Removes query strings (like ?is_from_webapp=1) from the video URL.
    """
    parsed = urlparse(url)
    # Reconstruct the URL keeping only scheme, netloc, and path
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

async def scrape_profile(url_input: str):
    """
    Main scraping logic: launches headless Chromium, navigates, scrolls, and extracts.
    """
    try:
        target_url, username = normalize_profile_url(url_input)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Targeting normalized URL: {target_url}")

    # Ensure the downloads directory exists
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    
    output_file = downloads_dir / f"tiktok_{username}_urls.txt"
    video_urls: set[str] = set()

    # Regex to match exactly a TikTok video link. 
    # e.g., https://www.tiktok.com/@username/video/1234567890
    video_regex = re.compile(r'^https?://(?:www\.)?tiktok\.com/@[^/]+/video/\d+')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Using a mobile viewport or setting specific user agents can sometimes 
        # help with bot detection, but standard desktop is a good starting point.
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        try:
            print("Navigating to profile...")
            # Wait until the DOM content is loaded
            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            
            # Allow initial page hydration
            await page.wait_for_timeout(3000)

            print("Scrolling page to load videos...")
            # Scroll multiple times to trigger lazy-loading of older videos
            for i in range(5):
                print(f"  Scroll {i + 1}/5...")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                # Give the network time to fetch new thumbnails/links
                await page.wait_for_timeout(2500)

            # Find all anchor tags on the page
            print("Extracting links...")
            links = await page.locator("a").all()
            
            for link in links:
                href = await link.get_attribute("href")
                if href and video_regex.match(href):
                    clean_url = clean_video_url(href)
                    video_urls.add(clean_url)

        except PlaywrightTimeoutError:
            print("Warning: Page load or element wait timed out. TikTok may be blocking the connection.")
        except Exception as e:
            print(f"Warning: An unexpected error occurred: {e}")
        finally:
            # ALWAYS close the browser to free up system resources
            print("Closing browser...")
            await browser.close()

    # Process and save results
    sorted_urls = sorted(list(video_urls))
    
    if not sorted_urls:
        print("\n--- WARNING: ZERO URLS FOUND ---")
        print("Possible reasons:")
        print("1. Private profile or empty account.")
        print("2. TikTok is blocking GitHub Actions IP addresses (Cloud provider ban).")
        print("3. A CAPTCHA or login wall intercepted the page load.")
        print("4. TikTok changed their HTML structure / URL scheme.")
        print("Note: An empty output file will still be created.\n")
    else:
        print(f"\nSuccessfully found {len(sorted_urls)} unique video URLs.")

    # Write to file (creates the file even if empty, as requested)
    with output_file.open("w", encoding="utf-8") as f:
        for url in sorted_urls:
            f.write(f"{url}\n")
            
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape TikTok profile for video URLs.")
    parser.add_argument("url", help="The TikTok profile URL to scrape.")
    args = parser.parse_args()

    asyncio.run(scrape_profile(args.url))
