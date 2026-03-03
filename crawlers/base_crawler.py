import requests
from bs4 import BeautifulSoup
import random
import time
import json


class BaseCrawler:
    """Base class for all job board crawlers."""

    def __init__(self, config: dict):
        self.config = config
        self.rate_limit = config["crawlers"]["rate_limit_seconds"]
        self.max_results = config["crawlers"]["max_results_per_site"]
        self.user_agents = config["crawlers"]["user_agents"]
        self.source_name = "Unknown"

    def get_headers(self) -> dict:
        """Return request headers with a random user agent."""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

    def fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch a URL and return parsed HTML."""
        time.sleep(self.rate_limit)
        response = requests.get(url, headers=self.get_headers(), timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def search(self, job_title: str, location: str, **filters) -> list:
        """Override in each crawler. Returns list of job dicts."""
        raise NotImplementedError("Each crawler must implement search()")

    def build_job_dict(self, title, company, location, salary, date_posted, job_url) -> dict:
        """Create a standardised job dictionary."""
        return {
            "Job Title": title.strip() if title else "",
            "Company": company.strip() if company else "",
            "Location": location.strip() if location else "",
            "Salary": salary.strip() if salary else "",
            "Date Posted": date_posted.strip() if date_posted else "",
            "Job URL": job_url.strip() if job_url else "",
            "Source": self.source_name,
            "Status": "New"
        }
