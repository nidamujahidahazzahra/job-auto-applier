import json
import re
import time
from datetime import datetime
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from scraper import CURRENCY_SYMBOL, ScraperError, _new_session, relative_date

SOURCE = "Tech in Asia"

ALGOLIA_URL = "https://219wx3mpv4-dsn.algolia.net/1/indexes/*/queries"
APP_ID = "219WX3MPV4"
API_KEY = "b528008a75dc1c4402bfe0d8db8b3f8e"
INDEX_NAME = "job_postings"

DETAIL_URL = "https://www.techinasia.com/jobs/{job_id}"

WORK_TYPE_MAP = {
    "Full-time": "Full time",
    "Full time": "Full time",
    "Part-time": "Part time",
    "Part time": "Part time",
    "Contract": "Contract",
    "Freelance": "Freelance",
    "Internship": "Internship",
    "Temporary": "Temporary",
}

def _algolia_params(keyword, location, page, hits_per_page=100):
    params = {
        "query": keyword,
        "hitsPerPage": hits_per_page,
        "page": page,
    }
    if location.strip():
        facet = f"city.work_country_name:{location.strip()}"
        params["facetFilters"] = json.dumps([[facet]])
    return urlencode(params)


def _safe_post(session, url, body, params=None, retries=3, timeout=30):
    for attempt in range(1, retries + 1):
        try:
            resp = session.post(url, params=params, json=body, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
        except (requests.RequestException, ValueError):
            pass
        if attempt < retries:
            time.sleep(2 * attempt)
    raise ScraperError("Gagal mengambil data Tech in Asia")


def _format_salary(hit):
    if not hit.get("is_salary_visible"):
        return ""
    low, high = hit.get("salary_min"), hit.get("salary_max")
    if not low and not high:
        return ""
    currency = (hit.get("currency") or {}).get("currency_code")
    symbol = CURRENCY_SYMBOL.get(currency, currency or "")
    amounts = []
    for value in (low, high):
        if value:
            try:
                amounts.append(f"{symbol} {int(value):,}")
            except (TypeError, ValueError):
                amounts.append(str(value))
    return " - ".join(amounts)


def _relative_date(raw):
    if not raw:
        return ""
    try:
        created = datetime.strptime(str(raw).strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ""
    return relative_date(created)


def _strip_html(value):
    if not value:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _map_work_type(value):
    if not value:
        return ""
    return WORK_TYPE_MAP.get(str(value).strip(), str(value).strip())


def _extract_skills(hit):
    skills = hit.get("job_skills") or []
    names = [str(sk.get("name")) for sk in skills if isinstance(sk, dict) and sk.get("name")]
    return ", ".join(names)


def _map_job(hit, keyword):
    city = hit.get("city") or {}
    location = ", ".join(
        part for part in (city.get("name"), city.get("country_name")) if part
    )
    company = (hit.get("company") or {}).get("name") or ""

    return {
        "source": SOURCE,
        "keyword": keyword,
        "job_id": str(hit.get("id") or hit.get("objectID") or ""),
        "title": hit.get("title") or "",
        "url": DETAIL_URL.format(job_id=hit.get("id") or hit.get("objectID") or ""),
        "company": company,
        "location": location,
        "salary": _format_salary(hit),
        "work_type": _map_work_type((hit.get("job_type") or {}).get("name")),
        "posted_date": _relative_date(hit.get("published_at")),
        "description": _strip_html(hit.get("description")),
        "skills": _extract_skills(hit),
        "scraped_at": "",
    }


def search_jobs(
    keyword, location="", max_pages=3, delay=1.0, session=None, on_progress=None
):
    session = session or _new_session()
    keyword = keyword.strip()
    seen = set()
    results = []

    for page in range(max_pages):
        if on_progress:
            on_progress("search", page + 1, max_pages, ALGOLIA_URL)
        body = {
            "requests": [
                {
                    "indexName": INDEX_NAME,
                    "params": _algolia_params(keyword, location, page),
                }
            ]
        }
        params = {
            "x-algolia-application-id": APP_ID,
            "x-algolia-api-key": API_KEY,
            "x-algolia-agent": "Algolia for Python 3.30.0",
        }
        data = _safe_post(session, ALGOLIA_URL, body, params=params)
        hits = (data.get("results") or [{}])[0].get("hits") or []
        if not hits:
            break

        for hit in hits:
            job = _map_job(hit, keyword)
            if not job["job_id"] or job["job_id"] in seen:
                continue
            seen.add(job["job_id"])
            results.append(job)

        if page < max_pages - 1:
            time.sleep(delay)

    return results


def scrape(keyword, location="", max_pages=3, delay=1.0, max_jobs=None, on_progress=None):
    session = _new_session()

    jobs = search_jobs(
        keyword,
        location=location,
        max_pages=max_pages,
        delay=delay,
        session=session,
        on_progress=on_progress,
    )

    if max_jobs:
        jobs = jobs[:max_jobs]

    now = datetime.now().isoformat(timespec="seconds")
    for job in jobs:
        job["scraped_at"] = now

    return jobs
