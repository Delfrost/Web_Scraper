# Web Scraper

A universal website scraper that converts web pages into structured JSON. It uses a "Static-First" hybrid approach, utilizing `httpx` for speed and upgrading to `Playwright` only when JavaScript rendering or deep pagination is required.

## Setup & Run

The project includes a `run.sh` script that handles virtual environment creation, dependency installation, and server startup.

### Prerequisites
- Python 3.10+
- Git Bash (if on Windows) or Terminal

### How to Run
1. Open your terminal in the project root.
2. Make the script executable and run it:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
   **Note:** This will install dependencies (including Playwright browsers) and start the server on port 8000.

3. **Access the Frontend:** Open http://localhost:8000 in your browser.

## Testing
I have tested the scraper against the following primary URLs:

**https://example.com**
- **Type:** Static Page
- **Result:** Successfully scraped using the fast static strategy.

**https://angular.io/**
- **Type:** JS-Heavy / SPA
- **Result:** Correctly detected insufficient static content and fell back to Playwright to render the full homepage.

**https://news.ycombinator.com/**
- **Type:** Pagination / Interaction
- **Result:** Detected the "More" button cues, upgraded to Playwright, and clicked through multiple pages to reach depth >= 3 (scraped 90+ stories).

## Known Limitations
- **Windows Subprocesses:** On Windows, uvicorn auto-reload can conflict with Playwright's asyncio loop. The `server.py` script forces `reload=False` to resolve this.
- **Strict Selectors:** The click strategy relies on English keywords ("More", "Next"). Non-English sites may require selector updates.