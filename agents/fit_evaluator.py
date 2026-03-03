import json


class FitEvaluator:
    """Agent: Scores how well the candidate matches each job."""

    def __init__(self, ai_helper, config: dict):
        self.ai = ai_helper
        self.config = config

    def load_cv_content(self, cv_path: str = "config/cv_content.txt") -> str:
        """Load the user's raw CV content."""
        with open(cv_path, "r") as f:
            return f.read()

    def evaluate_single_job(self, cv_content: str, job_description: str, job_title: str, company: str) -> dict:
        """Evaluate fit for a single job. Returns structured evaluation."""
        return self.ai.evaluate_fit(cv_content, job_description, job_title, company)

    def process_selected_jobs(self, sheets_manager, row_indices: list) -> int:
        """Evaluate fit for specific jobs by row index."""
        if not row_indices:
            return 0

        df = sheets_manager.get_all_jobs()
        cv_content = self.load_cv_content()
        evaluated_count = 0

        for row_index in row_indices:
            if row_index < 0 or row_index >= len(df):
                continue

            row = df.iloc[row_index]
            job_title = str(row.get("Job Title", ""))
            company = str(row.get("Company", ""))
            description = str(row.get("Description", ""))

            if description == "nan":
                description = ""

            if not description or len(description) < 30:
                print(f"[FitEval] Skipping '{job_title}' (no job description available)")
                continue

            print(f"[FitEval] Evaluating: {job_title} at {company}")
            evaluation = self.evaluate_single_job(cv_content, description, job_title, company)

            updates = {
                "Fit Score": str(evaluation.get("fit_score", 0)),
                "Fit Summary": json.dumps(evaluation)
            }
            sheets_manager.update_job_row(row_index, updates)
            evaluated_count += 1

        print(f"[FitEval] Done. Evaluated {evaluated_count} jobs.")
        return evaluated_count
