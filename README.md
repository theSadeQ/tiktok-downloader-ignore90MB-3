Scrape https://www.tiktok.com/@jaedengomezz
# TikTok Commit Scraper 2

This repository uses GitHub Actions and Python (Playwright) to automatically scrape public video URLs from a TikTok profile.

## How It Works
The entire process is driven by Git commit messages. When you push a commit containing a TikTok profile URL, a GitHub Action is triggered. 

The Action will:
1. Extract the URL from your commit message.
2. Spin up a headless Chromium browser using Playwright.
3. Navigate to the profile and scroll down to load videos.
4. Extract, clean, deduplicate, and sort the video URLs.
5. Save the output to a text file.
6. Commit and push the new file back to this repository automatically.

## How To Use

You don't need to change any code. Just make a Git commit with the URL anywhere in the message. 
You can use `--allow-empty` if you don't have any actual file changes to make:
```bash
git commit --allow-empty -m "scrape https://www.tiktok.com/@jaddenn"
git push

The script accepts various formats and will normalize them automatically:
- `tiktok.com/jaddenn`
- `https://tiktok.com/@jaddenn`
- `https://www.tiktok.com/@jaddenn`

## Where Results Are Saved

The resulting URLs are saved in the `downloads/` directory. The filename will be based on the extracted username. 

For example, if you scrape `@jaddenn`, the file will be:
`downloads/tiktok_jaddenn_urls.txt`

## Important Limitations & Zero URL Warnings

GitHub Actions runs on cloud servers (Microsoft Azure). Because cloud IPs are frequently used by botnets, platforms like TikTok often implement strict anti-bot measures. 

If the script returns `0` URLs, it will still create an empty text file, but print a warning in the GitHub Actions console. Common reasons include:
*   **Cloud Blocks:** TikTok is serving a CAPTCHA or login wall instead of the profile because it detects an automated cloud browser.
*   **Private/Empty Account:** The account is set to private or has no videos.
*   **Structure Changes:** TikTok frequently changes their internal HTML structure, which may break the link extraction.

*Note: This project strictly relies on public data and basic DOM scraping. It does not (and should not be used to) bypass CAPTCHAs, login walls, or access restrictions.*


### 4. Git Configuration Files

**File:** `.gitignore`

*Why this matters:* We explicitly allow `.txt` files in `downloads/` while ignoring local virtual environments, Python bytecode, and Playwright's testing artifacts to keep the repository clean.

```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual Environments
.venv/
venv/
ENV/
env/

# Playwright / Testing artifacts
playwright-report/
test-results/

# Temporary files
tmp/
*.tmp

# Note: We DO NOT ignore text files in the downloads directory
# because GitHub Actions needs to commit and push them.
