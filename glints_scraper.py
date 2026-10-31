import json
import re
import time
from datetime import datetime
from urllib.parse import quote

from scraper import (
    CURRENCY_SYMBOL,
    ScraperError,
    _new_session,
    _safe_get,
    relative_date,
)

SOURCE = "Glints"

SEARCH_URL = "https://glints.com/id/opportunities/jobs/explore"
DETAIL_URL = "https://glints.com/id/opportunities/jobs/{slug}/{job_id}"

WORK_TYPE_MAP = {
    "FULL_TIME": "Full time",
    "PART_TIME": "Part time",
    "CONTRACT": "Contract",
    "TEMPORARY": "Temporary",
    "INTERNSHIP": "Internship",
    "VOLUNTEER": "Volunteer",
}


def _next_data(html):
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    if not match:
        return None
    return json.loads(match.group(1))


def _extract_description(desc_json):
    if not desc_json:
        return ""
    if isinstance(desc_json, str):
        try:
            data = json.loads(desc_json)
        except (TypeError, ValueError):
            return desc_json
    else:
        data = desc_json
    if isinstance(data, dict):
        blocks = data.get("blocks") or []
        return "\n".join(
            b.get("text", "")
            for b in blocks
            if isinstance(b, dict) and b.get("text")
        )
    if isinstance(data, list):
        return "\n".join(
            str(b.get("text", "")) if isinstance(b, dict) else str(b)
            for b in data
        )
    return str(data)


def _format_salary(salaries):
    if not salaries:
        return ""
    parts = []
    for s in salaries:
        if not isinstance(s, dict):
            continue
        low, high = s.get("minAmount"), s.get("maxAmount")
        if not low and not high:
            continue
        symbol = CURRENCY_SYMBOL.get(s.get("CurrencyCode") or "IDR", "Rp")
        amounts = []
        for value in (low, high):
            if value:
                try:
                    amounts.append(f"{symbol} {int(value):,}")
                except (TypeError, ValueError):
                    amounts.append(str(value))
        rng = " - ".join(amounts)
        mode = (s.get("salaryMode") or "").lower()
        suffix = {"month": "per month", "year": "per year", "day": "per day"}.get(
            mode, ""
        )
        parts.append(f"{rng} {suffix}".strip())
    return "; ".join(p for p in parts if p)


def _relative_date(iso):
    if not iso:
        return ""
    try:
        created = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return ""
    return relative_date(created)


def _map_work_type(value):
    if not value:
        return ""
    return WORK_TYPE_MAP.get(str(value).upper(), str(value).replace("_", " ").title())


def _extract_skills(raw):
    skills = raw.get("skills")
    if not skills:
        skills = raw.get("JobSkills")
    if not skills:
        return ""
    names = []
    for sk in skills:
        if not isinstance(sk, dict):
            continue
        if isinstance(sk.get("skill"), dict):
            name = sk["skill"].get("name")
        else:
            name = sk.get("name") or sk.get("skillName")
        if name:
            names.append(str(name))
    return ", ".join(names)


def _map_job(raw, keyword):
    location = ""
    loc = raw.get("location")
    if isinstance(loc, dict) and loc.get("formattedName"):
        location = loc["formattedName"]

    company = ""
    comp = raw.get("company")
    if isinstance(comp, dict):
        company = comp.get("name") or ""

    return {
        "source": SOURCE,
        "keyword": keyword,
        "job_id": str(raw.get("id", "")),
        "title": raw.get("title") or "",
        "url": "",
        "company": company,
        "location": location,
        "salary": _format_salary(raw.get("salaries")),
        "work_type": _map_work_type(raw.get("type")),
        "posted_date": _relative_date(raw.get("createdAt")),
        "description": "",
        "skills": _extract_skills(raw),
        "scraped_at": "",
    }


def _slug_map(html):
    hrefs = re.findall(
        r'href="(/id/opportunities/jobs/([^/"]+)/'
        r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}))",
        html,
    )
    return {job_id: slug for _, slug, job_id in hrefs}


def search_jobs(keyword, session=None, on_progress=None):
    session = session or _new_session()
    keyword = keyword.strip()
    url = f"{SEARCH_URL}?keyword={quote(keyword)}"
    if on_progress:
        on_progress("search", 1, 1, url)
    html = _safe_get(session, url)
    data = _next_data(html)
    if not data:
        return []
    initial = (
        data.get("props", {}).get("pageProps", {}).get("initialJobs") or {}
    )
    raw_jobs = initial.get("jobsInPage") or []
    slugs = _slug_map(html)

    jobs = []
    for raw in raw_jobs:
        job = _map_job(raw, keyword)
        job_id = job["job_id"]
        slug = slugs.get(job_id)
        if slug:
            job["url"] = DETAIL_URL.format(slug=slug, job_id=job_id)
        else:
            job["url"] = f"https://glints.com/id/opportunities/jobs/{job_id}"
        jobs.append(job)
    return jobs


def get_job_detail(job, session=None, retries=2):
    session = session or _new_session()
    url = job.get("url")
    if not url:
        return job
    try:
        html = _safe_get(session, url, retries=retries)
    except ScraperError:
        return job

    data = _next_data(html)
    if not data:
        return job
    raw = (
        data.get("props", {})
        .get("pageProps", {})
        .get("initialData", {})
        .get("data")
        or {}
    )
    if not raw:
        return job

    if raw.get("title"):
        job["title"] = raw["title"]
    comp = raw.get("company") or {}
    if isinstance(comp, dict) and comp.get("name"):
        job["company"] = comp["name"]
    if raw.get("descriptionJsonString"):
        job["description"] = _extract_description(raw["descriptionJsonString"])
    if raw.get("type"):
        job["work_type"] = _map_work_type(raw["type"])
    if raw.get("createdAt"):
        job["posted_date"] = _relative_date(raw["createdAt"])
    salary = _format_salary(raw.get("salaries"))
    if salary:
        job["salary"] = salary
    skills = _extract_skills(raw)
    if skills:
        job["skills"] = skills

    return job


def scrape(keyword, delay=1.0, max_jobs=None, on_progress=None):
    session = _new_session()

    jobs = search_jobs(keyword, session, on_progress=on_progress)

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
