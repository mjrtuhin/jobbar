from crawlers.base_crawler import BaseCrawler
from urllib.parse import quote_plus
import time


class IndeedCrawler(BaseCrawler):
    """Crawls Indeed UK for job listings using Playwright headless browser."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.source_name = "Indeed"
        self.base_url = "https://uk.indeed.com"

    def build_search_url(self, job_title: str, location: str, start: int = 0, job_type: str = "", date_posted: str = "") -> str:
        """Build the Indeed search URL with filters."""
        url = f"{self.base_url}/jobs?q={quote_plus(job_title)}&l={quote_plus(location)}&start={start}"

        if job_type:
            type_map = {
                "full-time": "fulltime",
                "part-time": "parttime",
                "contract": "contract",
                "temporary": "temporary",
                "internship": "internship"
            }
            jt = type_map.get(job_type.lower(), "")
            if jt:
                url += f"&jt={jt}"

        if date_posted:
            date_map = {
                "past_24h": "1",
                "past_3days": "3",
                "past_week": "7",
                "past_14days": "14"
            }
            fromage = date_map.get(date_posted, "")
            if fromage:
                url += f"&fromage={fromage}"

        return url

    def search(self, job_title: str, location: str, **filters) -> list:
        """Search Indeed for jobs using Playwright headless browser."""
        jobs = []
        job_type = filters.get("job_type", "")
        date_posted = filters.get("date_posted", "")

        print(f"[Indeed] Searching for '{job_title}' in '{location}'...")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[Indeed] Playwright not installed. Run: pip install playwright && playwright install chromium")
            return jobs

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.get_headers()["User-Agent"],
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()

                pages_to_crawl = min(self.max_results // 15, 3)

                for page_num in range(pages_to_crawl):
                    start = page_num * 10
                    url = self.build_search_url(job_title, location, start=start, job_type=job_type, date_posted=date_posted)

                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(self.rate_limit + 2)

                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)

                    card_selectors = [
                        "div.job_seen_beacon",
                        "div.cardOutline",
                        "div.result",
                        "div[class*='job_seen']",
                        "div[class*='resultContent']",
                        "td.resultContent",
                        "li[class*='css-']"
                    ]

                    cards = []
                    for sel in card_selectors:
                        cards = page.query_selector_all(sel)
                        if cards:
                            break

                    if cards:
                        for card in cards:
                            try:
                                title = ""
                                job_url = ""
                                company = ""
                                loc = ""
                                salary = ""

                                title_selectors = [
                                    "h2.jobTitle a",
                                    "h2.jobTitle span",
                                    "h2 a",
                                    "a[data-jk]",
                                    "a.jcs-JobTitle",
                                    "span[title]"
                                ]
                                for ts in title_selectors:
                                    elem = card.query_selector(ts)
                                    if elem:
                                        title = elem.inner_text().strip()
                                        href = elem.get_attribute("href")
                                        if href:
                                            if href.startswith("/"):
                                                job_url = f"{self.base_url}{href}"
                                            elif href.startswith("http"):
                                                job_url = href
                                        break

                                if not job_url:
                                    link = card.query_selector("a[href*='/viewjob'], a[href*='/rc/clk'], a[href*='jk=']")
                                    if link:
                                        href = link.get_attribute("href")
                                        if href:
                                            job_url = href if href.startswith("http") else f"{self.base_url}{href}"
                                        if not title:
                                            title = link.inner_text().strip()

                                company_selectors = [
                                    "span[data-testid='company-name']",
                                    "span.companyName",
                                    "span.company",
                                    "a[data-tn-element='companyName']"
                                ]
                                for cs in company_selectors:
                                    elem = card.query_selector(cs)
                                    if elem:
                                        company = elem.inner_text().strip()
                                        break

                                location_selectors = [
                                    "div[data-testid='text-location']",
                                    "div.companyLocation",
                                    "span.companyLocation"
                                ]
                                for ls in location_selectors:
                                    elem = card.query_selector(ls)
                                    if elem:
                                        loc = elem.inner_text().strip()
                                        break

                                salary_selectors = [
                                    "div.salary-snippet-container",
                                    "div[data-testid='attribute_snippet_testid']",
                                    "span.salary-snippet",
                                    "div.metadata.salary-snippet-container"
                                ]
                                for ss in salary_selectors:
                                    elem = card.query_selector(ss)
                                    if elem:
                                        salary = elem.inner_text().strip()
                                        break

                                if title and job_url:
                                    job = self.build_job_dict(title, company, loc, salary, "", job_url)
                                    jobs.append(job)

                                if len(jobs) >= self.max_results:
                                    break

                            except Exception:
                                continue

                    if not cards:
                        job_links = page.query_selector_all("a[href*='/viewjob'], a[href*='/rc/clk'], a[href*='jk=']")
                        for link in job_links:
                            try:
                                title = link.inner_text().strip()
                                href = link.get_attribute("href") or ""
                                if title and href and len(title) > 5:
                                    job_url = href if href.startswith("http") else f"{self.base_url}{href}"
                                    job = self.build_job_dict(title, "", "", "", "", job_url)
                                    jobs.append(job)
                                if len(jobs) >= self.max_results:
                                    break
                            except Exception:
                                continue

                    print(f"[Indeed] Page {page_num + 1}: total jobs so far: {len(jobs)}")

                    if len(jobs) >= self.max_results:
                        break

                browser.close()

        except Exception as e:
            print(f"[Indeed] Error: {e}")

        print(f"[Indeed] Done. Total jobs found: {len(jobs)}")
        return jobs
