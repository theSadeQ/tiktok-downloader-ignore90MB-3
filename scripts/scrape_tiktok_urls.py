import sys
import re
import asyncio
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from playwright.async_api import async_playwright, TimeoutError
from playwright_stealth import stealth_async

def normalize_profile_url(url: str) -> tuple[str, str]:
    """Ensures the URL is formatted correctly and extracts the username."""
    if not url.startswith("http"):
        url = "https://" + url
    
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    username = ""
    for part in path_parts:
        if part.startswith('@'):
            username = part[1:]
            break
    
    if not username and path_parts:
        username = path_parts[0]
        
    normalized_url = f"https://www.tiktok.com/@{username}"
    return normalized_url, username

def clean_video_url(url: str) -> str:
    """Removes query parameters from the video URL."""
    parsed = urlparse(url)
    clean = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    return clean

async def main():
    if len(sys.argv) < 2:
        print("Usage: python scrape_tiktok_urls.py <profile_url>")
        sys.exit(1)

    raw_url = sys.argv[1]
    profile_url, username = normalize_profile_url(raw_url)
    print(f"Targeting profile: {profile_url} (Username: {username})")

    # Setup output directory
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    output_file = downloads_dir / f"tiktok_{username}_urls.txt"
    
    # Debug file paths
    debug_initial = downloads_dir / f"debug_1_initial_{username}.png"
    debug_scrolled = downloads_dir / f"debug_2_scrolled_{username}.png"
    debug_source = downloads_dir / f"debug_3_source_{username}.html"

    async with async_playwright() as p:
        # Launch Chromium with args to help prevent detection
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # Set a standard desktop viewport
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        # Apply stealth configuration to the page BEFORE navigating
        await stealth_async(page)

        try:
            print("Navigating to profile...")
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait to clear potential Cloudflare/Turnstile verification
            print("Waiting 5 seconds to clear potential bot checks...")
            await asyncio.sleep(5)
            
            print("Capturing initial debug screenshot...")
            await page.screenshot(path=str(debug_initial), full_page=True)

            # Mimic human smooth scrolling to trigger video loading
            print("Scrolling down smoothly to trigger lazy-loaded videos...")
            await page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 300;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            
                            // Stop after scrolling down significantly or hitting bottom
                            if (totalHeight >= scrollHeight || totalHeight > 15000) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 200);
                    });
                }
            """)

            # Give DOM a final moment to render after scrolling
            print("Waiting for final DOM elements to render...")
            await asyncio.sleep(2)

            print("Capturing post-scroll debug data...")
            await page.screenshot(path=str(debug_scrolled), full_page=True)
            html_content = await page.content()
            with open(debug_source, "w", encoding="utf-8") as f:
                f.write(html_content)

            print("Extracting links...")
            links = await page.locator("a").all()
            
            video_urls = set()
            video_pattern = re.compile(r"^https?://(?:www\.)?tiktok\.com/@[^/]+/video/\d+")
            
            for link in links:
                href = await link.get_attribute("href")
                if href and video_pattern.match(href):
                    clean_url = clean_video_url(href)
                    video_urls.add(clean_url)
            
            sorted_urls = sorted(list(video_urls))
            
            with open(output_file, "w") as f:
                for url in sorted_urls:
                    f.write(url + "\n")
            
            print(f"SUCCESS: Found {len(sorted_urls)} video URLs.")
            print(f"Saved to {output_file}")
            
            if len(sorted_urls) == 0:
                print("\nWARNING: ZERO URLS FOUND.")
                print("Even with stealth, TikTok might have detected the datacenter IP.")
                print(f"Please check the debug images in the downloads folder to see what the bot actually saw.")
            
        except TimeoutError:
            print("Error: Page load timed out.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
