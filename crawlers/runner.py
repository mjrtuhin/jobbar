from concurrent.futures import ThreadPoolExecutor, as_completed
from crawlers.reed_crawler import ReedCrawler
import pandas as pd


SOURCE_NAME_MAP = {
    "indeed": "Indeed",
    "linkedin": "LinkedIn"
}


def run_jobspy_single_site(site: str, job_title: str, location: str, results_wanted: int = 50,
                           hours_old: int = 168, job_type: str = "", country: str = "UK") -> list:
    """Run JobSpy for a single site. Isolated so one failure does not affect others."""
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("[JobSpy] Not installed. Run: pip install python-jobspy")
        return []

    jobspy_type_map = {
        "full-time": "fulltime",
        "part-time": "parttime",
        "contract": "contract",
        "temporary": "contract",
        "internship": "internship"
    }

    hours_map = {
        "past_24h": 24,
        "past_3days": 72,
        "past_week": 168,
        "past_14days": 336
    }

    if isinstance(hours_old, str):
        hours_old = hours_map.get(hours_old, 168)

    display_name = SOURCE_NAME_MAP.get(site, site)
    print(f"[{display_name}] Searching for '{job_title}' in '{location}'...")

    kwargs = {
        "site_name": [site],
        "search_term": job_title,
        "location": location,
        "results_wanted": results_wanted,
        "hours_old": hours_old,
        "country_indeed": country,
        "linkedin_fetch_description": True,
        "verbose": 1
    }

    jt = jobspy_type_map.get(job_type, "")
    if jt:
        kwargs["job_type"] = jt

    try:
        df = scrape_jobs(**kwargs)

        if df is None or df.empty:
            print(f"[{display_name}] No results found.")
            return []

        jobs = []
        for _, row in df.iterrows():
            title = row.get("title", "")
            company = row.get("company", "")
            loc = row.get("location", "")
            date_val = row.get("date_posted", "")
            job_url = row.get("job_url", "")

            title = "" if pd.isna(title) else str(title)
            company = "" if pd.isna(company) else str(company)
            loc = "" if pd.isna(loc) else str(loc)
            date_val = "" if pd.isna(date_val) else str(date_val)
            job_url = "" if pd.isna(job_url) else str(job_url)

            salary = ""
            min_sal = row.get("min_amount", None)
            max_sal = row.get("max_amount", None)
            currency = row.get("currency", "")
            if pd.notna(min_sal) and pd.notna(max_sal):
                currency = "" if pd.isna(currency) else str(currency)
                salary = f"{currency}{min_sal} - {currency}{max_sal}"
            elif pd.notna(min_sal):
                currency = "" if pd.isna(currency) else str(currency)
                salary = f"{currency}{min_sal}"

            description = row.get("description", "")
            description = "" if pd.isna(description) else str(description)

            jtype = row.get("job_type", "")
            jtype = "" if pd.isna(jtype) else str(jtype)

            is_remote = row.get("is_remote", "")
            is_remote = "" if pd.isna(is_remote) else str(is_remote)
            if is_remote == "True":
                is_remote = "Remote"
            elif is_remote == "False":
                is_remote = ""

            if title and job_url:
                jobs.append({
                    "Job Title": title,
                    "Company": company,
                    "Location": loc,
                    "Salary": salary,
                    "Date Posted": date_val,
                    "Job URL": job_url,
                    "Source": display_name,
                    "Status": "New",
                    "Description": description,
                    "Job Type": jtype,
                    "Remote": is_remote
                })

        print(f"[{display_name}] Found {len(jobs)} jobs.")
        return jobs

    except Exception as e:
        print(f"[{display_name}] Error: {e}")
        return []


def run_reed_search(config: dict, job_title: str, location: str, filters: dict) -> list:
    """Run Reed crawler separately (not covered by JobSpy)."""
    try:
        crawler = ReedCrawler(config)
        jobs = crawler.search(job_title, location, **filters)
        print(f"[Reed] Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"[Reed] Error: {e}")
        return []


def run_all_crawlers(config: dict, job_title: str, location: str, filters: dict = None) -> list:
    """Run all sites in parallel: Indeed, LinkedIn, Glassdoor, Google, ZipRecruiter (via JobSpy) + Reed."""
    if filters is None:
        filters = {}

    max_results = config.get("crawlers", {}).get("max_results_per_site", 50)
    date_posted = filters.get("date_posted", "past_week")
    job_type = filters.get("job_type", "")

    all_jobs = []
    seen_urls = set()

    jobspy_sites = ["indeed", "linkedin"]

    print(f"\nStarting job search for '{job_title}' in '{location}'...")
    print(f"Searching {len(jobspy_sites) + 1} sites (Indeed, LinkedIn, Reed) with up to {max_results} results each...\n")

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {}

        for site in jobspy_sites:
            future = executor.submit(
                run_jobspy_single_site, site, job_title, location,
                results_wanted=max_results, hours_old=date_posted, job_type=job_type
            )
            futures[future] = SOURCE_NAME_MAP.get(site, site)

        reed_future = executor.submit(
            run_reed_search, config, job_title, location, filters
        )
        futures[reed_future] = "Reed"

        for future in as_completed(futures):
            name = futures[future]
            try:
                jobs = future.result()
                added = 0
                for job in jobs:
                    url = job.get("Job URL", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_jobs.append(job)
                        added += 1
                print(f"[Runner] {name}: {added} unique jobs added (total: {len(all_jobs)})")
            except Exception as e:
                print(f"[Runner] {name} failed: {e}")

    print(f"\nSearch complete. Total unique jobs: {len(all_jobs)}")
    return all_jobs


def run_selected_crawlers(config: dict, job_title: str, location: str, crawler_names: list, filters: dict = None) -> list:
    """Run only specific crawlers by name."""
    if filters is None:
        filters = {}

    max_results = config.get("crawlers", {}).get("max_results_per_site", 50)
    date_posted = filters.get("date_posted", "past_week")
    job_type = filters.get("job_type", "")

    all_jobs = []
    seen_urls = set()

    name_to_jobspy = {
        "indeed": "indeed",
        "linkedin": "linkedin"
    }

    jobspy_sites = []
    run_reed = False

    for name in crawler_names:
        lower = name.lower()
        if lower == "reed":
            run_reed = True
        elif lower in name_to_jobspy:
            jobspy_sites.append(name_to_jobspy[lower])

    max_workers = len(jobspy_sites) + (1 if run_reed else 0)
    if max_workers == 0:
        return []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}

        for site in jobspy_sites:
            future = executor.submit(
                run_jobspy_single_site, site, job_title, location,
                results_wanted=max_results, hours_old=date_posted, job_type=job_type
            )
            futures[future] = SOURCE_NAME_MAP.get(site, site)

        if run_reed:
            reed_future = executor.submit(
                run_reed_search, config, job_title, location, filters
            )
            futures[reed_future] = "Reed"

        for future in as_completed(futures):
            name = futures[future]
            try:
                jobs = future.result()
                for job in jobs:
                    url = job.get("Job URL", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_jobs.append(job)
            except Exception as e:
                print(f"[Runner] {name} failed: {e}")

    return all_jobs
