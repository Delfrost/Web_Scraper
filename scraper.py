import httpx
import asyncio
import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from models import ScrapeResult, Section, Content, Meta, Link, Image, Interactions, Error
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# --- Helper: Universal HTML Parser ---
def parse_html(html: str, final_url: str) -> tuple[Meta, list[Section]]:
    soup = BeautifulSoup(html, "html.parser")

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

    sections = []
    containers = soup.find_all(['header', 'main', 'section', 'footer', 'article', 'nav'])
    if not containers:
        containers = [soup.body] if soup.body else []

    section_id_counter = 0

    for container in containers:
        if not container: continue
        
        label = "Section"
        first_heading = container.find(['h1', 'h2', 'h3'])
        if first_heading:
            label = first_heading.get_text(strip=True)[:50]
        else:
            text_preview = container.get_text(strip=True)
            label = " ".join(text_preview.split()[:5]) or "Empty Section"

        sec_type = "section"
        if container.name == "nav": sec_type = "nav"
        elif container.name == "footer": sec_type = "footer"
        elif container.name == "header": sec_type = "header"

        text = container.get_text(" ", strip=True)
        
        links = []
        for a in container.find_all("a", href=True):
            links.append(Link(text=a.get_text(strip=True) or "link", href=urljoin(final_url, a['href'])))

        images = []
        for img in container.find_all("img", src=True):
            images.append(Image(src=urljoin(final_url, img['src']), alt=img.get("alt", "")))

        headings = [h.get_text(strip=True) for h in container.find_all(['h1', 'h2', 'h3', 'h4'])]

        content = Content(headings=headings, text=text, links=links, images=images)

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

# Stage 2: Static Scraper
async def scrape_static(url: str) -> ScrapeResult:
    scraped_at = datetime.now(timezone.utc).isoformat()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
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

# Stage 3: Playwright Scraper
async def scrape_with_playwright(url: str) -> ScrapeResult:
    scraped_at = datetime.now(timezone.utc).isoformat()
    errors = []
    
    visited_pages = set([url])
    clicks_performed = []
    scroll_count = 0
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception as e:
                errors.append(Error(message=f"Navigation warning: {str(e)}", phase="render"))

            for i in range(3):
                try:
                    previous_height = await page.evaluate("document.body.scrollHeight")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)
                    scroll_count += 1
                    
                    new_height = await page.evaluate("document.body.scrollHeight")
                    
                    if new_height <= previous_height:
                        selector = "button:has-text('Load More'), button:has-text('Show More'), a:text-is('Next'), a:text-is('More'), [aria-label='Next page'], a.morelink"
                        
                        button = await page.query_selector(selector)
                        if button and await button.is_visible():
                            btn_text = await button.inner_text()
                            await button.click()
                            clicks_performed.append(f"Clicked button: {btn_text[:20]}")
                            try:
                                await page.wait_for_load_state("networkidle", timeout=5000)
                            except:
                                pass 
                    
                except Exception as e:
                    print(f"Interaction error step {i}: {e}")
                    pass
                finally:
                    visited_pages.add(page.url)

            content = await page.content()
            final_url = page.url
            meta, sections = parse_html(content, final_url)
            
            await browser.close()

            return ScrapeResult(
                url=url,
                scrapedAt=scraped_at,
                meta=meta,
                sections=sections,
                interactions=Interactions(
                    clicks=clicks_performed,
                    scrolls=scroll_count,
                    pages=list(visited_pages)
                ),
                errors=errors
            )

        except Exception as e:
            return ScrapeResult(
                url=url,
                scrapedAt=scraped_at,
                meta=Meta(),
                sections=[],
                errors=[Error(message=f"Playwright fatal error: {str(e)}", phase="render")]
            )

# Stage 4: Main Controller
async def scrape_smart(url: str) -> ScrapeResult:
    print(f"Attempting static scrape for {url}...")
    static_result = await scrape_static(url)

    total_text_len = sum(len(s.content.text) for s in static_result.sections)
    if static_result.errors or total_text_len < 200 or not static_result.meta.title:
        print(f"Static scrape insufficient (len={total_text_len}). Falling back to Playwright...")
        js_result = await scrape_with_playwright(url)
        if static_result.errors:
            js_result.errors.extend(static_result.errors)
        return js_result

    all_links = [link.text.lower() for sec in static_result.sections for link in sec.content.links]
    interaction_keywords = ["load more", "show more", "next page", "more articles"]
    
    has_exact_more = any(link.text.strip() == "More" for sec in static_result.sections for link in sec.content.links)
    has_interaction_cues = any(keyword in link_text for link_text in all_links for keyword in interaction_keywords)

    if has_interaction_cues or has_exact_more:
        print(f"Interaction cues detected. Upgrading to Playwright for depth...")
        js_result = await scrape_with_playwright(url)
        return js_result

    print("Static scrape successful and no interactions detected.")
    return static_result