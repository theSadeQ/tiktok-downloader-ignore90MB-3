# File: scripts/scrape_tiktok_urls.py

import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

def normalize_profile_url(raw_url: str) -> tuple[str, str]:
    """
    Normalizes different TikTok URL formats into a standard profile URL.
    Returns the normalized URL and the extracted username.
    """
    raw_url = raw_url.strip()
    if not raw_url.startswith("http"):
        raw_url = "https://" + raw_url
        
    parsed = urlparse(raw_url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    username = ""
    for part in path_parts:
        if part.startswith('@') or (len(path_parts) == 1 and not part.startswith('video')):
            username = part if part.startswith('@') else f"@{part}"
            break
            
    if not username:
        raise ValueError(f"Could not extract username from URL: {raw_url}")

    normalized_url = f"https://www.tiktok.com/{username}"
    return normalized_url, username.replace('@', '')

def clean_video_url(url: str) -> str:
    """Removes query parameters from the video URL for cleaner output."""
    parsed = urlparse(url)
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    return clean_url

async def scrape_profile(raw_url: str):
    """
    Scrapes a TikTok profile for video URLs and captures debug artifacts.
    """
    try:
        target_url, username = normalize_profile_url(raw_url)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Normalized Target URL: {target_url}")
    print(f"Target Username: {username}")

    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    
    output_file = downloads_dir / f"tiktok_{username}_urls.txt"
    
    # Debug artifact paths
    debug_initial_png = downloads_dir / f"debug_1_initial_{username}.png"
    debug_scrolled_png = downloads_dir / f"debug_2_scrolled_{username}.png"
    debug_html_source = downloads_dir / f"debug_3_source_{username}.html"

    async with async_playwright() as p:
        print("Launching headless Chromium browser...")
        # We launch headless, but set a standard viewport (window size) 
        # so our screenshots look like a real desktop screen.
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        try:
            print("Navigating to profile page...")
            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            
            # --- DEBUG SYSTEM: STAGE 1 ---
            print(f"Taking initial load screenshot -> {debug_initial_png.name}")
            await page.screenshot(path=debug_initial_png)

            print("Scrolling to load videos (5 iterations)...")
            for i in range(5):
                print(f"  Scroll {i+1}/5...")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)  # Wait for dynamic content to load

            # --- DEBUG SYSTEM: STAGE 2 & 3 ---
            print(f"Taking post-scroll screenshot -> {debug_scrolled_png.name}")
            await page.screenshot(path=debug_scrolled_png)
            
            print(f"Saving raw HTML source -> {debug_html_source.name}")
            html_content = await page.content()
            with open(debug_html_source, "w", encoding="utf-8") as f:
                f.write(html_content)

            print("Extracting links from the DOM...")
            links = await page.locator("a").all()
            
            video_urls = set()
            # TikTok video URL pattern: https://www.tiktok.com/@username/video/1234567890
            pattern = re.compile(r"^https?://(?:www\.)?tiktok\.com/@[^/]+/video/\d+")

            for link in links:
                href = await link.get_attribute("href")
                if href and pattern.match(href):
                    video_urls.add(clean_video_url(href))

            sorted_urls = sorted(list(video_urls))

            print(f"Found {len(sorted_urls)} unique video URLs.")
            
            # Always write to file (creates an empty file if 0 found)
            with open(output_file, "w", encoding="utf-8") as f:
                for url in sorted_urls:
                    f.write(f"{url}\n")
            
            print(f"Successfully saved to {output_file}")

            if len(sorted_urls) == 0:
                print("\n--- ZERO URLS FOUND ---")
                print("Please check the 'downloads/' folder in your repository for the debug files:")
                print(f"1. {debug_initial_png.name} (Did it hit a CAPTCHA immediately?)")
                print(f"2. {debug_scrolled_png.name} (Did the page load blank?)")
                print(f"3. {debug_html_source.name} (Check for 'Access Denied' or Cloudflare/bot-protection text)")

        except PlaywrightTimeoutError:
            print("Error: Timed out while waiting for the page to load.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            print("Closing browser...")
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/scrape_tiktok_urls.py <tiktok_profile_url>")
        sys.exit(1)
    
    asyncio.run(scrape_profile(sys.argv[1]))
