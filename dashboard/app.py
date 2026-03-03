import streamlit as st
import sys
import os
import json
import pandas as pd
from urllib.parse import quote
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sheets_manager import load_config, SheetsManager
from ai_helper import AIHelper
from crawlers.runner import run_selected_crawlers
from agents.cv_generator import CVGenerator
from agents.fit_evaluator import FitEvaluator


st.set_page_config(
    page_title="Jobbar - Smart Job Hunter",
    page_icon="briefcase",
    layout="wide",
    initial_sidebar_state="expanded"
)


CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        color: white;
    }

    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: white !important;
    }

    .hero-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }

    .hero-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: #888;
        margin-bottom: 1.5rem;
    }

    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px; padding: 1.5rem; color: white;
        text-align: center; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .stat-card-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        border-radius: 16px; padding: 1.5rem; color: white;
        text-align: center; box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
    }
    .stat-card-orange {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border-radius: 16px; padding: 1.5rem; color: white;
        text-align: center; box-shadow: 0 4px 15px rgba(245, 87, 108, 0.3);
    }
    .stat-card-blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        border-radius: 16px; padding: 1.5rem; color: white;
        text-align: center; box-shadow: 0 4px 15px rgba(79, 172, 254, 0.3);
    }
    .stat-number { font-size: 2.5rem; font-weight: 700; margin: 0; }
    .stat-label { font-size: 0.9rem; opacity: 0.9; margin-top: 0.3rem; }

    .section-header {
        font-family: 'Inter', sans-serif;
        font-size: 1.3rem; font-weight: 600; color: #333;
        padding-bottom: 0.5rem; border-bottom: 2px solid #667eea;
        margin-top: 1.5rem; margin-bottom: 1rem;
    }

    .search-box {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem;
    }

    .footer {
        text-align: center; padding: 2rem 0 1rem; color: #aaa;
        font-size: 0.82rem; border-top: 1px solid #eee; margin-top: 3rem;
    }

    div[data-testid="stMetricValue"] { font-size: 2rem; }
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def get_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.json")
    return load_config(config_path)


def get_sheets_manager(config):
    try:
        file_path = config.get("storage", {}).get("file_path", "data/jobs.xlsx")
        manager = SheetsManager(file_path=file_path)
        manager.connect()
        return manager
    except Exception as e:
        st.error(f"Could not connect to storage: {e}")
        return None


def get_ai_helper(config):
    ai_config = config["ai_provider"]
    if not ai_config.get("api_key"):
        st.error("AI API key not configured. Set MOONSHOT_API_KEY in your .env file.")
        return None
    return AIHelper(
        api_key=ai_config["api_key"],
        base_url=ai_config["base_url"],
        model=ai_config["model"]
    )


def run_agent_safely(agent_func, *args, **kwargs):
    """Wrap agent calls with error handling for auth and network issues."""
    try:
        return agent_func(*args, **kwargs)
    except Exception as e:
        error_str = str(e)
        if "401" in error_str or "authentication" in error_str.lower():
            st.error(
                "API Authentication Failed (401). Your Moonshot API key is invalid or expired. "
                "Go to platform.moonshot.ai to get a new key, then update your .env file."
            )
        elif "429" in error_str or "rate" in error_str.lower():
            st.error("Rate limit reached. Wait a minute and try again.")
        elif "timeout" in error_str.lower():
            st.error("Request timed out. The API server may be busy. Try again.")
        else:
            st.error(f"Agent error: {error_str}")
        return 0


def render_footer():
    st.markdown("""
    <div class="footer">
        Made with dedication by <strong>Md Julfikar Rahman Tuhin</strong><br>
        Jobbar - Multi-Agent AI Job Hunting System
    </div>
    """, unsafe_allow_html=True)


def clean_nan(val):
    if val is None:
        return ""
    s = str(val)
    if s in ("nan", "None", "NaN"):
        return ""
    return s


def build_eml_file(to_email: str, subject: str, body: str, cv_path: str, cl_path: str) -> bytes:
    """Build a .eml file with CV and cover letter attached."""
    msg = MIMEMultipart()
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["From"] = ""
    msg.attach(MIMEText(body, "plain"))

    for path, label in [(cv_path, "CV"), (cl_path, "Cover_Letter")]:
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(path))
                msg.attach(attachment)

    return msg.as_bytes()


def page_home():
    """Landing page."""
    st.markdown('<div class="hero-title">Welcome to Jobbar</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Your AI-powered job hunting assistant. Search, analyse, and apply smarter.</div>', unsafe_allow_html=True)

    config = get_config()
    sheets_manager = get_sheets_manager(config)

    total_jobs = new_jobs = processed_jobs = applied_jobs = cv_ready = 0

    if sheets_manager:
        df = sheets_manager.get_all_jobs()
        if not df.empty:
            total_jobs = len(df)
            if "Status" in df.columns:
                new_jobs = len(df[df["Status"] == "New"])
                cv_ready = len(df[df["Status"] == "CV Ready"])
                applied_jobs = len(df[df["Status"] == "Applied"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{total_jobs}</div><div class="stat-label">Total Jobs</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card-green"><div class="stat-number">{new_jobs}</div><div class="stat-label">New</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card-orange"><div class="stat-number">{cv_ready}</div><div class="stat-label">CV Ready</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card-blue"><div class="stat-number">{applied_jobs}</div><div class="stat-label">Applied</div></div>', unsafe_allow_html=True)

    st.markdown("")

    st.markdown('<div class="section-header">How It Works</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Step 1: Search**")
        st.caption("Crawl Indeed, LinkedIn, and Reed. All job data including descriptions are stored in Excel automatically.")
    with col2:
        st.markdown("**Step 2: Generate CV**")
        st.caption("Select jobs from My Jobs. AI reads the job description and creates a tailored CV and cover letter.")
    with col3:
        st.markdown("**Step 3: Apply**")
        st.caption("Go to Click to Apply. See job requirements and your CV side by side. Send application via email.")

    st.markdown("")
    st.markdown('<div class="section-header">Configuration</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Storage & AI", "Search Defaults", "CV Content"])

    with tab1:
        file_path = config.get("storage", {}).get("file_path", "data/jobs.xlsx")
        st.text_input("Excel File Path", value=file_path, disabled=True)
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("API Key", value=config["ai_provider"]["api_key"], type="password")
        with col2:
            st.text_input("Model", value=config["ai_provider"]["model"])
        st.caption("Using Moonshot Kimi API (free tier). Get your key at platform.moonshot.ai")

    with tab2:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Default Location", value=config["search_defaults"]["location"])
        with col2:
            st.selectbox("Job Type", ["full-time", "part-time", "contract", "temporary", "internship"], index=0, key="cfg_jt")
        with col3:
            st.selectbox("Date Posted", ["past_24h", "past_3days", "past_week", "past_14days"], index=2, key="cfg_dp")

    with tab3:
        cv_path = os.path.join(os.path.dirname(__file__), "..", "config", "cv_content.txt")
        cv_content = ""
        if os.path.exists(cv_path):
            with open(cv_path, "r") as f:
                cv_content = f.read()
        cv_text = st.text_area("Your CV Content", value=cv_content, height=400, label_visibility="collapsed")
        if st.button("Save CV Content", type="primary"):
            with open(cv_path, "w") as f:
                f.write(cv_text)
            st.success("CV content saved successfully.")

    render_footer()


def page_job_search():
    """Page: Job Search."""
    st.markdown('<div class="hero-title">Job Search</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Search across multiple job boards in one click.</div>', unsafe_allow_html=True)

    config = get_config()

    st.markdown('<div class="search-box">', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        job_title = st.text_input("What role are you looking for?", placeholder="e.g. Data Analyst, Software Engineer")
    with col2:
        location = st.text_input("Where?", value=config["search_defaults"]["location"])

    col1, col2, col3 = st.columns(3)
    with col1:
        job_type = st.selectbox("Job Type", ["full-time", "part-time", "contract", "temporary", "internship"])
    with col2:
        date_posted = st.selectbox(
            "Posted Within", ["past_24h", "past_3days", "past_week", "past_14days"], index=2,
            format_func=lambda x: {"past_24h": "Last 24 Hours", "past_3days": "Last 3 Days", "past_week": "Last 7 Days", "past_14days": "Last 14 Days"}.get(x, x)
        )
    with col3:
        crawlers_to_use = st.multiselect("Job Boards", ["Indeed", "LinkedIn", "Reed"], default=["Indeed", "LinkedIn", "Reed"])
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Search Jobs", type="primary", use_container_width=True):
        if not job_title:
            st.warning("Please enter a job title or keywords.")
            return

        filters = {"job_type": job_type, "date_posted": date_posted}
        progress_bar = st.progress(0, text="Starting search...")

        with st.spinner(f"Searching for '{job_title}' across {len(crawlers_to_use)} job boards..."):
            progress_bar.progress(20, text="Connecting to job boards...")
            jobs = run_selected_crawlers(config, job_title, location, [c.lower() for c in crawlers_to_use], filters)
            progress_bar.progress(80, text="Processing results...")

        progress_bar.progress(100, text="Done!")

        if jobs:
            st.success(f"Found {len(jobs)} unique jobs!")
            sheets_manager = get_sheets_manager(config)
            if sheets_manager:
                new_jobs = [j for j in jobs if not sheets_manager.is_duplicate(j["Job URL"])]
                if new_jobs:
                    sheets_manager.add_jobs_batch(new_jobs)
                    has_desc = sum(1 for j in new_jobs if j.get("Description", ""))
                    st.info(f"Saved {len(new_jobs)} new jobs ({has_desc} with full descriptions, {len(jobs) - len(new_jobs)} duplicates skipped).")
                else:
                    st.info("All jobs already exist in your database.")

            st.markdown('<div class="section-header">Search Results</div>', unsafe_allow_html=True)
            source_counts = {}
            for job in jobs:
                src = job.get("Source", "Unknown")
                source_counts[src] = source_counts.get(src, 0) + 1
            cols = st.columns(len(source_counts))
            for i, (src, count) in enumerate(source_counts.items()):
                with cols[i]:
                    st.metric(src, count)

            df = pd.DataFrame(jobs)
            display_cols = [c for c in ["Job Title", "Company", "Location", "Source", "Salary"] if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=400)
        else:
            st.warning("No jobs found. Try different keywords, a broader location, or a wider date range.")

    render_footer()


def page_jobs():
    """Page: My Jobs with sorting, filtering, and agent controls."""
    st.markdown('<div class="hero-title">My Jobs</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Select jobs and generate tailored CVs and cover letters.</div>', unsafe_allow_html=True)

    config = get_config()
    sheets_manager = get_sheets_manager(config)
    if not sheets_manager:
        return

    df = sheets_manager.get_all_jobs()
    if df.empty:
        st.info("No jobs in your database yet. Head over to Job Search to find some.")
        render_footer()
        return

    total = len(df)
    new_count = len(df[df["Status"] == "New"]) if "Status" in df.columns else 0
    cv_ready_count = len(df[df["Status"] == "CV Ready"]) if "Status" in df.columns else 0
    applied_count = len(df[df["Status"] == "Applied"]) if "Status" in df.columns else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", total)
    with col2:
        st.metric("New", new_count)
    with col3:
        st.metric("CV Ready", cv_ready_count)
    with col4:
        st.metric("Applied", applied_count)

    st.markdown('<div class="section-header">Filters & Sorting</div>', unsafe_allow_html=True)

    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        source_filter = st.selectbox("Source", ["All"] + sorted(df["Source"].unique().tolist()))
    with fcol2:
        status_filter = st.selectbox("Status", ["All"] + sorted(df["Status"].unique().tolist()))
    with fcol3:
        search_text = st.text_input("Search", placeholder="Title or company...")
    with fcol4:
        sort_by = st.selectbox("Sort by", [
            "Newest First", "Oldest First", "Title (A-Z)", "Title (Z-A)",
            "Company (A-Z)", "Source", "Status", "Salary (High-Low)",
            "Fit Score (High-Low)"
        ])

    filtered = df.copy()
    if source_filter != "All":
        filtered = filtered[filtered["Source"] == source_filter]
    if status_filter != "All":
        filtered = filtered[filtered["Status"] == status_filter]
    if search_text:
        mask = (
            filtered["Job Title"].str.contains(search_text, case=False, na=False) |
            filtered["Company"].str.contains(search_text, case=False, na=False)
        )
        filtered = filtered[mask]

    if sort_by == "Title (A-Z)":
        filtered = filtered.sort_values("Job Title", ascending=True)
    elif sort_by == "Title (Z-A)":
        filtered = filtered.sort_values("Job Title", ascending=False)
    elif sort_by == "Company (A-Z)":
        filtered = filtered.sort_values("Company", ascending=True)
    elif sort_by == "Source":
        filtered = filtered.sort_values("Source", ascending=True)
    elif sort_by == "Status":
        filtered = filtered.sort_values("Status", ascending=True)
    elif sort_by == "Oldest First":
        filtered = filtered.sort_values("Date Posted", ascending=True)
    elif sort_by == "Newest First":
        filtered = filtered.sort_values("Date Posted", ascending=False)
    elif sort_by == "Salary (High-Low)":
        filtered = filtered.sort_values("Salary", ascending=False)
    elif sort_by == "Fit Score (High-Low)" and "Fit Score" in filtered.columns:
        filtered["_sort_score"] = pd.to_numeric(filtered["Fit Score"], errors="coerce").fillna(0)
        filtered = filtered.sort_values("_sort_score", ascending=False)
        filtered = filtered.drop(columns=["_sort_score"])

    st.caption(f"Showing {len(filtered)} of {total} jobs")

    if "selected_jobs" not in st.session_state:
        st.session_state.selected_jobs = set()

    def toggle_selection(job_idx):
        """Callback to toggle job selection before next render."""
        key = f"sel_{job_idx}"
        if st.session_state.get(key, False):
            st.session_state.selected_jobs.add(job_idx)
        else:
            st.session_state.selected_jobs.discard(job_idx)

    scol1, scol2 = st.columns([1, 3])
    with scol1:
        if st.button("Select All Visible"):
            for idx in filtered.index:
                st.session_state.selected_jobs.add(idx)
                st.session_state[f"sel_{idx}"] = True
            st.rerun()
    with scol2:
        if st.button("Clear Selection"):
            for idx in filtered.index:
                st.session_state[f"sel_{idx}"] = False
            st.session_state.selected_jobs.clear()
            st.rerun()

    selected_count = len(st.session_state.selected_jobs)

    if selected_count > 0:
        st.markdown(f"**{selected_count} job(s) selected**")

        bcol1, bcol2, bcol3 = st.columns(3)

        with bcol1:
            if st.button("Generate CV & Cover Letter", type="primary", use_container_width=True):
                ai = get_ai_helper(config)
                if ai:
                    indices = list(st.session_state.selected_jobs)
                    with st.spinner(f"Generating for {len(indices)} jobs..."):
                        generator = CVGenerator(ai, config)
                        count = run_agent_safely(generator.process_selected_jobs, sheets_manager, indices)
                    if count and count > 0:
                        st.success(f"Generated documents for {count} jobs!")
                    st.session_state.selected_jobs.clear()
                    st.rerun()

        with bcol2:
            if st.button("Evaluate Fit Score", use_container_width=True):
                ai = get_ai_helper(config)
                if ai:
                    indices = list(st.session_state.selected_jobs)
                    with st.spinner(f"Evaluating {len(indices)} jobs..."):
                        evaluator = FitEvaluator(ai, config)
                        count = run_agent_safely(evaluator.process_selected_jobs, sheets_manager, indices)
                    if count and count > 0:
                        st.success(f"Evaluated {count} jobs!")
                    st.session_state.selected_jobs.clear()
                    st.rerun()

        with bcol3:
            if st.button("Mark as Applied", use_container_width=True):
                indices = list(st.session_state.selected_jobs)
                for idx in indices:
                    sheets_manager.update_job_row(idx, {"Status": "Applied"})
                st.success(f"Marked {len(indices)} jobs as Applied.")
                st.session_state.selected_jobs.clear()
                st.rerun()

    st.markdown('<div class="section-header">Job Cards</div>', unsafe_allow_html=True)

    for idx, row in filtered.iterrows():
        title = clean_nan(row.get("Job Title", "Unknown"))
        company = clean_nan(row.get("Company", ""))
        location = clean_nan(row.get("Location", ""))
        source = clean_nan(row.get("Source", ""))
        status = clean_nan(row.get("Status", "New")) or "New"
        salary = clean_nan(row.get("Salary", ""))
        job_url = clean_nan(row.get("Job URL", ""))
        date_posted = clean_nan(row.get("Date Posted", ""))
        job_type = clean_nan(row.get("Job Type", ""))
        remote = clean_nan(row.get("Remote", ""))
        description = clean_nan(row.get("Description", ""))
        fit_score = row.get("Fit Score", "")

        score_str = ""
        try:
            fs = clean_nan(fit_score)
            if fs and float(fs) > 0:
                score_str = f" | Fit: {float(fs):.0f}/100"
        except (ValueError, TypeError):
            pass

        has_desc = "Y" if description and len(description) > 30 else "N"
        status_emoji = {"New": "🔵", "CV Ready": "🟡", "Applied": "🟢"}.get(status, "⚪")
        company_str = f" at {company}" if company else ""
        header = f"{status_emoji} {title}{company_str}{score_str} [Desc: {has_desc}]"

        with st.expander(header, expanded=False):
            tcol1, tcol2 = st.columns([3, 1])
            with tcol1:
                st.checkbox(
                    "Select",
                    value=(idx in st.session_state.selected_jobs),
                    key=f"sel_{idx}",
                    on_change=toggle_selection,
                    args=(idx,)
                )
            with tcol2:
                if status != "Applied":
                    if st.button("Mark Applied", key=f"app_{idx}"):
                        sheets_manager.update_job_row(idx, {"Status": "Applied"})
                        st.rerun()
                else:
                    st.success("Applied")

            icol1, icol2, icol3 = st.columns(3)
            with icol1:
                if company:
                    st.markdown(f"**Company:** {company}")
                if location:
                    st.markdown(f"**Location:** {location}")
            with icol2:
                if salary:
                    st.markdown(f"**Salary:** {salary}")
                if date_posted:
                    st.markdown(f"**Posted:** {date_posted}")
            with icol3:
                st.markdown(f"**Source:** {source}")
                if job_type:
                    st.markdown(f"**Type:** {job_type}")
                if remote:
                    st.markdown(f"**Remote:** {remote}")

            if job_url:
                st.markdown(f"[Open Job Listing]({job_url})")

            if description:
                with st.container():
                    st.caption("Job Description (preview):")
                    st.text(description[:500] + ("..." if len(description) > 500 else ""))

            st.markdown("---")
            acol1, acol2 = st.columns(2)
            with acol1:
                if st.button("Generate CV & Cover Letter", key=f"gen_{idx}"):
                    ai = get_ai_helper(config)
                    if ai:
                        with st.spinner("Generating..."):
                            generator = CVGenerator(ai, config)
                            count = run_agent_safely(generator.process_selected_jobs, sheets_manager, [idx])
                        if count and count > 0:
                            st.success("Done! Go to Click to Apply to review and send.")
                        st.rerun()
            with acol2:
                if st.button("Evaluate Fit", key=f"eval_{idx}"):
                    ai = get_ai_helper(config)
                    if ai:
                        with st.spinner("Evaluating..."):
                            evaluator = FitEvaluator(ai, config)
                            count = run_agent_safely(evaluator.process_selected_jobs, sheets_manager, [idx])
                        if count and count > 0:
                            st.success("Done!")
                        st.rerun()

    render_footer()


def page_click_to_apply():
    """Page: Review CV alongside job description and send application email."""
    st.markdown('<div class="hero-title">Click to Apply</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Review your tailored CV and cover letter, then apply with one click.</div>', unsafe_allow_html=True)

    config = get_config()
    sheets_manager = get_sheets_manager(config)
    if not sheets_manager:
        return

    df = sheets_manager.get_all_jobs()
    if df.empty:
        st.info("No jobs yet.")
        render_footer()
        return

    ready_jobs = df[df["Status"].isin(["CV Ready"])]
    applied_jobs = df[df["Status"] == "Applied"]

    st.markdown(f"**{len(ready_jobs)}** jobs ready to apply | **{len(applied_jobs)}** already applied")

    if ready_jobs.empty:
        st.info("No jobs with generated CVs yet. Go to My Jobs, select some jobs, and click 'Generate CV & Cover Letter'.")
        render_footer()
        return

    for idx, row in ready_jobs.iterrows():
        title = clean_nan(row.get("Job Title", "Unknown"))
        company = clean_nan(row.get("Company", ""))
        location = clean_nan(row.get("Location", ""))
        salary = clean_nan(row.get("Salary", ""))
        job_url = clean_nan(row.get("Job URL", ""))
        description = clean_nan(row.get("Description", ""))
        cv_path = clean_nan(row.get("CV Path", ""))
        cl_path = clean_nan(row.get("Cover Letter Path", ""))
        fit_score = clean_nan(row.get("Fit Score", ""))

        score_display = ""
        try:
            if fit_score and float(fit_score) > 0:
                score_display = f" | Fit: {float(fit_score):.0f}/100"
        except (ValueError, TypeError):
            pass

        company_str = f" at {company}" if company else ""
        with st.expander(f"📋 {title}{company_str}{score_display}", expanded=False):

            if job_url:
                st.markdown(f"[Open Original Listing]({job_url})")

            left_col, right_col = st.columns(2)

            with left_col:
                st.markdown("**Job Description**")
                if location:
                    st.caption(f"Location: {location}")
                if salary:
                    st.caption(f"Salary: {salary}")
                st.markdown("---")
                if description:
                    st.text_area("", value=description[:3000], height=400, disabled=True, key=f"desc_{idx}", label_visibility="collapsed")
                else:
                    st.caption("No description available")

            with right_col:
                st.markdown("**Your Tailored CV**")
                if cv_path and os.path.exists(cv_path):
                    tex_path = cv_path.replace(".pdf", ".tex")
                    if os.path.exists(tex_path):
                        with open(tex_path, "r") as f:
                            tex_content = f.read()
                        st.text_area("", value=tex_content[:3000], height=400, disabled=True, key=f"cv_preview_{idx}", label_visibility="collapsed")
                    else:
                        st.success("CV PDF generated")

                    with open(cv_path, "rb") as f:
                        st.download_button("Download CV (PDF)", f.read(), file_name=f"CV_{company}_{title[:20]}.pdf", mime="application/pdf", key=f"dl_cv_{idx}")
                else:
                    st.warning("CV not found")

                if cl_path and os.path.exists(cl_path):
                    with open(cl_path, "rb") as f:
                        st.download_button("Download Cover Letter (PDF)", f.read(), file_name=f"CL_{company}_{title[:20]}.pdf", mime="application/pdf", key=f"dl_cl_{idx}")

            st.markdown("---")
            st.markdown("**Send Application**")

            email_col1, email_col2 = st.columns([2, 1])
            with email_col1:
                recipient = st.text_input("Employer Email", placeholder="hr@company.com", key=f"email_{idx}")
            with email_col2:
                sender_name = st.text_input("Your Name", value="Md Julfikar Rahman Tuhin", key=f"name_{idx}")

            subject = f"Application for {title} - {company}" if company else f"Application for {title}"
            body = (
                f"Dear Hiring Manager,\n\n"
                f"I am writing to express my interest in the {title} position"
                f"{' at ' + company if company else ''}. "
                f"Please find my CV and cover letter attached for your review.\n\n"
                f"I look forward to hearing from you.\n\n"
                f"Best regards,\n{sender_name}"
            )

            st.text_area("Email Preview", value=body, height=150, key=f"body_{idx}", disabled=True)

            btn_col1, btn_col2, btn_col3 = st.columns(3)

            with btn_col1:
                if recipient:
                    mailto_subject = quote(subject)
                    mailto_body = quote(body)
                    mailto_link = f"mailto:{recipient}?subject={mailto_subject}&body={mailto_body}"
                    st.markdown(f'<a href="{mailto_link}" target="_blank" style="display:inline-block;background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:0.6rem 1.5rem;border-radius:8px;text-decoration:none;font-weight:600;text-align:center;">Open in Email App</a>', unsafe_allow_html=True)
                    st.caption("This opens your email client. Attach the CV and cover letter PDFs manually.")
                else:
                    st.caption("Enter an email address above")

            with btn_col2:
                if recipient and cv_path and os.path.exists(cv_path):
                    eml_data = build_eml_file(recipient, subject, body, cv_path, cl_path)
                    st.download_button(
                        "Download .eml (with attachments)",
                        eml_data,
                        file_name=f"Application_{company}_{title[:15]}.eml",
                        mime="message/rfc822",
                        key=f"eml_{idx}"
                    )
                    st.caption("Download and open in your email client. Attachments included.")

            with btn_col3:
                if st.button("Mark as Applied", key=f"apply_done_{idx}"):
                    sheets_manager.update_job_row(idx, {"Status": "Applied"})
                    st.success("Marked as Applied!")
                    st.rerun()

    render_footer()


def page_analytics():
    """Page: Analytics."""
    st.markdown('<div class="hero-title">Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Insights from your job search data.</div>', unsafe_allow_html=True)

    config = get_config()
    sheets_manager = get_sheets_manager(config)
    if not sheets_manager:
        return

    df = sheets_manager.get_all_jobs()
    if df.empty:
        st.info("No data to analyse yet. Run a job search first.")
        render_footer()
        return

    total = len(df)
    new_count = len(df[df["Status"] == "New"]) if "Status" in df.columns else 0
    cv_ready = len(df[df["Status"] == "CV Ready"]) if "Status" in df.columns else 0
    applied_count = len(df[df["Status"] == "Applied"]) if "Status" in df.columns else 0
    remaining = total - applied_count

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{total}</div><div class="stat-label">Total Jobs</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card-green"><div class="stat-number">{applied_count}</div><div class="stat-label">Applied</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card-orange"><div class="stat-number">{remaining}</div><div class="stat-label">Remaining</div></div>', unsafe_allow_html=True)

    avg_score_val = 0
    if "Fit Score" in df.columns:
        df["Fit Score"] = pd.to_numeric(df["Fit Score"], errors="coerce").fillna(0)
        scored = df[df["Fit Score"] > 0]
        if not scored.empty:
            avg_score_val = scored["Fit Score"].mean()

    with col4:
        st.markdown(f'<div class="stat-card-blue"><div class="stat-number">{avg_score_val:.0f}</div><div class="stat-label">Avg Fit Score</div></div>', unsafe_allow_html=True)

    st.markdown("")

    st.markdown('<div class="section-header">Application Pipeline</div>', unsafe_allow_html=True)

    pipe_col1, pipe_col2, pipe_col3 = st.columns(3)
    with pipe_col1:
        st.metric("New (need CV generation)", new_count)
        if total > 0:
            st.progress(new_count / total, text=f"{(new_count / total * 100):.1f}%")
    with pipe_col2:
        st.metric("CV Ready (ready to apply)", cv_ready)
        if total > 0:
            st.progress(cv_ready / total, text=f"{(cv_ready / total * 100):.1f}%")
    with pipe_col3:
        st.metric("Applied (done)", applied_count)
        if total > 0:
            st.progress(applied_count / total, text=f"{(applied_count / total * 100):.1f}%")

    st.markdown("")

    tab1, tab2, tab3, tab4 = st.tabs(["By Source", "Fit Scores", "Job Types", "Full Data"])

    with tab1:
        if "Source" in df.columns:
            st.markdown('<div class="section-header">Jobs by Source</div>', unsafe_allow_html=True)
            source_counts = df["Source"].value_counts().reset_index()
            source_counts.columns = ["Source", "Count"]
            st.bar_chart(source_counts, x="Source", y="Count", color="Source")

            st.markdown('<div class="section-header">Applied vs Remaining by Source</div>', unsafe_allow_html=True)
            for src in df["Source"].unique():
                src_df = df[df["Source"] == src]
                src_applied = len(src_df[src_df["Status"] == "Applied"])
                src_total = len(src_df)
                pct = (src_applied / src_total * 100) if src_total > 0 else 0
                st.markdown(f"**{src}**: {src_total} jobs total, {src_applied} applied ({pct:.0f}%)")

    with tab2:
        if "Fit Score" in df.columns:
            scored = df[df["Fit Score"] > 0]
            if not scored.empty:
                st.markdown('<div class="section-header">Top 10 Best Matches</div>', unsafe_allow_html=True)
                top_cols = [c for c in ["Job Title", "Company", "Fit Score", "Source", "Status"] if c in scored.columns]
                st.dataframe(scored.nlargest(10, "Fit Score")[top_cols], use_container_width=True, hide_index=True)

                st.markdown('<div class="section-header">Score Distribution</div>', unsafe_allow_html=True)
                bins = [0, 25, 50, 75, 100]
                labels = ["0-25 (Low)", "26-50 (Fair)", "51-75 (Good)", "76-100 (Excellent)"]
                scored_c = scored.copy()
                scored_c["Range"] = pd.cut(scored_c["Fit Score"], bins=bins, labels=labels, include_lowest=True)
                range_counts = scored_c["Range"].value_counts().sort_index().reset_index()
                range_counts.columns = ["Range", "Count"]
                st.bar_chart(range_counts, x="Range", y="Count")

                scol1, scol2, scol3, scol4 = st.columns(4)
                with scol1:
                    st.metric("Average", f"{scored['Fit Score'].mean():.1f}")
                with scol2:
                    st.metric("Highest", f"{scored['Fit Score'].max():.0f}")
                with scol3:
                    st.metric("Lowest", f"{scored['Fit Score'].min():.0f}")
                with scol4:
                    st.metric("Median", f"{scored['Fit Score'].median():.0f}")
            else:
                st.info("No fit scores yet. Use Evaluate Fit from My Jobs.")
        else:
            st.info("No fit scores yet.")

    with tab3:
        if "Job Type" in df.columns:
            jt_counts = df["Job Type"].replace("", "Unknown").value_counts().reset_index()
            jt_counts.columns = ["Type", "Count"]
            if not jt_counts.empty:
                st.markdown('<div class="section-header">Jobs by Type</div>', unsafe_allow_html=True)
                st.bar_chart(jt_counts, x="Type", y="Count")

        if "Remote" in df.columns:
            remote_count = len(df[df["Remote"] == "Remote"])
            onsite_count = total - remote_count
            st.markdown('<div class="section-header">Remote vs On-site</div>', unsafe_allow_html=True)
            st.metric("Remote Jobs", remote_count)
            st.metric("On-site / Unspecified", onsite_count)

        if "Location" in df.columns:
            loc_counts = df["Location"].replace("", "Unknown").value_counts().head(15).reset_index()
            loc_counts.columns = ["Location", "Count"]
            if not loc_counts.empty:
                st.markdown('<div class="section-header">Top 15 Locations</div>', unsafe_allow_html=True)
                st.bar_chart(loc_counts, x="Location", y="Count")

    with tab4:
        st.markdown('<div class="section-header">All Jobs Data</div>', unsafe_allow_html=True)
        display_cols = [c for c in ["Job Title", "Company", "Location", "Source", "Status", "Salary", "Fit Score", "Date Posted", "Job Type", "Remote"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=600)

        csv_data = df.to_csv(index=False)
        st.download_button("Download Full Data as CSV", csv_data, file_name="jobbar_export.csv", mime="text/csv")

    render_footer()


def main():
    inject_css()

    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <div style="font-size: 1.8rem; font-weight: 700; color: #667eea;">Jobbar</div>
            <div style="font-size: 0.8rem; color: #aaa; margin-top: 0.2rem;">Smart Job Hunter</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        page = st.radio(
            "Navigation",
            ["Home", "Job Search", "My Jobs", "Click to Apply", "Analytics"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        st.markdown("""
        <div style="text-align: center; font-size: 0.75rem; color: #666; padding-top: 1rem;">
            Made by<br><strong style="color: #ccc;">Md Julfikar Rahman Tuhin</strong>
        </div>
        """, unsafe_allow_html=True)

    if page == "Home":
        page_home()
    elif page == "Job Search":
        page_job_search()
    elif page == "My Jobs":
        page_jobs()
    elif page == "Click to Apply":
        page_click_to_apply()
    elif page == "Analytics":
        page_analytics()


if __name__ == "__main__":
    main()
