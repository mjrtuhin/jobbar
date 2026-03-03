# 🤖 JobHunter AI — Multi-Agent Job Application System

> A fully automated, AI-powered job hunting system built in Python (Jupyter Notebook) with a Streamlit dashboard. The system crawls the internet for jobs, tailors your CV and cover letter per job using LaTeX, and scores your likelihood of getting hired.

---

## 📐 System Architecture Overview

```
User Input (Streamlit Dashboard)
        │
        ▼
┌─────────────────────────────────┐
│     PHASE 1: JOB DISCOVERY      │
│  Agents 1–5 (Parallel Crawlers) │
│  LinkedIn, Indeed, Glassdoor,   │
│  Reed.co.uk + others            │
└────────────┬────────────────────┘
             │
             ▼
     Google Sheets (Output)
     Job Title, Company, URL,
     Location, Date Posted
             │
             ▼
┌─────────────────────────────────┐
│   PHASE 2: JOB DEEP-READING     │
│         Agent 6                 │
│  Reads each job URL → extracts  │
│  full requirements & details    │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   PHASE 3: CV & COVER LETTER    │
│         Agent 7                 │
│  Takes CV content + job details │
│  → Generates tailored CV &      │
│    Cover Letter in LaTeX        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   PHASE 4: FIT EVALUATION       │
│         Agent 8                 │
│  Scores your fit (0–100%) for   │
│  each job with reasoning        │
└────────────┬────────────────────┘
             │
             ▼
     Streamlit Dashboard
     View jobs, CVs, scores
```

---

## 🧩 Agent Breakdown

### 🔍 Agents 1–5 — Parallel Web Crawlers

**Role:** Crawl multiple job sites simultaneously and collect job listings based on user-defined criteria.

**Targets:**
- LinkedIn Jobs
- Indeed UK
- Glassdoor
- Reed.co.uk
- Any other available job boards

**Inputs (from Streamlit):**
- Job title / keyword (e.g. "Data Analyst", "Security Guard", "Receptionist" — anything)
- Location (default: UK, but user can override)
- Optional filters: salary range, job type (full-time/part-time), date posted

**Outputs → Google Sheet:**

| Column | Description |
|---|---|
| Job Title | Title of the role |
| Company | Employer name |
| Location | City / Remote |
| Salary | If listed |
| Date Posted | When it was posted |
| Job URL | Direct link to listing |
| Source | Which site it came from |
| Status | New / Processed / Applied |

**Technical approach:**
- Each agent runs as an async task using `asyncio` / `concurrent.futures`
- Uses `requests` + `BeautifulSoup4` for scraping, or site APIs where available
- Deduplication logic to avoid storing the same job twice
- Rate limiting + user-agent rotation to avoid being blocked
- Writes to Google Sheet via **Google Sheets API (API key auth)**

---

### 📋 Agent 6 — Job Requirements Extractor

**Role:** For each job URL stored in the spreadsheet, visit the page and extract the full job description and requirements.

**Inputs:**
- Google Sheet (reads all rows where Status = "New")

**Process:**
- Visits each job URL
- Extracts: full job description, required skills, nice-to-have skills, experience level, qualifications, responsibilities
- Uses Claude AI (via Anthropic API) to structure the raw text into clean, categorised requirements

**Outputs (written back to Google Sheet):**

| Column | Description |
|---|---|
| Required Skills | Hard requirements |
| Nice-to-Have | Bonus skills |
| Experience Needed | Years / level |
| Key Responsibilities | What you'll actually do |
| Keywords | Important terms for CV tailoring |

---

### 📄 Agent 7 — CV & Cover Letter Generator

**Role:** Generate a tailored CV and cover letter for each job, formatted professionally in LaTeX.

**Inputs:**
- User's base CV content (provided once, stored in config)
- Job requirements from Agent 6
- LaTeX template (user provides format preferences)

**Process:**
- Claude AI reads the job requirements and the user's CV
- Reorders and rewrites CV sections to highlight the most relevant experience for that specific job
- Writes a personalised cover letter addressing the job's key requirements
- Compiles LaTeX to PDF using `pdflatex`

**Outputs:**
- `CV_[JobTitle]_[Company].pdf`
- `CoverLetter_[JobTitle]_[Company].pdf`
- Both saved locally and linked in the Google Sheet

**LaTeX Quality Checks:**
- Correct page margins and layout
- Professional fonts (e.g. `\usepackage{lmodern}`)
- Consistent spacing and formatting
- No compilation errors

---

### 🎯 Agent 8 — Fit Evaluator

**Role:** Evaluate how well the user's profile matches each job and provide a likelihood score.

**Inputs:**
- User's CV content
- Job requirements from Agent 6
- Generated CV from Agent 7

**Process:**
- Claude AI compares the user's skills, experience, and qualifications against the job requirements
- Produces a structured evaluation report per job

**Sample Output:**
```
Job: Data Analyst @ KPMG London
─────────────────────────────────
Fit Score:        78 / 100
Likelihood:       High ✅

Matched Skills:   Python, SQL, Excel, Data Visualisation
Missing Skills:   Power BI, Azure
Experience Gap:   You have 2 years, they want 3+

Strengths:        Strong analytical background, relevant education
Weaknesses:       No mention of financial sector experience

Recommendation:   Apply — strong candidate. Emphasise your SQL
                  projects and add Power BI to your CV if possible.
```

---

## 🖥️ Streamlit Dashboard

**The control centre for the entire system.**

### Pages / Sections:

#### 1. 🔧 Configuration
- Enter Google Sheet link
- Enter Google API key + Anthropic API key
- Upload / paste CV content
- Set LaTeX template preferences
- Set default search location

#### 2. 🔍 Job Search
- Input: job title, keywords, location, filters
- Button: "Start Search" → triggers Agents 1–5
- Live progress bar showing crawling status
- Preview of jobs found

#### 3. 📊 Job Dashboard
- Table view of all jobs in Google Sheet
- Filter by: source, score, status, date
- Click any job to see full details, requirements, fit score

#### 4. 📄 CV & Cover Letters
- View generated CV and cover letter per job
- Download as PDF
- Regenerate with different tone/emphasis

#### 5. 📈 Analytics
- How many jobs found per site
- Average fit score
- Top skills you're missing across all jobs
- Best matching jobs ranked by score

---

## 🗂️ Project File Structure

```
jobhunter_ai/
│
├── JobHunter_AI.ipynb          # Main Jupyter Notebook (all agents)
│
├── config/
│   ├── config.json             # API keys, sheet ID, user preferences
│   └── cv_content.txt          # User's raw CV content
│
├── templates/
│   ├── cv_template.tex         # LaTeX CV template
│   └── cover_letter.tex        # LaTeX cover letter template
│
├── outputs/
│   ├── cvs/                    # Generated CV PDFs
│   └── cover_letters/          # Generated cover letter PDFs
│
├── dashboard/
│   └── app.py                  # Streamlit dashboard
│
└── requirements.txt            # Python dependencies
```

---

## 📦 Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Notebook | Jupyter Notebook |
| Web Scraping | `requests`, `BeautifulSoup4`, `playwright` |
| Async Crawling | `asyncio` / `concurrent.futures` |
| AI (all agents) | Anthropic Claude API (`claude-sonnet-4-20250514`) |
| Spreadsheet | Google Sheets API (API key) |
| CV Formatting | LaTeX (`pdflatex`) |
| Dashboard | Streamlit |
| PDF Generation | `pdflatex` via `subprocess` |
| Data Handling | `pandas` |

---

## 🔑 What You Need to Provide

Before running the system, you'll need:

1. **Google Sheet link** — publicly shared with editing permissions
2. **Google API key** — free from Google Cloud Console (Sheets API enabled)
3. **Anthropic API key** — for Claude AI (powers all 8 agents)
4. **Your CV content** — raw text of your experience, skills, education
5. **LaTeX template** — your preferred CV format (or use the default provided)

---

## 🚀 How It Works — Step by Step

1. Open `JobHunter_AI.ipynb` in Jupyter
2. Fill in your config (API keys, CV content, Sheet link) in **Cell 1**
3. Run **Phase 1** cells → 5 agents crawl job sites in parallel → jobs appear in your Google Sheet
4. Run **Phase 2** cell → Agent 6 visits every job URL and extracts full requirements
5. Run **Phase 3** cell → Agent 7 generates a tailored CV + cover letter in LaTeX for each job
6. Run **Phase 4** cell → Agent 8 scores every job and gives a hire recommendation
7. Open Streamlit: `streamlit run dashboard/app.py` → view everything in a clean UI

---

## ⚠️ Known Limitations & Notes

- **LinkedIn** heavily blocks scrapers — will use `playwright` headless browser + their public job search URL format
- **Google Sheets API key** allows reading public sheets freely; writing requires the sheet to be set to "Anyone with the link can edit"
- **LaTeX compilation** requires `pdflatex` installed locally (`apt install texlive-full` on Linux / MiKTeX on Windows)
- **Rate limiting** — crawlers include delays to avoid being blocked; very large searches may take several minutes
- This system is for **personal use** — always check a site's Terms of Service before scraping

---

## 📅 Build Order

| Phase | What gets built | Priority |
|---|---|---|
| 1 | Config setup + Google Sheets connection | First |
| 2 | Agents 1–5 crawlers (one site at a time, then parallelised) | Second |
| 3 | Agent 6 — requirements extractor | Third |
| 4 | Agent 7 — CV + cover letter in LaTeX | Fourth |
| 5 | Agent 8 — fit scorer | Fifth |
| 6 | Streamlit dashboard | Last |

---

*System designed based on user specification — March 2026*
