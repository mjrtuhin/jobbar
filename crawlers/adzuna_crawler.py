from crawlers.base_crawler import BaseCrawler
from urllib.parse import quote_plus


class AdzunaCrawler(BaseCrawler):
    """Crawls Adzuna UK for job listings."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.source_name = "Adzuna"
        self.base_url = "https://www.adzuna.co.uk"

    def build_search_url(self, job_title: str, location: str, page: int = 1, job_type: str = "", date_posted: str = "") -> str:
        """Build the Adzuna search URL."""
        keywords = quote_plus(job_title)
        loc = quote_plus(location)
        url = f"{self.base_url}/search?q={keywords}&loc={loc}&p={page}"

        if job_type:
            type_map = {
                "full-time": "full_time",
                "part-time": "part_time",
                "contract": "contract",
                "temporary": "temporary"
            }
            ft = type_map.get(job_type.lower(), "")
            if ft:
                url += f"&cty={ft}"

        if date_posted:
            date_map = {
                "past_24h": "1",
                "past_3days": "3",
                "past_week": "7",
                "past_14days": "14"
            }
            max_days = date_map.get(date_posted, "")
            if max_days:
                url += f"&max_days_old={max_days}"

        return url

    def parse_job_card(self, card) -> dict:
        """Extract job details from a single Adzuna job card."""
        title = ""
        job_url = ""
        company = ""
        location = ""
        salary = ""
        date_posted = ""

        title_elem = card.find("h2")
        if title_elem:
            link = title_elem.find("a")
            if link:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if href.startswith("/"):
                    job_url = f"{self.base_url}{href}"
                elif href.startswith("http"):
                    job_url = href

        company_elem = card.find("div", class_="ui-provider-name")
        if not company_elem:
            company_elem = card.find("a", attrs={"data-type": "company"})
        if company_elem:
            company = company_elem.get_text(strip=True)

        location_elem = card.find("span", class_="at_location")
        if not location_elem:
            location_elem = card.find("div", class_="ui-location")
        if location_elem:
            location = location_elem.get_text(strip=True)

        salary_elem = card.find("span", class_="ui-salary")
        if not salary_elem:
            salary_elem = card.find("div", class_="salary")
        if salary_elem:
            salary = salary_elem.get_text(strip=True)

        date_elem = card.find("time")
        if date_elem:
            date_posted = date_elem.get("datetime", date_elem.get_text(strip=True))

        if not title or not job_url:
            return None

        return self.build_job_dict(title, company, location, salary, date_posted, job_url)

    def search(self, job_title: str, location: str, **filters) -> list:
        """Search Adzuna for jobs and return a list of job dicts."""
        jobs = []
        job_type = filters.get("job_type", "")
        date_posted = filters.get("date_posted", "")
        pages_to_crawl = min(self.max_results // 20, 3)

        print(f"[Adzuna] Searching for '{job_title}' in '{location}'...")

        for page_num in range(1, pages_to_crawl + 1):
            try:
                url = self.build_search_url(job_title, location, page=page_num, job_type=job_type, date_posted=date_posted)
                soup = self.fetch_page(url)

                cards = soup.find_all("div", class_="a-card")
                if not cards:
                    cards = soup.find_all("div", class_="result")
                if not cards:
                    cards = soup.find_all("article")

                if not cards:
                    print(f"[Adzuna] No more results on page {page_num}")
                    break

                for card in cards:
                    job = self.parse_job_card(card)
                    if job and len(jobs) < self.max_results:
                        jobs.append(job)

                print(f"[Adzuna] Page {page_num}: found {len(cards)} cards, total jobs: {len(jobs)}")

                if len(jobs) >= self.max_results:
                    break

            except Exception as e:
                print(f"[Adzuna] Error on page {page_num}: {e}")
                break

        print(f"[Adzuna] Done. Total jobs found: {len(jobs)}")
        return jobs
