import subprocess
import os
import json
import re


class CVGenerator:
    """Agent: Generates tailored CVs and cover letters in LaTeX, compiled to PDF."""

    def __init__(self, ai_helper, config: dict):
        self.ai = ai_helper
        self.config = config
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cv_template_path = os.path.join(self.project_root, config["latex"]["cv_template"])
        self.cl_template_path = os.path.join(self.project_root, config["latex"]["cover_letter_template"])
        self.output_cvs = os.path.join(self.project_root, config["latex"]["output_dir_cvs"])
        self.output_cls = os.path.join(self.project_root, config["latex"]["output_dir_cover_letters"])

    def load_cv_content(self) -> str:
        cv_path = os.path.join(self.project_root, "config", "cv_content.txt")
        with open(cv_path, "r") as f:
            return f.read()

    def load_template(self, template_path: str) -> str:
        with open(template_path, "r") as f:
            return f.read()

    def sanitize_filename(self, text: str) -> str:
        clean = re.sub(r"[^\w\s-]", "", text)
        clean = re.sub(r"\s+", "_", clean.strip())
        return clean[:50]

    def escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters in text."""
        replacements = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}"
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text

    def build_professional_summary(self, summary_text: str) -> str:
        """Build the Professional Summary LaTeX block."""
        escaped = self.escape_latex(summary_text.strip())
        return (
            "\\noindent\n"
            "\\textbf{\\textcolor{sectioncolor}{Professional Summary}} \\\\\n"
            f"{escaped}\n"
        )

    def build_work_history(self, work_items: list) -> str:
        """Build the Work History LaTeX block.
        Each item: {title, company, dates, location, bullets: [str]}
        """
        lines = [
            "\\noindent\n",
            "\\textbf{\\textcolor{sectioncolor}{Work History}}\n",
            "\\begin{itemize}[leftmargin=*, label=\\textcolor{bulletcolor}{\\textbullet}]\n"
        ]
        for item in work_items:
            title = self.escape_latex(item.get("title", ""))
            company = self.escape_latex(item.get("company", ""))
            dates = self.escape_latex(item.get("dates", ""))
            loc = self.escape_latex(item.get("location", ""))
            lines.append(f"    \\item \\textbf{{{title}, {company}}} \\hfill \\textit{{{dates}, {loc}}}\n")
            bullets = item.get("bullets", [])
            if bullets:
                lines.append("    \\begin{itemize}\n")
                for b in bullets:
                    lines.append(f"        \\item {self.escape_latex(b)}\n")
                lines.append("    \\end{itemize}\n")
        lines.append("\\end{itemize}\n")
        return "".join(lines)

    def build_education(self, edu_items: list) -> str:
        """Build the Education LaTeX block."""
        lines = [
            "\\noindent\n",
            "\\textbf{\\textcolor{sectioncolor}{Education}}\n",
            "\\begin{itemize}[leftmargin=*, label=\\textcolor{bulletcolor}{\\textbullet}]\n"
        ]
        for item in edu_items:
            degree = self.escape_latex(item.get("degree", ""))
            dates = self.escape_latex(item.get("dates", ""))
            institution = self.escape_latex(item.get("institution", ""))
            bullets = item.get("bullets", [])
            lines.append(f"    \\item \\textbf{{{degree}}} \\hfill \\textit{{{dates}, {institution}}}\n")
            if bullets:
                lines.append("    \\begin{itemize}\n")
                for b in bullets:
                    lines.append(f"        \\item {self.escape_latex(b)}\n")
                lines.append("    \\end{itemize}\n")
        lines.append("\\end{itemize}\n")
        return "".join(lines)

    def build_skills(self, skills: list) -> str:
        """Build the Skills LaTeX block (3 columns)."""
        lines = [
            "\\noindent\n",
            "\\textbf{\\textcolor{sectioncolor}{Skills}}\n",
            "\\begin{multicols}{3}\n",
            "\\begin{itemize}[leftmargin=*, label=\\textcolor{bulletcolor}{\\textbullet}]\n"
        ]
        for skill in skills:
            lines.append(f"\\item {self.escape_latex(skill)}\n")
        lines.append("\\end{itemize}\n")
        lines.append("\\end{multicols}\n")
        return "".join(lines)

    def build_extracurricular(self, items: list) -> str:
        lines = [
            "\\noindent\n",
            "\\textbf{\\textcolor{sectioncolor}{Extracurricular Activities}}\n",
            "\\begin{itemize}[leftmargin=*, label=\\textcolor{bulletcolor}{\\textbullet}]\n"
        ]
        for item in items:
            lines.append(f"    \\item {self.escape_latex(item)}\n")
        lines.append("\\end{itemize}\n")
        return "".join(lines)

    def build_accomplishments(self, items: list) -> str:
        lines = [
            "\\noindent\n",
            "\\textbf{\\textcolor{sectioncolor}{Accomplishments}}\n",
            "\\begin{itemize}[leftmargin=*, label=\\textcolor{bulletcolor}{\\textbullet}]\n"
        ]
        for item in items:
            lines.append(f"    \\item {self.escape_latex(item)}\n")
        lines.append("\\end{itemize}\n")
        return "".join(lines)

    def fill_cv_template(self, template: str, sections: dict) -> str:
        """Fill the CV template with generated sections."""
        result = template
        result = result.replace("%%PROFESSIONAL_SUMMARY%%", sections.get("professional_summary", ""))
        result = result.replace("%%WORK_HISTORY%%", sections.get("work_history", ""))
        result = result.replace("%%EDUCATION%%", sections.get("education", ""))
        result = result.replace("%%SKILLS%%", sections.get("skills", ""))
        result = result.replace("%%EXTRACURRICULAR%%", sections.get("extracurricular", ""))
        result = result.replace("%%ACCOMPLISHMENTS%%", sections.get("accomplishments", ""))
        return result

    def fill_cover_letter_template(self, template: str, cover_letter_text: str, job_title: str, company: str) -> str:
        result = template
        result = result.replace("%%COVER_LETTER_CONTENT%%", self.escape_latex(cover_letter_text))
        result = result.replace("%%JOB_TITLE%%", self.escape_latex(job_title))
        result = result.replace("%%COMPANY%%", self.escape_latex(company))
        return result

    def compile_latex(self, tex_content: str, output_path: str) -> bool:
        tex_file = output_path.replace(".pdf", ".tex")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(tex_file, "w") as f:
            f.write(tex_content)

        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", os.path.dirname(output_path), tex_file],
                capture_output=True, text=True, timeout=30
            )
            if os.path.exists(output_path):
                for ext in [".aux", ".log", ".out"]:
                    cleanup = output_path.replace(".pdf", ext)
                    if os.path.exists(cleanup):
                        os.remove(cleanup)
                print(f"[CVGen] PDF created: {output_path}")
                return True
            else:
                print(f"[CVGen] LaTeX compilation failed. Check {tex_file}")
                if result.stderr:
                    print(f"[CVGen] Error: {result.stderr[:500]}")
                return False
        except subprocess.TimeoutExpired:
            print(f"[CVGen] LaTeX compilation timed out for {tex_file}")
            return False
        except FileNotFoundError:
            print("[CVGen] pdflatex not found. Install texlive: apt install texlive-full")
            return False

    def generate_cv_sections(self, cv_content: str, job_description: str, job_title: str, company: str) -> dict:
        """Ask AI to return a JSON with CV sections tailored to the job."""
        system_prompt = (
            "You are a professional CV writer. Given the candidate's CV and a job description, "
            "return a JSON object with these exact keys:\n"
            "- professional_summary: A 3-4 sentence summary tailored to the job.\n"
            "- work_history: A list of objects with keys: title, company, dates, location, bullets (list of 3-4 achievement strings).\n"
            "- education: A list of objects with keys: degree, dates, institution, bullets (list of 1-2 detail strings, can be empty).\n"
            "- skills: A flat list of 12-16 skill strings relevant to the job.\n"
            "- extracurricular: A flat list of 2-3 strings.\n"
            "- accomplishments: A flat list of 3-5 strings.\n\n"
            "IMPORTANT: Keep all factual information accurate. Do not invent experience or qualifications. "
            "Reorder and emphasize items that match the job description. "
            "Return ONLY valid JSON, nothing else."
        )

        user_message = (
            f"Candidate CV:\n{cv_content}\n\n"
            f"Job posting for {job_title} at {company}:\n{job_description}\n\n"
            "Return the tailored JSON."
        )

        result = self.ai.chat(system_prompt, user_message, temperature=0.4)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(result[start:end])
                except json.JSONDecodeError:
                    pass
            print("[CVGen] AI did not return valid JSON, using fallback")
            return None

    def generate_for_job(self, job_title: str, company: str, job_description: str, cv_content: str = None) -> dict:
        """Generate a tailored CV and cover letter for a single job."""
        if cv_content is None:
            cv_content = self.load_cv_content()

        safe_name = self.sanitize_filename(f"{job_title}_{company}")
        print(f"[CVGen] Generating documents for: {job_title} at {company}")

        cv_sections_data = self.generate_cv_sections(cv_content, job_description, job_title, company)

        cv_success = False
        cv_pdf_path = os.path.join(self.output_cvs, f"CV_{safe_name}.pdf")

        if cv_sections_data:
            sections_latex = {
                "professional_summary": self.build_professional_summary(
                    cv_sections_data.get("professional_summary", "")
                ),
                "work_history": self.build_work_history(
                    cv_sections_data.get("work_history", [])
                ),
                "education": self.build_education(
                    cv_sections_data.get("education", [])
                ),
                "skills": self.build_skills(
                    cv_sections_data.get("skills", [])
                ),
                "extracurricular": self.build_extracurricular(
                    cv_sections_data.get("extracurricular", [])
                ),
                "accomplishments": self.build_accomplishments(
                    cv_sections_data.get("accomplishments", [])
                )
            }

            cv_template = self.load_template(self.cv_template_path)
            cv_latex = self.fill_cv_template(cv_template, sections_latex)
            cv_success = self.compile_latex(cv_latex, cv_pdf_path)

        cover_letter = self.ai.write_cover_letter(cv_content, job_description, job_title, company)
        cl_template = self.load_template(self.cl_template_path)
        cl_latex = self.fill_cover_letter_template(cl_template, cover_letter, job_title, company)
        cl_pdf_path = os.path.join(self.output_cls, f"CoverLetter_{safe_name}.pdf")
        cl_success = self.compile_latex(cl_latex, cl_pdf_path)

        return {
            "cv_path": cv_pdf_path if cv_success else "",
            "cover_letter_path": cl_pdf_path if cl_success else "",
            "cv_success": cv_success,
            "cl_success": cl_success
        }

    def process_selected_jobs(self, sheets_manager, row_indices: list) -> int:
        if not row_indices:
            return 0

        df = sheets_manager.get_all_jobs()
        cv_content = self.load_cv_content()
        generated_count = 0

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
                print(f"[CVGen] Skipping '{job_title}' (no job description available)")
                continue

            result = self.generate_for_job(job_title, company, description, cv_content)

            updates = {
                "CV Path": result["cv_path"],
                "Cover Letter Path": result["cover_letter_path"],
                "Status": "CV Ready"
            }
            sheets_manager.update_job_row(row_index, updates)
            generated_count += 1

        print(f"[CVGen] Done. Generated documents for {generated_count} jobs.")
        return generated_count
