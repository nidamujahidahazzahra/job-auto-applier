import html
import io
import os
from datetime import datetime

import streamlit as st

import glints_scraper
import linkedin_scraper
import scraper
import techinasia_scraper

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --primary: #6366F1;
  --primary-soft: #EEF2FF;
  --bg: #F6F7FB;
  --card: #FFFFFF;
  --border: #E5E7EB;
  --text: #0F172A;
  --muted: #64748B;
}

html[data-theme="dark"] {
  --primary: #818CF8;
  --primary-soft: #1E1B4B;
  --bg: #0B1120;
  --card: #111A2E;
  --border: #1E293B;
  --text: #E2E8F0;
  --muted: #94A3B8;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background-color: var(--bg); }

[data-testid="stSidebar"] { background-color: var(--card); border-right: 1px solid var(--border); }

/* ---- Hero ---- */
.hero {
  background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 55%, #A855F7 100%);
  border-radius: 18px;
  padding: 28px 30px;
  color: #fff;
  margin: 4px 0 10px;
  box-shadow: 0 10px 30px rgba(99, 102, 241, .35);
}
.hero-badge {
  display: inline-block;
  background: rgba(255, 255, 255, .18);
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .4px;
}
.hero-title { font-size: 27px; font-weight: 800; margin-top: 12px; letter-spacing: -.3px; }
.hero-sub { font-size: 14px; opacity: .92; margin-top: 6px; }

/* ---- KPI ---- */
.kpi-row { display: flex; gap: 16px; flex-wrap: wrap; margin: 16px 0 10px; }
.kpi {
  flex: 1 1 170px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px 20px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, .05);
}
.kpi .icon { font-size: 22px; }
.kpi .num { font-size: 30px; font-weight: 800; color: var(--primary); margin-top: 6px; }
.kpi .lbl { font-size: 12px; color: var(--muted); margin-top: 2px; text-transform: uppercase; font-weight: 700; letter-spacing: .5px; }

/* ---- Job card ---- */
.job {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px 20px;
  margin-bottom: 14px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, .06);
  transition: box-shadow .15s ease, transform .15s ease;
}
.job:hover { box-shadow: 0 8px 22px rgba(16, 24, 40, .10); transform: translateY(-1px); }
.job-top { display: flex; align-items: baseline; gap: 10px; }
.job-no {
  flex: none;
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
  background: var(--primary-soft);
  padding: 2px 9px;
  border-radius: 6px;
}
.job-title { font-size: 17px; font-weight: 700; color: var(--text); text-decoration: none; line-height: 1.35; }
.job-title:hover { color: var(--primary); }
.job-company { color: var(--primary); font-weight: 600; font-size: 14px; margin-top: 6px; }
.job-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 11px; }
.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 11px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 500;
  background: var(--primary-soft);
  color: var(--text);
  border: 1px solid var(--border);
}
.chip.location { color: var(--primary); }
.chip.salary { background: rgba(16, 185, 129, .10); color: #059669; border-color: rgba(16, 185, 129, .25); }
.chip.type { background: rgba(245, 158, 11, .10); color: #B45309; border-color: rgba(245, 158, 11, .25); }
.chip.date { background: rgba(148, 163, 184, .12); color: var(--muted); }
.chip.source-jobstreet { background: rgba(99, 102, 241, .12); color: #6366F1; font-weight: 700; }
.chip.source-glints { background: rgba(236, 72, 153, .12); color: #DB2777; font-weight: 700; }
.chip.source-linkedin { background: rgba(10, 102, 194, .12); color: #0A66C2; font-weight: 700; }
.chip.source-techinasia { background: rgba(16, 185, 129, .12); color: #059669; font-weight: 700; }
details.job-desc { margin-top: 12px; border-top: 1px dashed var(--border); padding-top: 10px; }
details.job-desc summary { cursor: pointer; font-size: 13px; font-weight: 700; color: var(--primary); }
details.job-desc .body {
  margin-top: 10px;
  color: var(--text);
  font-size: 13.5px;
  line-height: 1.6;
  white-space: pre-wrap;
  max-height: 280px;
  overflow: auto;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
}

/* ---- Widgets ---- */
div[data-testid="stButton"] > button {
  border-radius: 12px;
  font-weight: 600;
  border: 1px solid var(--border);
  transition: transform .12s ease, box-shadow .12s ease;
}
div[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  color: #fff;
  border: none;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(99, 102, 241, .35);
}
div[data-testid="stDownloadButton"] > button { border-radius: 12px; font-weight: 600; border: 1px solid var(--border); }
div[data-testid="stTextInput"] input { border-radius: 10px; }
div[data-testid="stSlider"] .stSlider { }
div[data-testid="stNumberInput"] input { border-radius: 10px; }

.side-head {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1.3px;
  text-transform: uppercase;
  color: var(--primary);
  margin: 18px 0 10px;
}
.side-foot { color: var(--muted); font-size: 12px; margin-top: 22px; line-height: 1.5; }

.section-title {
  font-size: 19px;
  font-weight: 800;
  color: var(--text);
  margin: 22px 0 6px;
  letter-spacing: -.2px;
}
.section-sub { color: var(--muted); font-size: 13px; margin-bottom: 10px; }

.info-panel {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 26px 28px;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.6;
}
.empty-note { color: var(--muted); font-size: 13.5px; margin: 10px 0 20px; }
"""


def inject_css():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def hero():
    st.markdown(
        '<div class="hero">'
        '<span class="hero-badge">Jobstreet · Glints · LinkedIn · Tech in Asia</span>'
        '<div class="hero-title">Job Scraper</div>'
        '<div class="hero-sub">Ambil lowongan kerja dari Jobstreet, Glints, LinkedIn, dan '
        "Tech in Asia berdasarkan posisi atau skill, lalu simpan sebagai CSV / Excel.</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def progress_callback(state):
    def cb(stage, current, total, label=""):
        if stage == "search":
            state["bar"].progress(0.0)
            state["status"].info(f"Mencari lowongan... halaman {current}/{total}")
        elif stage == "detail":
            if total > 0:
                state["bar"].progress(current / total)
            state["status"].info(f"Mengambil detail {current}/{total}: {label[:70]}")
    return cb


def kpi_row(df):
    cards = [
        ("💼", len(df), "Total Lowongan"),
        ("🏢", df["company"].nunique(), "Perusahaan"),
        ("📍", df["location"].nunique(), "Kota"),
        ("💰", int(df["salary"].fillna("").astype(str).str.strip().ne("").sum()), "Dengan Gaji"),
    ]
    inner = "".join(
        f'<div class="kpi"><div class="icon">{icon}</div>'
        f'<div class="num">{value}</div><div class="lbl">{label}</div></div>'
        for icon, value, label in cards
    )
    st.markdown(f'<div class="kpi-row">{inner}</div>', unsafe_allow_html=True)


def chip(text, cls=""):
    text = str(text).strip()
    if not text:
        return ""
    return f'<span class="chip {cls}">{html.escape(text)}</span>'


def job_card(row, idx):
    title = html.escape(str(row["title"]))
    url = row.get("url") or ""
    company = html.escape(str(row["company"]) or "")
    desc = html.escape(str(row["description"]) or "")
    href = html.escape(url)
    src = str(row.get("source") or "")
    src_chip = chip(src, f"source-{src.lower().replace(' ', '')}") if src else ""
    meta = (
        src_chip
        + chip(row["location"], "location")
        + chip(row["salary"], "salary")
        + chip(row["work_type"], "type")
        + chip(row["posted_date"], "date")
    )
    detail = (
        f'<details class="job-desc"><summary>Lihat deskripsi</summary>'
        f'<div class="body">{desc or "(tidak tersedia)"}</div></details>'
    )
    return (
        f'<div class="job">'
        f'<div class="job-top"><span class="job-no">{idx}</span>'
        f'<a class="job-title" href="{href}" target="_blank" rel="noopener noreferrer">{title}</a></div>'
        f'<div class="job-company">{company}</div>'
        f'<div class="job-meta">{meta}</div>'
        f"{detail}"
        f"</div>"
    )


def render_jobs(df):
    st.markdown('<div class="section-title">Hasil Pencarian</div>', unsafe_allow_html=True)

    colf1, colf2 = st.columns([3, 1])
    with colf1:
        query = st.text_input(
            "🔎 Filter hasil", placeholder="Cari judul, perusahaan, lokasi, skill..."
        )
    with colf2:
        limit = st.selectbox("Tampilkan per halaman", [20, 50, 100, "Semua"])

    filtered = df
    if query.strip():
        q = query.strip().lower()
        mask = filtered.apply(
            lambda r: any(
                q in str(v).lower()
                for v in (
                    r.get("title"),
                    r.get("company"),
                    r.get("location"),
                    r.get("description"),
                    r.get("skills"),
                    r.get("source"),
                )
            ),
            axis=1,
        )
        filtered = filtered[mask]

    limit_all = limit == "Semua"
    shown = filtered if limit_all else filtered.head(int(limit))

    st.markdown(
        f'<div class="empty-note">Menampilkan {len(shown)} dari {len(filtered)} lowongan.</div>',
        unsafe_allow_html=True,
    )

    if len(shown) == 0:
        st.warning("Tidak ada lowongan yang cocok dengan filter.")
        return

    cards = "".join(job_card(row, i + 1) for i, (_, row) in enumerate(shown.iterrows()))
    st.markdown(cards, unsafe_allow_html=True)


def save_output(df, keyword):
    """Write the results to output/ once per scrape and return the shared file base name."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{scraper.slugify(keyword) or 'jobs'}_{timestamp}"
    scraper.save_csv(df, os.path.join(OUTPUT_DIR, f"{base_name}.csv"))
    scraper.save_xlsx(df, os.path.join(OUTPUT_DIR, f"{base_name}.xlsx"))
    return base_name


def download_section(df, base_name):
    st.markdown('<div class="section-title">Simpan / Unduh</div>', unsafe_allow_html=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    xlsx_buf = io.BytesIO()
    df.to_excel(xlsx_buf, index=False)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.download_button(
            "Download CSV",
            csv_bytes,
            file_name=f"{base_name}.csv",
            mime="text/csv",
            width="stretch",
        )
    with col_b:
        st.download_button(
            "Download Excel",
            xlsx_buf.getvalue(),
            file_name=f"{base_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with col_c:
        st.download_button(
            "Download JSON",
            df.to_json(orient="records", force_ascii=False).encode("utf-8"),
            file_name=f"{base_name}.json",
            mime="application/json",
            width="stretch",
        )

    st.markdown(
        f'<div class="side-foot">File tersimpan otomatis di:<br><code>{OUTPUT_DIR}</code></div>',
        unsafe_allow_html=True,
    )

    with st.expander("Lihat tabel data (tanpa deskripsi)"):
        st.dataframe(
            df.drop(columns=["description"]),
            width="stretch",
            hide_index=True,
        )


def run_scrape(keyword, sources, location, max_pages, delay, max_jobs):
    state = {"bar": st.progress(0.0), "status": st.empty()}
    cb = progress_callback(state)
    location = location.strip() or "Indonesia"
    max_jobs = int(max_jobs) or None

    all_jobs = []
    for source in sources:
        state["status"].info(f"▶️ Scraping dari {source}...")
        try:
            if source == "Jobstreet":
                source_jobs = scraper.scrape(
                    keyword,
                    max_pages=int(max_pages),
                    delay=float(delay),
                    max_jobs=max_jobs,
                    on_progress=cb,
                )
            elif source == "Glints":
                source_jobs = glints_scraper.scrape(
                    keyword,
                    delay=float(delay),
                    max_jobs=max_jobs,
                    on_progress=cb,
                )
            elif source == "LinkedIn":
                source_jobs = linkedin_scraper.scrape(
                    keyword,
                    location=location,
                    max_pages=int(max_pages),
                    delay=float(delay),
                    max_jobs=max_jobs,
                    on_progress=cb,
                )
            else:
                source_jobs = techinasia_scraper.scrape(
                    keyword,
                    location=location,
                    max_pages=int(max_pages),
                    delay=float(delay),
                    max_jobs=max_jobs,
                    on_progress=cb,
                )
        except scraper.ScraperError as e:
            st.error(f"Gagal scraping {source}: {e}")
            continue
        except Exception as e:
            # A layout change on one site shouldn't take down the other sources.
            st.error(f"Error tak terduga saat scraping {source}: {type(e).__name__}: {e}")
            continue
        all_jobs.extend(source_jobs)

    state["bar"].progress(1.0)
    state["status"].empty()

    if not all_jobs:
        return None
    return scraper.to_dataframe(all_jobs)


def main():
    st.set_page_config(page_title="Job Scraper", page_icon="🔍", layout="wide")
    inject_css()
    hero()

    with st.sidebar:
        st.markdown('<div class="side-head">Pengaturan</div>', unsafe_allow_html=True)
        keyword = st.text_input(
            "Posisi / skill",
            value="data analyst",
            help="Contoh: 'data analyst', 'it support', 'sql', 'python'",
        )
        sources = st.multiselect(
            "Sumber data",
            ["Jobstreet", "Glints", "LinkedIn", "Tech in Asia"],
            default=["Glints", "LinkedIn", "Tech in Asia"],
            help="Jobstreet saat ini sering memblokir request otomatis (HTTP 403). "
            "Glints maksimal 30 job per kata kunci (tanpa login). "
            "LinkedIn: 10 job per halaman, gaji sering tidak tersedia. "
            "Tech in Asia: fokus lowongan startup/tech.",
        )
        location = st.text_input(
            "Lokasi (untuk LinkedIn & Tech in Asia)",
            value="Indonesia",
            help="Hanya dipakai saat sumber LinkedIn atau Tech in Asia dipilih.",
        )
        max_pages = st.slider(
            "Jumlah halaman (Jobstreet, LinkedIn, Tech in Asia)", 1, 10, 3
        )
        delay = st.slider("Jeda antar request (detik)", 0.0, 5.0, 1.0, 0.5)
        max_jobs = st.number_input("Batas jumlah job per sumber (0 = semua)", min_value=0, value=0)
        run = st.button("Mulai Scraping", type="primary", width="stretch")
        st.markdown(
            '<div class="side-foot">Data hasil scraping tersimpan otomatis ke folder '
            "<code>output/</code> di project ini.</div>",
            unsafe_allow_html=True,
        )

    if run:
        if not keyword.strip():
            st.error("Posisi / skill tidak boleh kosong.")
            return
        if not sources:
            st.error("Pilih minimal satu sumber data.")
            return
        df = run_scrape(keyword, sources, location, max_pages, delay, max_jobs)
        if df is None:
            st.session_state.pop("df", None)
            st.warning("Tidak ada lowongan ditemukan.")
            return
        # Streamlit reruns the whole script on every widget change (filter box,
        # per-page select, download buttons), so keep results in session_state
        # and save the files only once per scrape.
        st.session_state["df"] = df
        st.session_state["base_name"] = save_output(df, keyword)
        st.success(f"Selesai! {len(df)} lowongan berhasil diambil.")

    df = st.session_state.get("df")
    if df is None:
        st.markdown(
            '<div class="info-panel">Masukkan posisi atau skill di sidebar '
            "(misal: <b>data analyst</b>, <b>sql</b>, <b>python</b>), pilih sumber data, "
            "lalu tekan <b>Mulai Scraping</b>.<br><br>"
            "Untuk setiap lowongan akan diambil: judul, perusahaan, lokasi, gaji, "
            "tipe kerja, tanggal posting, deskripsi lengkap, dan skill (untuk Glints).</div>",
            unsafe_allow_html=True,
        )
        return

    kpi_row(df)
    render_jobs(df)
    download_section(df, st.session_state["base_name"])

if __name__ == "__main__":
    main()
