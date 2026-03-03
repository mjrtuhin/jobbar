import requests
from bs4 import BeautifulSoup
import json
import time
import random


class RequirementsExtractor:
    """Agent: Visits each job URL and extracts structured requirements using AI."""

    def __init__(self, ai_helper, config: dict):
        self.ai = ai_helper
        self.config = config
        self.user_agents = config["crawlers"]["user_agents"]
        self.rate_limit = config["crawlers"]["rate_limit_seconds"]

    def get_headers(self) -> dict:
        """Return request headers with a random user agent."""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9"
        }

    def fetch_job_description(self, url: str) -> str:
        """Fetch the full text content from a job listing URL (fallback only)."""
        try:
            time.sleep(self.rate_limit)
            response = requests.get(url, headers=self.get_headers(), timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()

            main_content = soup.find("main")
            if not main_content:
                main_content = soup.find("article")
            if not main_content:
                main_content = soup.find("div", class_="jobsearch-jobDescriptionText")
            if not main_content:
                main_content = soup.find("div", id="job-description")
            if not main_content:
                main_content = soup.find("div", class_="description")
            if not main_content:
                main_content = soup.body

            if main_content:
                text = main_content.get_text(separator="\n", strip=True)
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                return "\n".join(lines[:200])

            return ""

        except Exception as e:
            print(f"[Extractor] Failed to fetch {url}: {e}")
            return ""

    def extract_requirements(self, job_description: str) -> dict:
        """Use AI to structure a raw job description into categorised requirements."""
        if not job_description or len(job_description) < 50:
            return {
                "required_skills": [],
                "nice_to_have": [],
                "experience_needed": "",
                "key_responsibilities": [],
                "keywords": []
            }

        return self.ai.extract_job_requirements(job_description)

    def process_job(self, job_url: str, stored_description: str = "") -> dict:
        """Full pipeline: use stored description or fetch URL, then extract requirements."""
        print(f"[Extractor] Processing: {job_url}")

        description = stored_description.strip() if stored_description else ""

        if not description or len(description) < 50:
            print(f"[Extractor] No stored description, trying to fetch URL...")
            description = self.fetch_job_description(job_url)

        if not description:
            print(f"[Extractor] No content found for: {job_url}")
            return {}

        requirements = self.extract_requirements(description)
        print(f"[Extractor] Extracted {len(requirements.get('required_skills', []))} required skills")
        return requirements

    def process_jobs_from_sheet(self, sheets_manager) -> int:
        """Process all 'New' jobs from the local Excel file."""
        new_jobs = sheets_manager.get_jobs_by_status("New")
        if new_jobs.empty:
            print("[Extractor] No new jobs to process.")
            return 0

        processed_count = 0

        for idx, row in new_jobs.iterrows():
            job_url = row.get("Job URL", "")
            if not job_url:
                continue

            stored_desc = str(row.get("Description", ""))
            if stored_desc == "nan":
                stored_desc = ""

            requirements = self.process_job(job_url, stored_desc)
            if not requirements:
                continue

            row_index = sheets_manager.find_job_row(job_url)
            if row_index < 0:
                continue

            updates = {
                "Required Skills": ", ".join(requirements.get("required_skills", [])),
                "Nice-to-Have": ", ".join(requirements.get("nice_to_have", [])),
                "Experience Needed": requirements.get("experience_needed", ""),
                "Key Responsibilities": ", ".join(requirements.get("key_responsibilities", [])),
                "Keywords": ", ".join(requirements.get("keywords", [])),
                "Status": "Processed"
            }

            sheets_manager.update_job_row(row_index, updates)
            processed_count += 1
            print(f"[Extractor] Updated row {row_index}")

        print(f"[Extractor] Done. Processed {processed_count} jobs.")
        return processed_count

    def process_selected_jobs(self, sheets_manager, row_indices: list) -> int:
        """Process specific jobs by their row indices."""
        if not row_indices:
            return 0

        df = sheets_manager.get_all_jobs()
        processed_count = 0

        for row_index in row_indices:
            if row_index < 0 or row_index >= len(df):
                continue

            row = df.iloc[row_index]
            job_url = str(row.get("Job URL", ""))
            if not job_url:
                continue

            stored_desc = str(row.get("Description", ""))
            if stored_desc == "nan":
                stored_desc = ""

            requirements = self.process_job(job_url, stored_desc)
            if not requirements:
                continue

            updates = {
                "Required Skills": ", ".join(requirements.get("required_skills", [])),
                "Nice-to-Have": ", ".join(requirements.get("nice_to_have", [])),
                "Experience Needed": requirements.get("experience_needed", ""),
                "Key Responsibilities": ", ".join(requirements.get("key_responsibilities", [])),
                "Keywords": ", ".join(requirements.get("keywords", [])),
                "Status": "Processed"
            }

            sheets_manager.update_job_row(row_index, updates)
            processed_count += 1
            print(f"[Extractor] Updated row {row_index}")

        print(f"[Extractor] Done. Processed {processed_count} jobs.")
        return processed_count
