from crawlers.base_crawler import BaseCrawler
from urllib.parse import quote_plus
import time


class LinkedInCrawler(BaseCrawler):
    """Crawls LinkedIn public job listings using Playwright headless browser."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.source_name = "LinkedIn"
        self.base_url = "https://www.linkedin.com"

    def build_search_url(self, job_title: str, location: str, start: int = 0, date_posted: str = "", job_type: str = "") -> str:
        """Build LinkedIn job search URL using the public jobs endpoint."""
        keywords = quote_plus(job_title)
        loc = quote_plus(location)
        url = f"{self.base_url}/jobs/search?keywords={keywords}&location={loc}&start={start}"

        if date_posted:
            date_map = {
                "past_24h": "r86400",
                "past_week": "r604800",
                "past_month": "r2592000"
            }
            f_tpr = date_map.get(date_posted, "")
            if f_tpr:
                url += f"&f_TPR={f_tpr}"

        if job_type:
            type_map = {
                "full-time": "F",
                "part-time": "P",
                "contract": "C",
                "temporary": "T",
                "internship": "I"
            }
            f_jt = type_map.get(job_type.lower(), "")
            if f_jt:
                url += f"&f_JT={f_jt}"

        return url

    def search(self, job_title: str, location: str, **filters) -> list:
        """Search LinkedIn for jobs using Playwright headless browser."""
        jobs = []
        job_type = filters.get("job_type", "")
        date_posted = filters.get("date_posted", "")

        print(f"[LinkedIn] Searching for '{job_title}' in '{location}'...")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[LinkedIn] Playwright not installed. Run: pip install playwright && playwright install chromium")
            return jobs

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.get_headers()["User-Agent"],
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()

                pages_to_crawl = min(self.max_results // 25, 3)

                for page_num in range(pages_to_crawl):
                    start = page_num * 25
                    url = self.build_search_url(job_title, location, start=start, date_posted=date_posted, job_type=job_type)

                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(self.rate_limit + 2)

                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)

                    cards = page.query_selector_all("div.base-card")
                    if not cards:
                        cards = page.query_selector_all("div.job-search-card")
                    if not cards:
                        cards = page.query_selector_all("li.jobs-search-results__list-item")

                    if not cards:
                        print(f"[LinkedIn] No results on page {page_num + 1}")
                        break

                    for card in cards:
                        try:
                            title_elem = card.query_selector("h3.base-search-card__title")
                            if not title_elem:
                                title_elem = card.query_selector("span.sr-only")
                            title = title_elem.inner_text().strip() if title_elem else ""

                            link_elem = card.query_selector("a.base-card__full-link")
                            if not link_elem:
                                link_elem = card.query_selector("a")
                            job_url = link_elem.get_attribute("href") if link_elem else ""

                            company_elem = card.query_selector("h4.base-search-card__subtitle")
                            if not company_elem:
                                company_elem = card.query_selector("a.hidden-nested-link")
                            company = company_elem.inner_text().strip() if company_elem else ""

                            location_elem = card.query_selector("span.job-search-card__location")
                            loc = location_elem.inner_text().strip() if location_elem else ""

                            date_elem = card.query_selector("time")
                            date_text = date_elem.get_attribute("datetime") if date_elem else ""

                            if title and job_url:
                                job = self.build_job_dict(title, company, loc, "", date_text, job_url)
                                jobs.append(job)

                            if len(jobs) >= self.max_results:
                                break

                        except Exception:
                            continue

                    print(f"[LinkedIn] Page {page_num + 1}: found {len(cards)} cards, total jobs: {len(jobs)}")

                    if len(jobs) >= self.max_results:
                        break

                browser.close()

        except Exception as e:
            print(f"[LinkedIn] Error: {e}")

        print(f"[LinkedIn] Done. Total jobs found: {len(jobs)}")
        return jobs
