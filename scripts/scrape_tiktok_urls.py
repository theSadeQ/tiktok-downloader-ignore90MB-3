import sys
import re
import time
from playwright.sync_api import sync_playwright

def scrape_urlebird(urlebird_url):
    print(f"Targeting mirror site: {urlebird_url}")
    
    # Extract username for logging purposes
    username_match = re.search(r'/user/([a-zA-Z0-9_.-]+)', urlebird_url)
    username = username_match.group(1) if username_match else "unknown"
    print(f"Extracted username: @{username}")

    # Use a set to automatically prevent duplicate IDs
    video_ids = set() 

    with sync_playwright() as p:
        # Launch browser in headless mode (required for GitHub Actions)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Go to the Urlebird profile page
            page.goto(urlebird_url, wait_until="domcontentloaded", timeout=60000)
            
            # Scroll down multiple times to trigger lazy-loading of the videos
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
            
            # Grab the 'href' attribute from EVERY anchor (link) tag on the page
            all_links = page.eval_on_selector_all(
                "a", 
                "elements => elements.map(el => el.href)"
            )
            
            print(f"Total links found on page: {len(all_links)}")
            
            # Scan each link for a TikTok Video ID pattern
            for link in all_links:
                if not link:
                    continue
                    
                # Regex search: Look for a sequence of 18 to 21 digits anywhere in the URL
                match = re.search(r'(\d{18,21})', link)
                
                # If we find a long number, and the link isn't a random asset, it's a video ID
                if match:
                    video_ids.add(match.group(1))

            if not video_ids:
                print("No video IDs found. The page structure might be blocking us.")
                print("\n--- DEBUG: First 30 links found on page ---")
                for l in all_links[:30]:
                    print(l)
                print("---------------------------------------------\n")
            else:
                print(f"Successfully scraped {len(video_ids)} unique video IDs.")
                
                # Save the IDs to our output file
                with open('video_ids.txt', 'w') as f:
                    for vid in video_ids:
                        f.write(f"{vid}\n")
                        print(f"Saved: {vid}")
                        
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    # Ensure the script received a URL argument from the GitHub Actions YAML
    if len(sys.argv) < 2:
        print("Usage: python scrape_tiktok_urls.py <urlebird_url>")
        sys.exit(1)
    
    target_url = sys.argv[1]
    scrape_urlebird(target_url)
