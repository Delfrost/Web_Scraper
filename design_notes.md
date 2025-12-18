# Design Notes

## Static vs JS Fallback
- **Strategy:** I implemented a "Static-First" approach to prioritize speed and resource efficiency. The system first attempts a fast `httpx` fetch.
- **Trigger:** We upgrade to Playwright if:
  1. The static scrape fails (errors).
  2. The extracted text is insufficient (< 200 characters).
  3. **Interaction Cues:** Specific keywords (e.g., "Load More", "Next Page") are detected in the static links, indicating hidden paginated content that requires interaction.

## Wait Strategy for JS
- **Network Idle:** I use `networkidle` state to ensure initial JS content is fully populated.
- **Wait for Selectors:** For interactions, I explicitly wait for specific button selectors (e.g., `button:has-text('Load More')`).
- **Details:** The scraper uses a robust `try/finally` block to record visited URLs even if a timeout occurs during the heavy loading of subsequent pages.

## Click & Scroll Strategy
- **Click flows:** The scraper looks for a wide range of pagination selectors, including `button:has-text('Show More')`, `a:text-is('Next')`, and `a:text-is('More')`.
- **Scroll/Pagination:** It performs a loop of 3 interactions. In each iteration, it attempts to scroll to the bottom. If the scroll does not increase page height, it attempts to find and click a "Next/More" button.
- **Stop conditions:** The loop terminates after 3 interaction cycles or if no further content loads.

## Section Grouping & Labels
- **Grouping:** Content is grouped by semantic HTML tags (`<header>`, `<main>`, `<section>`, `<footer>`, `<article>`, `<nav>`). If these are missing, it falls back to the `<body>` tag.
- **Labels:** The label is derived from the first Heading tag (`h1`-`h3`) found within the section. If no heading exists, it falls back to the first 5 words of the section text.
- **Types:** Types (`nav`, `footer`, `header`) are inferred directly from the HTML tag names.

## Noise Filtering & Truncation
- **Filtering:** The scraper focuses on semantic containers to naturally avoid some noise, though strict CSS removal of ads/banners is handled by the browser context's user agent and layout rendering.
- **Truncation:** The `rawHtml` field is strictly truncated to 1000 characters to prevent massive JSON payloads, with the `truncated` boolean set to true.