import sys
import re
import time
import os
from playwright.sync_api import sync_playwright

def main():
    # 1. Ensure we receive the Urlebird URL as an argument
    if len(sys.argv) < 2:
        print("Usage: python scrape_tiktok_urls.py <urlebird_url>")
        sys.exit(1)

    urlebird_url = sys.argv[1]
    
    # 2. Extract the username directly from the Urlebird URL
    # Looks for '/user/' followed by the username characters
    match = re.search(r'/user/([a-zA-Z0-9_.-]+)', urlebird_url)
    if not match:
        print(f"Error: Could not extract username from {urlebird_url}")
        sys.exit(1)
        
    username = match.group(1)
    print(f"Targeting mirror site: {urlebird_url} for user: @{username}")

    with sync_playwright() as p:
        # Launch Chromium (No stealth arguments needed for Urlebird!)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(urlebird_url, wait_until="domcontentloaded", timeout=60000)
            
            # Scroll down to trigger lazy-loading of the videos
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)
                
            # 3. Find all video links on the page
            links = page.eval_on_selector_all(
                "a[href*='/video/']", 
                "elements => elements.map(el => el.href)"
            )
            
            video_ids = set() # Set prevents duplicates
            
            # 4. Extract IDs from the Urlebird links
            for link in links:
                # Matches the numeric ID right before an optional trailing slash
                # e.g., "title-12345/" -> captures "12345"
                id_match = re.search(r'-(\d+)/?$', link)
                if id_match:
                    video_ids.add(id_match.group(1))
                    
            if not video_ids:
                print("No video IDs found. The page might be empty.")
            else:
                # 5. Save the Reconstructed Official URLs
                os.makedirs("downloads", exist_ok=True)
                output_file = f"downloads/tiktok_{username}_urls.txt"
                
                with open(output_file, "w", encoding="utf-8") as f:
                    for vid_id in sorted(video_ids, reverse=True): 
                        official_url = f"https://www.tiktok.com/@{username}/video/{vid_id}"
                        f.write(f"{official_url}\n")
                        
                print(f"Success! Scraped {len(video_ids)} video IDs and saved to {output_file}")
                
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
