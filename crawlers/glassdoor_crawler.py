from crawlers.base_crawler import BaseCrawler
from urllib.parse import quote_plus


class GlassdoorCrawler(BaseCrawler):
    """Crawls Glassdoor UK for job listings."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.source_name = "Glassdoor"
        self.base_url = "https://www.glassdoor.co.uk"

    def build_search_url(self, job_title: str, location: str, page: int = 1) -> str:
        """Build the Glassdoor search URL."""
        keywords = quote_plus(job_title)
        loc = quote_plus(location)
        url = f"{self.base_url}/Job/jobs.htm?sc.keyword={keywords}&locT=C&locKeyword={loc}&p={page}"
        return url

    def parse_job_card(self, card) -> dict:
        """Extract job details from a single Glassdoor job card."""
        title = ""
        job_url = ""
        company = ""
        location = ""
        salary = ""
        date_posted = ""

        title_elem = card.find("a", class_="JobCard_jobTitle")
        if not title_elem:
            title_elem = card.find("a", attrs={"data-test": "job-title"})
        if not title_elem:
            title_elem = card.find("a", class_="jobTitle")
        if title_elem:
            title = title_elem.get_text(strip=True)
            href = title_elem.get("href", "")
            if href.startswith("/"):
                job_url = f"{self.base_url}{href}"
            elif href.startswith("http"):
                job_url = href

        company_elem = card.find("span", class_="EmployerProfile_compactEmployerName")
        if not company_elem:
            company_elem = card.find("div", class_="jobCard-company")
        if not company_elem:
            company_elem = card.find("span", attrs={"data-test": "employer-name"})
        if company_elem:
            company = company_elem.get_text(strip=True)

        location_elem = card.find("div", attrs={"data-test": "emp-location"})
        if not location_elem:
            location_elem = card.find("span", class_="JobCard_location")
        if location_elem:
            location = location_elem.get_text(strip=True)

        salary_elem = card.find("div", attrs={"data-test": "detailSalary"})
        if not salary_elem:
            salary_elem = card.find("span", class_="JobCard_salaryEstimate")
        if salary_elem:
            salary = salary_elem.get_text(strip=True)

        if not title or not job_url:
            return None

        return self.build_job_dict(title, company, location, salary, date_posted, job_url)

    def search(self, job_title: str, location: str, **filters) -> list:
        """Search Glassdoor for jobs and return a list of job dicts."""
        jobs = []
        pages_to_crawl = min(self.max_results // 30, 3)

        print(f"[Glassdoor] Searching for '{job_title}' in '{location}'...")

        for page_num in range(1, pages_to_crawl + 1):
            try:
                url = self.build_search_url(job_title, location, page=page_num)
                soup = self.fetch_page(url)

                cards = soup.find_all("li", class_="JobsList_jobListItem")
                if not cards:
                    cards = soup.find_all("li", attrs={"data-test": "jobListing"})
                if not cards:
                    cards = soup.find_all("div", class_="jobCard")

                if not cards:
                    print(f"[Glassdoor] No more results on page {page_num}")
                    break

                for card in cards:
                    job = self.parse_job_card(card)
                    if job and len(jobs) < self.max_results:
                        jobs.append(job)

                print(f"[Glassdoor] Page {page_num}: found {len(cards)} cards, total jobs: {len(jobs)}")

                if len(jobs) >= self.max_results:
                    break

            except Exception as e:
                print(f"[Glassdoor] Error on page {page_num}: {e}")
                break

        print(f"[Glassdoor] Done. Total jobs found: {len(jobs)}")
        return jobs
