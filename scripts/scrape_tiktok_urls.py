import sys
import re
import time
import os
from playwright.sync_api import sync_playwright

def main():
    # 1. Validate Input
    if len(sys.argv) < 2:
        print("Usage: python scrape_tiktok_urls.py <tiktok_url>")
        sys.exit(1)

    tiktok_url = sys.argv[1]
    
    # 2. Extract the username from the official TikTok URL
    # Regex looks for the '@' symbol and captures everything up to the next space or slash
    match = re.search(r'@([a-zA-Z0-9_.-]+)', tiktok_url)
    if not match:
        print(f"Error: Could not extract a valid username from {tiktok_url}")
        sys.exit(1)
        
    username = match.group(1)
    
    # 3. Construct the localized Mirror Site URL (Urlebird Taiwan endpoint)
    urlebird_url = f"https://urlebird.com/tw/user/{username}/"
    print(f"Targeting mirror site: {urlebird_url}")

    with sync_playwright() as p:
        # Launch Chromium headless (no stealth needed for Urlebird!)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Go to the mirror site
            page.goto(urlebird_url, wait_until="domcontentloaded", timeout=60000)
            
            # Scroll down a few times to trigger lazy-loading of images/videos
            # Note: The image shows a "加載更多" (Load More) button, but scrolling 
            # often triggers the initial batch load.
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)
                
            # 4. Extract all link elements that point to a video
            # We look for any <a> tag whose href contains '/video/'
            links = page.eval_on_selector_all(
                "a[href*='/video/']", 
                "elements => elements.map(el => el.href)"
            )
            
            video_ids = set() # Use a set to automatically remove duplicates
            
            # 5. Extract IDs and Reconstruct
            for link in links:
                # Regex looks for a dash, followed by numbers, optionally ending with a slash
                # e.g., "title-of-video-7123456789/" -> captures "7123456789"
                id_match = re.search(r'-(\d+)/?$', link)
                if id_match:
                    video_ids.add(id_match.group(1))
                    
            if not video_ids:
                print("No video IDs found. The page might be empty or the structure changed.")
            else:
                # 6. Save the reconstructed Official TikTok URLs
                os.makedirs("downloads", exist_ok=True)
                output_file = f"downloads/tiktok_{username}_urls.txt"
                
                with open(output_file, "w", encoding="utf-8") as f:
                    # Sort reverse so newest (usually higher ID) is at the top
                    for vid_id in sorted(video_ids, reverse=True): 
                        official_url = f"https://www.tiktok.com/@{username}/video/{vid_id}"
                        f.write(f"{official_url}\n")
                        
                print(f"Success! Scraped {len(video_ids)} video IDs and saved to {output_file}")
                
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
