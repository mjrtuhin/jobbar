from crawlers.base_crawler import BaseCrawler
from urllib.parse import quote_plus
import re


class ReedCrawler(BaseCrawler):
    """Crawls Reed.co.uk for job listings."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.source_name = "Reed"
        self.base_url = "https://www.reed.co.uk"

    def build_search_url(self, job_title: str, location: str, page: int = 1, job_type: str = "", date_posted: str = "") -> str:
        """Build the Reed search URL with filters."""
        keywords = quote_plus(job_title)
        loc = quote_plus(location)
        url = f"{self.base_url}/jobs/{keywords}-jobs-in-{loc}?pageno={page}"

        if job_type:
            type_map = {
                "full-time": "Full-time",
                "part-time": "Part-time",
                "contract": "Contract",
                "temporary": "Temporary"
            }
            jt = type_map.get(job_type.lower(), "")
            if jt:
                url += f"&employmenttype={quote_plus(jt)}"

        if date_posted:
            date_map = {
                "past_24h": "Today",
                "past_3days": "Last3Days",
                "past_week": "Last7Days",
                "past_14days": "Last14Days"
            }
            dp = date_map.get(date_posted, "")
            if dp:
                url += f"&dateposted={dp}"

        return url

    def extract_metadata_from_card(self, card) -> dict:
        """Extract company, location, salary from a card using multiple strategies."""
        company = ""
        location = ""
        salary = ""
        date_posted = ""

        all_text_elements = card.find_all(["span", "div", "p", "a", "li", "dd", "dt"])

        for elem in all_text_elements:
            text = elem.get_text(strip=True)
            if not text or len(text) > 200:
                continue

            classes = " ".join(elem.get("class", []))

            if not company:
                if any(kw in classes.lower() for kw in ["company", "employer", "posted-by", "postedby", "recruiter"]):
                    company = text
                elif elem.name == "a" and elem.get("href", "").startswith("/jobs/") and "jobs-in" not in elem.get("href", ""):
                    pass
                elif elem.name == "a" and "/companies/" in elem.get("href", ""):
                    company = text

            if not location:
                if any(kw in classes.lower() for kw in ["location", "loc"]):
                    location = text

            if not salary:
                if any(kw in classes.lower() for kw in ["salary", "pay", "wage"]):
                    salary = text
                elif re.search(r"[\u00a3\$]\s*[\d,]+", text):
                    salary = text

            if not date_posted:
                if any(kw in classes.lower() for kw in ["date", "posted", "time", "ago"]):
                    date_posted = text

        if not company or not location:
            meta_elements = card.find_all(["dl", "ul", "div"])
            for meta in meta_elements:
                items = meta.find_all(["dd", "li", "span"])
                for item in items:
                    text = item.get_text(strip=True)
                    if not text:
                        continue
                    if not company and ("by " in text.lower() or "posted by" in text.lower()):
                        company = text.replace("by ", "").replace("Posted by", "").strip()
                    if not location and re.search(r"[A-Z][a-z]+,?\s+[A-Z]", text) and not re.search(r"[\u00a3\$]", text):
                        if len(text) < 60:
                            location = text

        return {
            "company": company,
            "location": location,
            "salary": salary,
            "date_posted": date_posted
        }

    def parse_job_card(self, card) -> dict:
        """Extract job details from a single Reed job card."""
        title = ""
        job_url = ""

        title_elem = card.find("h2")
        if not title_elem:
            title_elem = card.find("h3")
        if title_elem:
            link = title_elem.find("a")
            if link:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if href.startswith("/"):
                    job_url = f"{self.base_url}{href}"
                else:
                    job_url = href
            else:
                title = title_elem.get_text(strip=True)

        if not title:
            links = card.find_all("a", href=True)
            for link in links:
                href = link.get("href", "")
                if "/jobs/" in href and "?" not in href.split("/jobs/")[1][:20]:
                    text = link.get_text(strip=True)
                    if text and len(text) > 5:
                        title = text
                        if href.startswith("/"):
                            job_url = f"{self.base_url}{href}"
                        else:
                            job_url = href
                        break

        if not title or not job_url:
            return None

        meta = self.extract_metadata_from_card(card)

        return self.build_job_dict(
            title,
            meta["company"],
            meta["location"],
            meta["salary"],
            meta["date_posted"],
            job_url
        )

    def search(self, job_title: str, location: str, **filters) -> list:
        """Search Reed for jobs and return a list of job dicts."""
        jobs = []
        job_type = filters.get("job_type", "")
        date_posted = filters.get("date_posted", "")
        pages_to_crawl = min(self.max_results // 25, 10)

        print(f"[Reed] Searching for '{job_title}' in '{location}'...")

        for page_num in range(1, pages_to_crawl + 1):
            try:
                url = self.build_search_url(job_title, location, page=page_num, job_type=job_type, date_posted=date_posted)
                soup = self.fetch_page(url)

                cards = soup.find_all("article")
                if not cards:
                    cards = soup.find_all("div", attrs={"data-qa": True})
                if not cards:
                    all_links = soup.find_all("a", href=re.compile(r"/jobs/.*\d+"))
                    if all_links:
                        for link in all_links:
                            parent = link.find_parent(["article", "div", "li"])
                            if parent and parent not in cards:
                                cards.append(parent)

                if not cards:
                    print(f"[Reed] No more results on page {page_num}")
                    break

                page_jobs = 0
                for card in cards:
                    job = self.parse_job_card(card)
                    if job and len(jobs) < self.max_results:
                        jobs.append(job)
                        page_jobs += 1

                print(f"[Reed] Page {page_num}: found {page_jobs} jobs, total: {len(jobs)}")

                if len(jobs) >= self.max_results or page_jobs == 0:
                    break

            except Exception as e:
                print(f"[Reed] Error on page {page_num}: {e}")
                break

        print(f"[Reed] Done. Total jobs found: {len(jobs)}")
        return jobs
