# 🔍 Noon Search Analytics Dashboard

> LLM-powered comparison of **Google** vs **Close4** search ranking quality — built for business stakeholders at [noon.com](https://noon.com).

---

## What it does

This Streamlit dashboard surfaces insights from the `auto_analyser` BigQuery pipeline — giving search product managers a clear, visual way to understand:

| View | What you see |
|------|-------------|
| **📊 Overview** | Win rates, avg scores, score distribution, delivery mix, popularity-by-rank |
| **🔍 Query Explorer** | Browse every evaluated query, filter by winner, drill into LLM reasons |
| **📦 Product Comparison** | Side-by-side top-10 products for any query, per engine |
| **💡 Systemic Insights** | Macro-level strengths/weaknesses/verdict from LLM summary |

---

## Project structure

```
noon-search-analytics/
├── app.py                        # Main Streamlit app (entry point)
├── utils/
│   ├── __init__.py
│   ├── bq_client.py              # BigQuery connection + SQL queries
│   └── helpers.py                # Charts, formatters, constants
├── .streamlit/
│   ├── config.toml               # Dark theme config
│   └── secrets.toml.template     # Copy → secrets.toml and fill in creds
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Local setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_ORG/noon-search-analytics.git
cd noon-search-analytics
pip install -r requirements.txt
```

### 2. Set up BigQuery credentials

Copy the secrets template and fill in your GCP service account JSON:

```bash
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your real credentials
```

The service account needs **BigQuery Data Viewer** + **BigQuery Job User** roles on the relevant projects.

### 3. Run

```bash
streamlit run app.py
```

---

## Deploy on Streamlit Cloud

1. **Push to GitHub** (the `.gitignore` already excludes `secrets.toml`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo → `app.py` as the main file
4. Under **Advanced settings → Secrets**, paste the contents of your `secrets.toml`
5. Click **Deploy**

---

## BigQuery tables required

| Table | Description |
|-------|-------------|
| `noonbigmerchsandbox.satyam.auto_analyser_v1_sa` | Per-query LLM response with scores, winner, reasons, URLs |
| `noonbigmerchsandbox.satyam.auto_analyser_summary_sa` | Country-level macro LLM summary |
| `noonbigmerchsandbox.satyam.llm_analytics_base2` | Base table with engine, rank, delivery, popularity per product |

---

## Adding more countries

The dashboard already supports `SA`, `AE`, `EG` — just make sure the corresponding tables exist. The country selector in the sidebar filters all queries dynamically.

---

## Refreshing data

Data is cached for **1 hour** (`@st.cache_data(ttl=3600)`). Use the **🔄 Refresh** button in the sidebar to force a reload.

---

## Tech stack

- [Streamlit](https://streamlit.io) — UI framework  
- [Plotly](https://plotly.com/python/) — interactive charts  
- [google-cloud-bigquery](https://cloud.google.com/python/docs/reference/bigquery/latest) — BQ client  
- Fonts: **Syne** (headings) + **DM Mono** (data) via Google Fonts
