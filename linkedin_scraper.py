import re
import time
from datetime import datetime

from bs4 import BeautifulSoup

from scraper import ScraperError, _new_session, _safe_get

SOURCE = "LinkedIn"

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs/view/{job_id}"

WORK_TYPE_MAP = {
    "penuh waktu": "Full time",
    "full-time": "Full time",
    "full time": "Full time",
    "paruh waktu": "Part time",
    "part-time": "Part time",
    "kontrak": "Contract",
    "contract": "Contract",
    "magang": "Internship",
    "internship": "Internship",
    "sukarelawan": "Volunteer",
    "volunteer": "Volunteer",
    "lainnya": "Other",
    "other": "Other",
}


def _map_work_type(value):
    if not value:
        return ""
    key = str(value).strip().lower()
    return WORK_TYPE_MAP.get(key, str(value).strip())


def _parse_cards(html, keyword):
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for card in soup.select("div.base-search-card"):
        urn = card.get("data-entity-urn") or ""
        m = re.search(r"(\d+)$", urn)
        if not m:
            continue
        job_id = m.group(1)

        title_el = card.select_one(".base-search-card__title")
        title = title_el.get_text(strip=True) if title_el else ""

        link_el = card.select_one("a.base-card__full-link")
        url = link_el.get("href") if link_el else f"https://www.linkedin.com/jobs/view/{job_id}"
        url = (url or "").split("?")[0]

        company_el = card.select_one(".base-search-card__subtitle a")
        company = company_el.get_text(strip=True) if company_el else ""

        location_el = card.select_one(".job-search-card__location")
        location = location_el.get_text(strip=True) if location_el else ""

        date_el = card.select_one(".job-search-card__listdate")
        posted = date_el.get_text(strip=True) if date_el else ""

        jobs.append(
            {
                "source": SOURCE,
                "keyword": keyword,
                "job_id": job_id,
                "title": title,
                "url": url,
                "company": company,
                "location": location,
                "salary": "",
                "work_type": "",
                "posted_date": posted,
                "description": "",
                "skills": "",
                "scraped_at": "",
            }
        )
    return jobs


def search_jobs(
    keyword,
    location="Indonesia",
    max_pages=3,
    delay=1.0,
    session=None,
    on_progress=None,
):
    session = session or _new_session()
    keyword = keyword.strip()
    seen = set()
    results = []
    start = 0

    for page in range(1, max_pages + 1):
        params = {"keywords": keyword, "location": location, "start": start}
        url = SEARCH_URL
        if on_progress:
            on_progress("search", page, max_pages, url)
        try:
            html = _safe_get(session, url, params=params)
        except ScraperError:
            break
        page_jobs = _parse_cards(html, keyword)
        if not page_jobs:
            break
        # The guest API returns a variable number of cards (usually 10), so
        # advance by what we actually got instead of a fixed page size.
        start += len(page_jobs)
        new_jobs = [j for j in page_jobs if j["job_id"] not in seen]
        for job in new_jobs:
            seen.add(job["job_id"])
        results.extend(new_jobs)
        if page < max_pages:
            time.sleep(delay)

    return results


def get_job_detail(job, session=None, retries=2):
    session = session or _new_session()
    url = DETAIL_URL.format(job_id=job["job_id"])
    try:
        html = _safe_get(session, url, retries=retries)
    except ScraperError:
        return job

    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("h1.top-card-layout__title")
    if title_el:
        job["title"] = title_el.get_text(strip=True)

    company_el = soup.select_one("a.topcard__org-name-link")
    if company_el:
        job["company"] = company_el.get_text(strip=True)

    loc_el = None
    for flavor in soup.select(".topcard__flavor"):
        if flavor.select(".topcard__org-name-link"):
            continue
        text = flavor.get_text(strip=True)
        if text and "ago" not in text.lower():
            loc_el = flavor
            break
    if loc_el is None:
        loc_el = soup.select_one(".topcard__flavor")
    if loc_el is not None:
        text = loc_el.get_text(strip=True)
        if text:
            job["location"] = text

    date_el = soup.select_one(".posted-time-ago__text")
    if date_el:
        job["posted_date"] = date_el.get_text(strip=True)

    desc_el = soup.select_one("div.show-more-less-html__markup")
    if desc_el:
        job["description"] = desc_el.get_text("\n", strip=True)

    criteria = {}
    for item in soup.select("li.description__job-criteria-item"):
        header = item.select_one(".description__job-criteria-subheader")
        text = item.select_one(".description__job-criteria-text")
        if header and text:
            criteria[header.get_text(strip=True).lower()] = text.get_text(strip=True)

    for key in ("jenis pekerjaan", "employment type"):
        if key in criteria:
            job["work_type"] = _map_work_type(criteria[key])
            break

    return job


def scrape(
    keyword,
    location="Indonesia",
    max_pages=3,
    delay=1.0,
    max_jobs=None,
    on_progress=None,
):
    session = _new_session()

    if on_progress:
        on_progress("search", 0, max_pages, "")
    jobs = search_jobs(
        keyword, location, max_pages, delay, session, on_progress=on_progress
    )

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
