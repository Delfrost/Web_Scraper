import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from models import ScrapeResult, Section, Content, Meta, Link, Image, Interactions, Error
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# --- Helper: Universal HTML Parser ---
def parse_html(html: str, final_url: str) -> tuple[Meta, list[Section]]:
    """
    Parses raw HTML and extracts Meta and Sections.
    Used by both Static and Playwright scrapers.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Extract Meta
    title = soup.title.string.strip() if soup.title else ""
    
    description = ""
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if desc_tag:
        description = desc_tag.get("content", "").strip()

    language = "en"
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        language = html_tag.get("lang")

    canonical = None
    canonical_tag = soup.find("link", rel="canonical")
    if canonical_tag:
        canonical = canonical_tag.get("href")

    meta = Meta(title=title, description=description, language=language, canonical=canonical)

    # 2. Extract Sections
    sections = []
    
    # Structural heuristics
    containers = soup.find_all(['header', 'main', 'section', 'footer', 'article', 'nav'])
    if not containers:
        containers = [soup.body] if soup.body else []

    section_id_counter = 0

    for container in containers:
        if not container: continue
        
        # Label Heuristic
        label = "Section"
        first_heading = container.find(['h1', 'h2', 'h3'])
        if first_heading:
            label = first_heading.get_text(strip=True)[:50]
        else:
            text_preview = container.get_text(strip=True)
            label = " ".join(text_preview.split()[:5]) or "Empty Section"

        # Type Heuristic
        sec_type = "section"
        if container.name == "nav": sec_type = "nav"
        elif container.name == "footer": sec_type = "footer"
        elif container.name == "header": sec_type = "header"

        # Content Extraction
        text = container.get_text(" ", strip=True)
        
        links = []
        for a in container.find_all("a", href=True):
            links.append(Link(
                text=a.get_text(strip=True) or "link",
                href=urljoin(final_url, a['href'])
            ))

        images = []
        for img in container.find_all("img", src=True):
            images.append(Image(
                src=urljoin(final_url, img['src']),
                alt=img.get("alt", "")
            ))

        headings = [h.get_text(strip=True) for h in container.find_all(['h1', 'h2', 'h3', 'h4'])]

        content = Content(
            headings=headings,
            text=text,
            links=links,
            images=images
        )

        # Raw HTML Truncation
        raw_html = str(container)
        truncated = False
        if len(raw_html) > 1000:
            raw_html = raw_html[:1000] + "..."
            truncated = True

        sections.append(Section(
            id=f"sec-{section_id_counter}",
            type=sec_type,
            label=label,
            sourceUrl=final_url,
            content=content,
            rawHtml=raw_html,
            truncated=truncated
        ))
        section_id_counter += 1

    return meta, sections

# --- Strategy 1: Static Scraper ---
async def scrape_static(url: str) -> ScrapeResult:
    scraped_at = datetime.now(timezone.utc).isoformat()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0, headers={"User-Agent": "LyftrBot/1.0"}) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
            final_url = str(response.url)
            
            meta, sections = parse_html(html, final_url)
            
            return ScrapeResult(
                url=url,
                scrapedAt=scraped_at,
                meta=meta,
                sections=sections,
                interactions=Interactions(pages=[final_url]),
                errors=[]
            )
    except Exception as e:
        return ScrapeResult(
            url=url,
            scrapedAt=scraped_at,
            meta=Meta(),
            sections=[],
            errors=[Error(message=f"Static error: {str(e)}", phase="fetch")]
        )

# --- Strategy 2: Playwright Scraper (Fallback) ---
async def scrape_with_playwright(url: str) -> ScrapeResult:
    scraped_at = datetime.now(timezone.utc).isoformat()
    errors = []
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            # Create context with user agent to avoid bot detection
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
            page = await context.new_page()

            # Navigate and wait for network idle (simulates basic load wait)
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
            except Exception as e:
                errors.append(Error(message=f"Navigation timeout/error: {str(e)}", phase="render"))

            content = await page.content()
            final_url = page.url
            
            # Reuse the same parser
            meta, sections = parse_html(content, final_url)
            
            await browser.close()

            return ScrapeResult(
                url=url,
                scrapedAt=scraped_at,
                meta=meta,
                sections=sections,
                interactions=Interactions(pages=[final_url]),
                errors=errors
            )

        except Exception as e:
            return ScrapeResult(
                url=url,
                scrapedAt=scraped_at,
                meta=Meta(),
                sections=[],
                errors=[Error(message=f"Playwright error: {str(e)}", phase="render")]
            )

# --- Main Controller: Smart Scrape ---
async def scrape_smart(url: str) -> ScrapeResult:
    # 1. Try Static First
    print(f"Attempting static scrape for {url}...")
    static_result = await scrape_static(url)

    # 2. Check Heuristic: Is it 'insufficient'?
    # Condition: If we have errors OR total text extracted is very low (< 200 chars)
    total_text_len = sum(len(s.content.text) for s in static_result.sections)
    
    if not static_result.errors and total_text_len > 200:
        print("Static scrape successful.")
        return static_result

    # 3. Fallback to Playwright
    print(f"Static scrape insufficient (len={total_text_len}). Falling back to Playwright...")
    js_result = await scrape_with_playwright(url)
    
    # Merge errors if any
    if static_result.errors:
        js_result.errors.extend(static_result.errors)
        
    return js_result