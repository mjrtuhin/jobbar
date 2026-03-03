# JobHunter AI - Build Progress

## Project Overview
Multi-agent AI-powered job hunting system. Crawls job boards, tailors CVs and cover letters via LaTeX, scores job fit.

## Build Log

### Step 1 - Progress File Created
- Created this file to track all build progress.
- Date: March 3, 2026

### Step 2 - Project Folder Structure Created
- config/
- templates/
- outputs/cvs/
- outputs/cover_letters/
- dashboard/

### Step 3 - requirements.txt Created
- requests, beautifulsoup4, playwright, openai, gspread, google-auth, pandas, streamlit, python-dotenv, lxml

### Step 4 - config.json Created
- Placeholder config with sections for: google_sheets, ai_provider, search_defaults, crawlers, latex
- Uses Service Account JSON for Google Sheets auth

### Step 5 - cv_content.txt Created
- Template with placeholders for: name, email, phone, education, work experience, skills, certifications, projects, languages

### Step 6 - Google Sheets Manager Module Created
- sheets_manager.py with SheetsManager class
- Methods: connect, get_all_jobs, get_jobs_by_status, add_job, add_jobs_batch, update_job_row, find_job_row, is_duplicate
- Uses gspread + Service Account credentials
- Auto-creates worksheet with correct column headers if not found

### Step 7 - Config Updated for Moonshot Kimi API
- Switched from Anthropic to Moonshot Kimi (OpenAI-compatible API)
- base_url: https://api.moonshot.cn/v1
- model: moonshot-v1-8k
- Updated requirements.txt: anthropic replaced with openai

### Step 8 - AI Helper Module Created
- ai_helper.py with AIHelper class
- Methods: chat, extract_job_requirements, tailor_cv, write_cover_letter, evaluate_fit
- Uses OpenAI-compatible client pointed at Moonshot Kimi
- JSON parsing with fallback for messy AI responses

### Step 9 - Indeed Crawler Built (Agent 1)
- crawlers/base_crawler.py: BaseCrawler base class with shared logic (headers, rate limiting, fetch, job dict builder)
- crawlers/indeed_crawler.py: IndeedCrawler targeting uk.indeed.com
- Supports filters: job_type, date_posted
- Pagination support, multiple fallback selectors for parsing

### Step 10 - Reed Crawler Built (Agent 2)
- crawlers/reed_crawler.py: ReedCrawler targeting reed.co.uk
- Supports filters: job_type, date_posted
- Pagination support, fallback selectors

### Step 11 - Glassdoor Crawler Built (Agent 3)
- crawlers/glassdoor_crawler.py: GlassdoorCrawler targeting glassdoor.co.uk
- Basic keyword + location search with pagination
- Multiple fallback selectors for different page layouts

### Step 12 - LinkedIn Crawler Built (Agent 4)
- crawlers/linkedin_crawler.py: Uses Playwright headless browser
- Targets LinkedIn public job search pages
- Supports job_type and date_posted filters

### Step 13 - Adzuna Crawler Built (Agent 5)
- crawlers/adzuna_crawler.py: AdzunaCrawler targeting adzuna.co.uk
- Supports filters: job_type, date_posted, pagination

### Step 14 - Parallel Crawler Runner
- crawlers/runner.py: Runs all 5 crawlers simultaneously via ThreadPoolExecutor
- URL-based deduplication across all sources
- Supports running all crawlers or selected ones by name

### Step 15 - Agent 6: Requirements Extractor
- agents/requirements_extractor.py
- Fetches job URLs, strips HTML, extracts structured requirements via AI
- Writes back to Google Sheet with status update

### Step 16 - Agent 7: CV and Cover Letter Generator
- agents/cv_generator.py
- Tailors CV content per job using AI, generates LaTeX, compiles to PDF
- Handles both CV and cover letter with template placeholders

### Step 17 - Agent 8: Fit Evaluator
- agents/fit_evaluator.py
- Compares CV against job requirements, produces 0-100 score
- Writes fit score and summary JSON back to sheet

### Step 18 - LaTeX Templates Created
- templates/cv_template.tex: Professional A4 CV with section formatting
- templates/cover_letter.tex: Clean cover letter with date and subject line

### Step 19 - .env + .gitignore Setup
- .env file with MOONSHOT_API_KEY, GOOGLE_SHEET_URL, GOOGLE_CREDENTIALS_FILE
- .env.example for GitHub (no real keys)
- .gitignore: .env, credentials, pycache, generated PDFs
- Updated sheets_manager.py and ai_helper.py to load from .env

### Step 20 - Streamlit Dashboard Built
- dashboard/app.py with 5 pages:
  - Configuration: API keys, CV content, search defaults
  - Job Search: Search with filters, write to sheet
  - Job Dashboard: View/filter jobs, trigger agents 6/7/8
  - CV & Cover Letters: Download generated PDFs
  - Analytics: Charts for sources, fit scores, top keywords

### Step 21 - Main Jupyter Notebook Created
- JobHunter_AI.ipynb with cells for all 4 phases
- Cell 1: Setup (config, sheets, AI)
- Phase 1: Crawl and save to sheet
- Phase 2: Extract requirements
- Phase 3: Generate CVs/cover letters
- Phase 4: Evaluate fit
- Results view with sorted table

### Step 22 - Switched from Google Sheets to Local Excel
- Google API required payment, so switched to local .xlsx storage
- Rewrote sheets_manager.py to use openpyxl + pandas (no Google dependencies)
- Updated config.json: removed google_sheets section, added storage.file_path
- Updated requirements.txt: removed gspread/google-auth, added openpyxl
- Updated all agents (requirements_extractor, cv_generator, fit_evaluator) for new row indexing
- Updated dashboard/app.py: removed Google Sheets references
- Updated JobHunter_AI.ipynb: uses local Excel storage
- Cleaned .env and .env.example: removed Google keys
- Updated .gitignore: data/jobs.xlsx instead of credentials.json
- Created data/ folder with .gitkeep

### Step 23 - Replaced Custom Crawlers with JobSpy
- Problem: Indeed, Glassdoor, Adzuna returned 0 results (selectors outdated, sites block scrapers)
- Research: Found JobSpy (github.com/speedyapply/JobSpy), battle-tested library with 58+ releases
- JobSpy handles: Indeed, LinkedIn, Glassdoor, Google, ZipRecruiter with built-in pagination (up to 1000 per site)
- Rewrote crawlers/runner.py: uses JobSpy for 5 sites + custom Reed crawler (not covered by JobSpy)
- Updated requirements.txt: added python-jobspy, removed playwright
- Updated dashboard: new site selection (Indeed, LinkedIn, Glassdoor, Google, ZipRecruiter, Reed)
- Pagination now handled automatically by JobSpy via results_wanted parameter

### Step 24 - Bug Fixes After First Test Run
- Problem 1: Only 50 results showing per site (config had max_results_per_site=50)
  - Fix: Increased to 500 in config.json
- Problem 2: Reed crawler only returning job titles and URLs, company/location showing as "nan"
  - Fix: Completely rewrote reed_crawler.py with generic text extraction
  - New extract_metadata_from_card() searches all child elements by class name patterns
  - Falls back to searching dl/ul/div meta elements for company and location
  - No longer depends on specific CSS class names that change frequently
- Problem 3: Glassdoor, Google, ZipRecruiter returning 0 results via JobSpy
  - Root cause: Running all JobSpy sites in one call meant one failure killed all results
  - Fix: Rewrote runner.py to call JobSpy separately for each site via run_jobspy_single_site()
  - Each site runs independently with its own error handling
- Problem 4: Duplicate LinkedIn entries (lowercase "linkedin" vs capitalized "LinkedIn")
  - Fix: Added SOURCE_NAME_MAP dictionary for consistent capitalized source names
- Problem 5: NaN values from pandas showing as "nan" string in Excel
  - Fix: Added explicit pd.isna() checks before string conversion in run_jobspy_single_site()

### Step 25 - Removed Broken Sites (Glassdoor, Google, ZipRecruiter)
- Glassdoor, Google, ZipRecruiter are broken in JobSpy itself (Cloudflare blocking, missing cursors)
- This is a known upstream issue (JobSpy GitHub issue #302), not a bug in our code
- Removed all three from runner.py (SOURCE_NAME_MAP, jobspy_sites list, name_to_jobspy mapping)
- Updated dashboard site selection to only show: Indeed, LinkedIn, Reed
- System now uses 3 working sources: Indeed and LinkedIn via JobSpy, Reed via custom crawler

### Step 26 - Fixed 403 Errors + Per-Job Agent Controls + Dashboard Redesign
- Problem: Requirements Extractor got 403 Forbidden when re-fetching Indeed job URLs
  - Root cause: Indeed blocks direct HTTP requests
  - Fix: JobSpy already returns job descriptions during crawl. Now saved to "Description" column in Excel
  - Extractor now uses stored descriptions first, only falls back to fetching URL if no description stored
- Added "Description" column to SHEET_COLUMNS in sheets_manager.py
- Added process_selected_jobs() method to all 3 agents (Extractor, CVGenerator, FitEvaluator)
  - Agents now work on specific jobs by row index instead of processing all jobs blindly
- Dashboard completely redesigned with 3 pages:
  - Home: stats, how-it-works guide, configuration tabs (storage, search defaults, CV content)
  - Job Search: search box with filters, progress bar, results summary
  - My Jobs: card-based view with per-job expanders showing full details
    - Select individual jobs via checkboxes or "Select All Visible"
    - Run agents on single jobs (buttons inside each card)
    - Run agents on multiple selected jobs (bulk action bar)
    - "Mark as Applied" button per job or in bulk
    - Download CV and Cover Letter PDFs directly from each card
    - Filter by source, status, or search text
    - Status indicators: blue (New), yellow (Processed), green (Applied)

### Step 27 - Major Restructure: Dropped Extractor, Added Click to Apply
- Dropped Requirements Extractor agent entirely (was getting 403s, Moonshot not needed for this)
- JobSpy already provides full job descriptions during crawl, stored in "Description" column
- Added "Job Type" and "Remote" columns to capture more data from JobSpy
- Removed old columns: Required Skills, Nice-to-Have, Experience Needed, Key Responsibilities, Keywords
- Simplified AI helper: tailor_cv() and write_cover_letter() now take raw job description directly
- Added write_application_email() method for generating short email bodies
- CV Generator now reads Description field and passes it directly to AI (no extraction step needed)
- New status flow: New -> CV Ready -> Applied
- Dashboard restructured to 5 pages:
  - Home: stats, 3-step how-it-works, configuration
  - Job Search: search with filters, progress bar, results
  - My Jobs: advanced sorting (9 options), filtering, bulk actions, per-job agent buttons
  - Click to Apply: side-by-side job description vs tailored CV, email integration
    - "Open in Email App" button (mailto link with pre-filled subject/body)
    - "Download .eml" button (email file with CV and cover letter attached)
    - Mark as Applied button
  - Analytics: pipeline view, source breakdown, fit scores, job types, locations, CSV export
- All agent calls wrapped in run_agent_safely() for graceful error handling (401, 429, timeout)

### BUILD COMPLETE
All core components built. No paid APIs needed except Moonshot Kimi (free tier).
Active job sources: Indeed, LinkedIn, Reed.
