from openai import OpenAI
import json


class AIHelper:
    """Handles all AI-powered tasks using Moonshot Kimi API (OpenAI-compatible)."""

    def __init__(self, api_key: str, base_url: str = "https://api.moonshot.cn/v1", model: str = "moonshot-v1-8k"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        """Send a message to the AI and get a response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content

    def tailor_cv(self, cv_content: str, job_description: str, job_title: str, company: str) -> str:
        """Rewrite CV content to match a specific job description."""
        system_prompt = (
            "You are a professional CV writer. Rewrite the given CV content to highlight "
            "the most relevant skills and experience for the target job. "
            "Keep all factual information accurate. Do not invent experience. "
            "Return the rewritten CV content as plain text, structured with clear sections."
        )

        user_message = (
            f"Here is the candidate's CV:\n\n{cv_content}\n\n"
            f"Here is the job posting for {job_title} at {company}:\n\n{job_description}\n\n"
            "Rewrite the CV to best match this job."
        )

        return self.chat(system_prompt, user_message, temperature=0.5)

    def write_cover_letter(self, cv_content: str, job_description: str, job_title: str, company: str) -> str:
        """Generate a personalised cover letter for a specific job."""
        system_prompt = (
            "You are a professional cover letter writer. Write a compelling, personalised "
            "cover letter that addresses the specific job requirements. "
            "Keep it professional, concise (under 400 words), and genuine. "
            "Do not use generic filler phrases."
        )

        user_message = (
            f"Write a cover letter for the following:\n\n"
            f"Position: {job_title} at {company}\n\n"
            f"Candidate CV:\n{cv_content}\n\n"
            f"Job Posting:\n{job_description}"
        )

        return self.chat(system_prompt, user_message, temperature=0.6)

    def write_application_email(self, job_title: str, company: str, candidate_name: str) -> str:
        """Generate a short 3-4 line application email body."""
        system_prompt = (
            "You are a professional email writer. Write a very short application email (3-4 lines only). "
            "Be direct and professional. Do not include subject line. "
            "Mention the attached CV and cover letter. Keep it under 60 words."
        )

        user_message = (
            f"Write a short email body for applying to {job_title} at {company}. "
            f"The candidate's name is {candidate_name}."
        )

        return self.chat(system_prompt, user_message, temperature=0.5)

    def evaluate_fit(self, cv_content: str, job_description: str, job_title: str, company: str) -> dict:
        """Score how well the candidate matches a job. Returns structured evaluation."""
        system_prompt = (
            "You are a recruitment analyst. Evaluate how well a candidate matches a job. "
            "Respond in valid JSON with these keys: "
            "fit_score (integer 0 to 100), likelihood (string: Low/Medium/High), "
            "matched_skills (list), missing_skills (list), experience_gap (string), "
            "strengths (list), weaknesses (list), recommendation (string)."
        )

        user_message = (
            f"Candidate CV:\n{cv_content}\n\n"
            f"Job Posting for {job_title} at {company}:\n{job_description}\n\n"
            "Evaluate the fit."
        )

        result = self.chat(system_prompt, user_message, temperature=0.3)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(result[start:end])
            return {"fit_score": 0, "likelihood": "Unknown", "recommendation": "Could not evaluate."}


def init_ai(config_path: str = "config/config.json") -> AIHelper:
    """Quick helper to load config and return an AIHelper instance."""
    from sheets_manager import load_config
    config = load_config(config_path)

    ai_config = config["ai_provider"]
    return AIHelper(
        api_key=ai_config["api_key"],
        base_url=ai_config["base_url"],
        model=ai_config["model"]
    )
