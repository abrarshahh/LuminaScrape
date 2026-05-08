from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def crawl_page(page: Page) -> dict:
    """
    Extracts page text/HTML for LLM extraction.

    Best-effort strategy:
    - Capture HTML via Playwright.
    - Capture structured-ish text via a DOM walker (better than raw innerText for many SPAs).
    - If `crawl4ai` is available and usable, also attempt markdown conversion (optional).
    """
    logger.info("Crawling page content...")
    try:
        # Get raw HTML
        html = await page.content()
        logger.debug(f"Captured HTML content (length: {len(html)})")

        # Better-than-innerText extraction
        markdown = await page.evaluate(
            """() => {
              function visible(el) {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                if (!style) return true;
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                return true;
              }
              const blocks = [];
              const tags = new Set(['H1','H2','H3','H4','H5','H6','P','LI','TD','TH','SECTION','ARTICLE','MAIN']);
              const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null);
              while (walker.nextNode()) {
                const el = walker.currentNode;
                if (!visible(el)) continue;
                if (!tags.has(el.tagName)) continue;
                const txt = (el.innerText || '').trim();
                if (!txt) continue;
                if (txt.length < 3) continue;
                blocks.push(txt);
              }
              // De-dupe while preserving order
              const seen = new Set();
              const out = [];
              for (const b of blocks) {
                const norm = b.replace(/\\s+/g,' ').trim();
                if (!norm) continue;
                if (seen.has(norm)) continue;
                seen.add(norm);
                out.push(norm);
              }
              return out.join('\\n\\n');
            }"""
        )
        logger.info(f"Text extraction complete (length: {len(markdown)})")

        crawl4ai_md = None
        try:
            # Optional: some crawl4ai installs can convert HTML->markdown locally.
            from crawl4ai import markdown_generator  # type: ignore

            crawl4ai_md = markdown_generator.generate_markdown(html)  # type: ignore[attr-defined]
        except Exception:
            crawl4ai_md = None
        
        return {
            "url": page.url,
            "markdown": markdown,
            "html": html,
            "crawl4ai_markdown": crawl4ai_md,
        }
    except Exception as e:
        logger.error(f"Error during page crawl: {e}")
        return {"error": str(e)}
