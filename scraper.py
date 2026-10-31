import os
import re
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://id.jobstreet.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

COLUMNS = [
    "source",
    "keyword",
    "job_id",
    "title",
    "url",
    "company",
    "location",
    "salary",
    "work_type",
    "posted_date",
    "description",
    "skills",
    "scraped_at",
]


CURRENCY_SYMBOL = {
    "IDR": "Rp",
    "SGD": "S$",
    "MYR": "RM",
    "PHP": "₱",
    "THB": "฿",
    "VND": "₫",
    "USD": "$",
    "AUD": "A$",
}


class ScraperError(Exception):
    pass


def slugify(keyword):
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", keyword.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


def relative_date(created):
    """Format a datetime as 'Posted 3d ago'. Naive datetimes are treated as local time."""
    if created is None:
        return ""
    now = datetime.now(timezone.utc) if created.tzinfo else datetime.now()
    delta = now - created
    days = delta.days
    if days < 0:
        return "Today"
    if days == 0:
        hours = int(delta.seconds // 3600)
        return "Just now" if hours < 1 else f"Posted {hours}h ago"
    if days < 7:
        return f"Posted {days}d ago"
    if days < 30:
        return f"Posted {days // 7}w ago"
    if days < 365:
        return f"Posted {days // 30}mo ago"
    return f"Posted {days // 365}y ago"


def _new_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def _safe_get(session, url, params=None, retries=3, timeout=30):
    status = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, params=params, timeout=timeout)
            status = resp.status_code
            if resp.status_code == 200:
                return resp.text
            # Client errors (404, 403, ...) won't fix themselves on retry.
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                break
            if resp.status_code == 429 and attempt < retries:
                time.sleep(10 * attempt)
                continue
        except requests.RequestException:
            pass
        if attempt < retries:
            time.sleep(2 * attempt)
    if status == 403:
        raise ScraperError(f"Akses diblokir situs (HTTP 403): {url}")
    suffix = f" (HTTP {status})" if status else ""
    raise ScraperError(f"Gagal mengambil halaman{suffix}: {url}")


def _parse_card(card, keyword):
    job_id = None
    title = None
    url = None

    title_el = card.select_one("[data-automation=jobTitle]")
    if title_el is not None:
        title = title_el.get_text(strip=True)
        href = title_el.get("href") or ""
        m = re.search(r"/job/(\d+)", href)
        if m:
            job_id = m.group(1)
            url = f"{BASE_URL}{href.split('?')[0]}"

    company_el = card.select_one("[data-automation=jobCompany]")
    company = company_el.get_text(strip=True) if company_el else ""

    location_el = card.select_one("[data-automation=jobLocation]")
    location = location_el.get_text(strip=True) if location_el else ""

    salary_el = card.select_one("[data-automation=jobSalary]")
    salary = salary_el.get_text(strip=True) if salary_el else ""

    if not job_id:
        return None

    return {
        "source": "Jobstreet",
        "keyword": keyword,
        "job_id": job_id,
        "title": title,
        "url": url,
        "company": company,
        "location": location,
        "salary": salary,
        "work_type": "",
        "posted_date": "",
        "description": "",
        "skills": "",
        "scraped_at": "",
    }


def _parse_cards(html, keyword):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("[data-card-type='JobCard'], article[data-automation*='job']")
    jobs = []
    for card in cards:
        job = _parse_card(card, keyword)
        if job:
            jobs.append(job)
    return jobs


def search_jobs(keyword, max_pages=3, delay=1.0, session=None, on_progress=None):
    session = session or _new_session()
    keyword = keyword.strip()
    seen = set()
    results = []

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/{slugify(keyword)}-jobs?page={page}"
        if on_progress:
            on_progress("search", page, max_pages, url)
        try:
            html = _safe_get(session, url)
        except ScraperError:
            # Keep what earlier pages returned; only fail if nothing was fetched.
            if page == 1:
                raise
            break
        page_jobs = _parse_cards(html, keyword)
        new_jobs = [j for j in page_jobs if j["job_id"] not in seen]
        for job in new_jobs:
            seen.add(job["job_id"])
        results.extend(new_jobs)
        if not page_jobs:
            break
        if page < max_pages:
            time.sleep(delay)

    return results


def get_job_detail(job, session=None, retries=2):
    session = session or _new_session()
    url = f"{BASE_URL}/job/{job['job_id']}"
    try:
        html = _safe_get(session, url, retries=retries)
    except ScraperError:
        return job

    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("[data-automation=job-detail-title]")
    if title_el:
        job["title"] = title_el.get_text(strip=True)

    company_el = soup.select_one("[data-automation=advertiser-name]")
    if company_el:
        job["company"] = company_el.get_text(strip=True)

    location_el = soup.select_one("[data-automation=job-detail-location]")
    if location_el:
        job["location"] = location_el.get_text(strip=True)

    salary_el = soup.select_one("[data-automation=job-detail-salary]")
    if salary_el:
        job["salary"] = salary_el.get_text(strip=True)

    work_type_el = soup.select_one("[data-automation=job-detail-work-type]")
    if work_type_el:
        job["work_type"] = work_type_el.get_text(strip=True)

    desc_el = soup.select_one("[data-automation=jobAdDetails]")
    if desc_el:
        job["description"] = desc_el.get_text(" ", strip=True)

    listed_el = soup.select_one("[data-automation=job-detail-date-posted]")
    if not listed_el:
        for span in soup.find_all("span"):
            text = span.get_text(strip=True)
            if text.startswith(("Posted ", "Listed ", "Expiring")):
                listed_el = span
                break
    if listed_el:
        job["posted_date"] = listed_el.get_text(strip=True)

    return job


def scrape(keyword, max_pages=3, delay=1.0, max_jobs=None, on_progress=None):
    session = _new_session()

    if on_progress:
        on_progress("search", 0, max_pages, "")
    jobs = search_jobs(keyword, max_pages, delay, session, on_progress=on_progress)

    if max_jobs:
        jobs = jobs[:max_jobs]

    total = len(jobs)
    for idx, job in enumerate(jobs, start=1):
        if on_progress:
            on_progress("detail", idx, total, job["title"])
        get_job_detail(job, session)
        if idx < total:
            time.sleep(delay)

    now = datetime.now().isoformat(timespec="seconds")
    for job in jobs:
        job["scraped_at"] = now

    return jobs


def to_dataframe(jobs):
    return pd.DataFrame(jobs, columns=COLUMNS)


def save_csv(df, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def save_xlsx(df, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    df.to_excel(path, index=False)
    return path
