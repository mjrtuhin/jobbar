# JobHunter AI -- Multi-Agent Job Application System

> A fully automated, AI-powered job hunting system built in Python with a Streamlit dashboard. The system crawls the internet for jobs, tailors your CV and cover letter per job using LaTeX, and scores your likelihood of getting hired.

---

## System Architecture Overview

```
User Input (Streamlit Dashboard)
        |
        v
+-------------------------------+
|     PHASE 1: JOB DISCOVERY    |
|  Parallel Crawlers            |
|  LinkedIn, Indeed, Reed       |
+---------------+---------------+
                |
                v
        Excel Database
        Job Title, Company, URL,
        Location, Date Posted
                |
                v
+-------------------------------+
|   PHASE 2: CV & COVER LETTER  |
|   CV Generator Agent          |
|   Takes CV content + job desc |
|   -> Generates tailored CV &  |
|      Cover Letter in LaTeX    |
+---------------+---------------+
                |
                v
+-------------------------------+
|   PHASE 3: FIT EVALUATION     |
|   Fit Evaluator Agent         |
|   Scores your fit (0-100%)    |
|   for each job with reasoning |
+---------------+---------------+
                |
                v
        Streamlit Dashboard
        View jobs, CVs, scores
```

---

## Agent Breakdown

### Agents 1-3 -- Parallel Web Crawlers

**Role:** Crawl multiple job sites simultaneously and collect job listings based on user-defined criteria.

**Targets:**
- LinkedIn Jobs
- Indeed UK
- Reed.co.uk

**Inputs (from Streamlit):**
- Job title / keyword (e.g. "Data Analyst", "Security Guard", "Receptionist")
- Location (default: UK, but user can override)
- Optional filters: salary range, job type (full-time/part-time), date posted

**Outputs (Excel Database):**

| Column | Description |
|---|---|
| Job Title | Title of the role |
| Company | Employer name |
| Location | City / Remote |
| Salary | If listed |
| Date Posted | When it was posted |
| Job URL | Direct link to listing |
| Source | Which site it came from |
| Status | New / CV Ready / Applied |
| Description | Full job description |
| Job Type | Full-time / Part-time / Contract |
| Remote | Remote status |

**Technical approach:**
- Each crawler runs as a parallel task using `concurrent.futures.ThreadPoolExecutor`
- Uses `python-jobspy` for Indeed and LinkedIn, custom `BeautifulSoup4` scraper for Reed
- Deduplication logic to avoid storing the same job twice
- Rate limiting + user-agent rotation to avoid being blocked
- Writes to local Excel file via `openpyxl` + `pandas`

---

### CV Generator Agent

**Role:** Generate a tailored CV and cover letter for each job, formatted professionally in LaTeX.

**Inputs:**
- User's base CV content (stored in `config/cv_content.txt`)
- User's profile (stored in `config/profile.json`)
- Job description from the database
- LaTeX templates

**Process:**
- AI reads the job description and the user's CV
- Reorders and rewrites CV sections to highlight the most relevant experience
- Generates a personalised cover letter addressing the job's key requirements
- Compiles LaTeX to PDF using `pdflatex`
- Falls back to `.tex` file if PDF compilation fails

**Outputs:**
- `CV_[JobTitle]_[Company].pdf`
- `CoverLetter_[JobTitle]_[Company].pdf`
- Both saved locally and linked in the database

---

### Fit Evaluator Agent

**Role:** Evaluate how well the user's profile matches each job and provide a likelihood score.

**Inputs:**
- User's CV content
- Job description

**Process:**
- AI compares the user's skills, experience, and qualifications against the job requirements
- Produces a structured JSON evaluation

**Sample Output:**
```
Job: Data Analyst @ KPMG London
---------------------------------
Fit Score:        78 / 100
Likelihood:       High

Matched Skills:   Python, SQL, Excel, Data Visualisation
Missing Skills:   Power BI, Azure
Experience Gap:   You have 2 years, they want 3+

Strengths:        Strong analytical background, relevant education
Weaknesses:       No mention of financial sector experience

Recommendation:   Apply -- strong candidate. Emphasise your SQL
                  projects and add Power BI to your CV if possible.
```

---

## Streamlit Dashboard

**The control centre for the entire system.**

### Pages:

#### 1. Home
- System overview and quick statistics
- Total jobs collected, CVs generated, average fit score

#### 2. My Profile
- Edit personal details: name, email, phone, location
- Manage languages, community service, references
- All generated documents use this profile data

#### 3. Job Search
- Input: job title, keywords, location, filters
- Select which crawlers to use (Indeed, LinkedIn, Reed)
- Live progress during crawling

#### 4. My Jobs
- Table view of all jobs in the database
- Filter by source, status, job type
- Select jobs for CV generation
- View full job details and descriptions

#### 5. Click to Apply
- Select a job from the dropdown
- Four tabs:
  - **CV Preview**: View and download tailored CV (PDF or LaTeX)
  - **Cover Letter**: View and download cover letter (PDF or LaTeX)
  - **Fit Evaluation**: AI compatibility score with detailed breakdown
  - **Apply by Email**: AI-generated application email with mailto link and .eml download

#### 6. Analytics
- Job distribution by source
- Status breakdown
- Salary and location analysis

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Web Scraping | python-jobspy, BeautifulSoup4, requests |
| Parallel Crawling | concurrent.futures (ThreadPoolExecutor) |
| AI Backend | Groq API (Llama 3.3 70B) via OpenAI-compatible client |
| Data Storage | Local Excel (.xlsx) via openpyxl + pandas |
| CV Formatting | LaTeX (pdflatex) |
| Dashboard | Streamlit |
| PDF Generation | pdflatex via subprocess |

---

## What You Need

Before running the system, you need:

1. **Groq API key** -- free from [console.groq.com](https://console.groq.com)
2. **Your CV content** -- raw text of your experience, skills, education
3. **Your profile details** -- name, contact info, languages, references
4. **LaTeX distribution** -- for PDF compilation (or use .tex files directly)

---

## How It Works -- Step by Step

1. Set up your `.env` with your Groq API key
2. Edit `config/cv_content.txt` with your base CV
3. Fill in `config/profile.json` with your personal details (or use the dashboard)
4. Run the dashboard: `streamlit run dashboard/app.py`
5. Search for jobs on the **Job Search** page
6. Select jobs and generate tailored CVs on the **My Jobs** page
7. Review CVs, cover letters, fit scores, and apply via the **Click to Apply** page

---

## Known Limitations & Notes

- **LinkedIn** may block some description fetching -- the system enables `linkedin_fetch_description` but some listings may return empty descriptions
- **LaTeX compilation** requires `pdflatex` installed locally; if not available, `.tex` files are saved instead
- **Rate limiting** -- crawlers include delays to avoid being blocked; large searches may take several minutes
- This system is for **personal use** -- always check a site's Terms of Service before scraping

---

*System designed and built -- March 2026*
