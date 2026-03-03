# Jobbar - Multi-Agent AI Job Hunting System

Jobbar is an intelligent, multi-agent job hunting platform that automates the entire job application pipeline. It crawls multiple job boards simultaneously, stores results in a structured Excel database, and leverages AI agents to generate tailored CVs, cover letters, fit evaluations, and application emails for each position.

Built with Python and powered by a Streamlit dashboard, Jobbar provides a complete end-to-end solution for job seekers who want to apply smarter, not harder.

---

## Features

**Automated Job Crawling**
Searches Indeed, LinkedIn, and Reed in parallel using multi-threaded execution. Deduplicates listings automatically and stores all results with full metadata including job descriptions, salary data, and posting dates.

**AI-Powered CV Generation**
Uses a LaTeX-based template system to produce professionally formatted, ATS-friendly CVs. The AI analyses each job description and restructures the candidate's experience, skills, and accomplishments to maximise relevance for the specific role.

**Personalised Cover Letters**
Generates tailored cover letters for every application, compiled into clean PDF documents via LaTeX. Each letter addresses the specific requirements of the role and highlights matching qualifications.

**Job Fit Evaluation**
An AI agent scores compatibility (0-100) between the candidate's profile and each job posting. It identifies matched skills, missing skills, experience gaps, strengths, weaknesses, and provides a hiring likelihood assessment.

**Custom Application Emails**
Generates concise, professional application emails with references to the attached CV and cover letter. Supports both mailto links and downloadable .eml files with MIME attachments.

**User Profile System**
Fully customisable profile system where users input their personal details, languages, community service, and references. All generated documents pull from this profile, making the system usable by anyone.

**Interactive Dashboard**
A polished 6-page Streamlit dashboard with:
- Home: System overview and quick stats
- My Profile: Edit personal details used across all documents
- Job Search: Configure and launch multi-site crawls
- My Jobs: Browse, filter, and manage all collected listings
- Click to Apply: Generate and preview CVs, cover letters, fit evaluations, and emails
- Analytics: Visual breakdown of job data by source, type, and status

---

## Project Architecture

```
jobbar/
├── dashboard/
│   └── app.py                  # Streamlit dashboard (6 pages)
├── agents/
│   ├── cv_generator.py         # CV + cover letter generation agent
│   ├── fit_evaluator.py        # Job fit scoring agent
│   └── requirements_extractor.py
├── crawlers/
│   ├── runner.py               # Parallel crawler orchestrator
│   ├── reed_crawler.py         # Reed.co.uk crawler
│   ├── indeed_crawler.py       # Indeed crawler (via JobSpy)
│   ├── linkedin_crawler.py     # LinkedIn crawler (via JobSpy)
│   ├── base_crawler.py         # Base crawler class
│   ├── adzuna_crawler.py       # Adzuna crawler
│   └── glassdoor_crawler.py    # Glassdoor crawler
├── templates/
│   ├── cv_template.tex         # LaTeX CV template with placeholders
│   └── cover_letter.tex        # LaTeX cover letter template
├── config/
│   ├── config.json             # System configuration
│   ├── profile.json            # User profile data
│   └── cv_content.txt          # Base CV content for AI processing
├── data/
│   └── jobs.xlsx               # Job database (auto-generated)
├── outputs/
│   ├── cvs/                    # Generated CV PDFs and .tex files
│   └── cover_letters/          # Generated cover letter PDFs and .tex files
├── ai_helper.py                # AI client (OpenAI-compatible API wrapper)
├── sheets_manager.py           # Excel database manager
├── requirements.txt            # Python dependencies
└── .env                        # API keys (not tracked in git)
```

---

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Dashboard | Streamlit |
| AI Backend | Groq API (Llama 3.3 70B) via OpenAI-compatible client |
| Job Scraping | python-jobspy, BeautifulSoup4, requests |
| Document Generation | LaTeX (pdflatex) |
| Data Storage | Excel (.xlsx) via openpyxl + pandas |
| Concurrency | concurrent.futures (ThreadPoolExecutor) |

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A free Groq API key (get one at [console.groq.com](https://console.groq.com))
- LaTeX distribution for PDF generation:
  - **macOS**: `brew install basictex`
  - **Ubuntu/Debian**: `sudo apt install texlive-full`
  - **Windows**: Install [MiKTeX](https://miktex.org/download)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/mjrtuhin/jobbar.git
cd jobbar
```

2. **Create a virtual environment (recommended)**

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up your API key**

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

5. **Add your CV content**

Edit `config/cv_content.txt` with your base CV information. This is the raw text the AI uses to generate tailored versions.

6. **Set up your profile**

Edit `config/profile.json` with your personal details:

```json
{
    "full_name": "Your Full Name",
    "email": "your.email@example.com",
    "phone": "+44 1234 567890",
    "location": "Your City, Country",
    "languages": [
        {"language": "English", "level": "Native"}
    ],
    "community_service": [
        "Volunteer, Organisation Name, 2020-2023"
    ],
    "references": [
        {
            "name": "Reference Name",
            "title": "Job Title, Company",
            "phone": "+44 1234 567890",
            "email": "reference@example.com",
            "relationship": "Professional"
        }
    ]
}
```

Alternatively, you can fill in your profile through the dashboard's **My Profile** page.

### Running the Dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`.

---

## Usage Guide

### 1. Search for Jobs
Navigate to **Job Search**, enter a job title and location, select which job boards to crawl (Indeed, LinkedIn, Reed), and click Search. Results are saved to the Excel database automatically.

### 2. Review Listings
Go to **My Jobs** to browse all collected listings. You can view job details, filter by source, and select jobs for CV generation.

### 3. Generate Application Documents
Select jobs and click **Generate CV**. The system will:
- Analyse each job description
- Restructure your CV to highlight relevant experience
- Generate a matching cover letter
- Compile both into PDF via LaTeX

### 4. Apply to Jobs
Visit **Click to Apply** to:
- Preview and download your tailored CV (PDF or LaTeX)
- Preview and download the cover letter
- View AI fit evaluation with compatibility score
- Generate and send a custom application email

---

## Configuration

The `config/config.json` file controls system behaviour:

```json
{
    "ai_provider": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "provider": "groq"
    },
    "search_defaults": {
        "location": "United Kingdom",
        "job_type": "full-time",
        "date_posted": "past_week"
    },
    "crawlers": {
        "max_results_per_site": 500,
        "rate_limit_seconds": 2
    }
}
```

The AI backend uses an OpenAI-compatible API interface, so you can swap to any compatible provider by changing the `base_url` and `model` fields.

---

## LaTeX Setup Notes

If PDF compilation fails, the system will still save the `.tex` file so you can compile it manually or download it directly.

**macOS users**: After installing basictex, you may need to install additional LaTeX packages:

```bash
sudo tlmgr update --self
sudo tlmgr install enumitem fontawesome5 xcolor hyperref geometry multicol
```

If `tlmgr` is not found, run:
```bash
eval "$(/usr/libexec/path_helper)"
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| API returns 401 error | Check that your `GROQ_API_KEY` in `.env` is valid |
| LinkedIn descriptions are empty | This is expected for some listings; the system uses `linkedin_fetch_description=True` but LinkedIn may block some requests |
| pdflatex not found | Install a LaTeX distribution (see Prerequisites) |
| PDF won't open | Check the `.tex` file in `outputs/` for LaTeX errors; you can compile it manually |
| No jobs found | Try broader search terms or different job boards |

---

## Contributing

Contributions are welcome. Please open an issue first to discuss proposed changes.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "Add your feature"`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

This project is developed as an academic project. All rights reserved.

---

## Author

**Md Julfikar Rahman Tuhin**
- GitHub: [@mjrtuhin](https://github.com/mjrtuhin)
