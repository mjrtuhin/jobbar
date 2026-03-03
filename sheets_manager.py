import json
import os
import pandas as pd
from openpyxl import load_workbook


SHEET_COLUMNS = [
    "Job Title",
    "Company",
    "Location",
    "Salary",
    "Date Posted",
    "Job URL",
    "Source",
    "Status",
    "Description",
    "Job Type",
    "Remote",
    "Fit Score",
    "Fit Summary",
    "CV Path",
    "Cover Letter Path"
]


class SheetsManager:
    """Handles all read/write operations using a local Excel file."""

    def __init__(self, file_path: str = "data/jobs.xlsx"):
        self.file_path = file_path
        self.df = None

    def connect(self):
        """Load the Excel file, or create it if it does not exist."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        if os.path.exists(self.file_path):
            self.df = pd.read_excel(self.file_path, engine="openpyxl")
            for col in SHEET_COLUMNS:
                if col not in self.df.columns:
                    self.df[col] = ""
        else:
            self.df = pd.DataFrame(columns=SHEET_COLUMNS)
            self._save()

        print(f"Connected to local file: {self.file_path} ({len(self.df)} jobs)")

    def _save(self):
        """Write the current DataFrame back to the Excel file."""
        self.df.to_excel(self.file_path, index=False, engine="openpyxl")

    def get_all_jobs(self) -> pd.DataFrame:
        """Return all jobs as a DataFrame."""
        if self.df is None:
            return pd.DataFrame(columns=SHEET_COLUMNS)
        return self.df.copy()

    def get_jobs_by_status(self, status: str) -> pd.DataFrame:
        """Get all jobs with a specific status (e.g. 'New', 'Processed')."""
        if self.df is None or self.df.empty:
            return pd.DataFrame(columns=SHEET_COLUMNS)
        return self.df[self.df["Status"] == status].copy()

    def add_job(self, job_data: dict):
        """Add a single job row."""
        row = {}
        for col in SHEET_COLUMNS:
            row[col] = job_data.get(col, "")
        new_row = pd.DataFrame([row])
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self._save()

    def add_jobs_batch(self, jobs: list):
        """Add multiple job rows at once."""
        rows = []
        for job in jobs:
            row = {}
            for col in SHEET_COLUMNS:
                row[col] = job.get(col, "")
            rows.append(row)
        if rows:
            new_rows = pd.DataFrame(rows)
            self.df = pd.concat([self.df, new_rows], ignore_index=True)
            self._save()

    def update_job_row(self, row_index: int, updates: dict):
        """Update specific columns in a given row. row_index is 0-based DataFrame index."""
        for col_name, value in updates.items():
            if col_name in SHEET_COLUMNS and row_index < len(self.df):
                self.df.at[row_index, col_name] = value
        self._save()

    def find_job_row(self, job_url: str) -> int:
        """Find the row index of a job by its URL. Returns -1 if not found."""
        if self.df is None or self.df.empty:
            return -1
        matches = self.df[self.df["Job URL"] == job_url]
        if matches.empty:
            return -1
        return matches.index[0]

    def is_duplicate(self, job_url: str) -> bool:
        """Check if a job URL already exists."""
        return self.find_job_row(job_url) >= 0

    def get_row_count(self) -> int:
        """Get total number of job rows."""
        if self.df is None:
            return 0
        return len(self.df)


def load_config(config_path: str = "config/config.json") -> dict:
    """Load configuration from the JSON file, with .env overrides for secrets."""
    from dotenv import load_dotenv
    load_dotenv()

    with open(config_path, "r") as f:
        config = json.load(f)

    env_api_key = os.getenv("MOONSHOT_API_KEY")
    if env_api_key:
        config["ai_provider"]["api_key"] = env_api_key

    return config


def init_sheets(config_path: str = "config/config.json") -> SheetsManager:
    """Quick helper to load config and return a connected SheetsManager."""
    config = load_config(config_path)
    file_path = config.get("storage", {}).get("file_path", "data/jobs.xlsx")
    manager = SheetsManager(file_path=file_path)
    manager.connect()
    return manager
