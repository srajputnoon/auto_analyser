"""
BigQuery client wrapper with Streamlit caching.
Credentials are loaded from st.secrets (set in Streamlit Cloud or .streamlit/secrets.toml).
"""

import json
import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account


@st.cache_resource
def get_bq_client():
    """Return a cached BigQuery client using service account from secrets."""
    credentials_info = dict(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/bigquery"],
    )
    client = bigquery.Client(
        credentials=credentials,
        project=credentials_info["project_id"],
    )
    return client


@st.cache_data(ttl=3600, show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    """Execute a BigQuery SQL query and return a DataFrame. Results cached for 1 hour."""
    client = get_bq_client()
    return client.query(sql).to_dataframe()


# ─── Canonical queries ────────────────────────────────────────────────────────

QUERY_ANALYSIS_SQL = """
SELECT
  country,
  query,
  CAST(JSON_VALUE(clean_json, '$.google_score')  AS FLOAT64) AS google_score,
  CAST(JSON_VALUE(clean_json, '$.close4_score')  AS FLOAT64) AS close4_score,
  JSON_VALUE(clean_json, '$.winner')              AS winner,
  ARRAY_TO_STRING(JSON_VALUE_ARRAY(clean_json, '$.reason'), '\n\n') AS reason,
  google_url,
  close4_url,
  google_products,
  close4_products
FROM (
  SELECT
    country,
    query,
    google_url,
    close4_url,
    REGEXP_REPLACE(llm_response, r'```json|```', '') AS clean_json
  FROM `noonbigmerchsandbox.satyam.auto_analyser_v1_sa`
)
LEFT JOIN (
  SELECT country, query, google AS google_products, close4 AS close4_products
  FROM (
    WITH base AS (
      SELECT DISTINCT "SA" AS country, query, engine, index_position,
             title, brand, delivery_type_tag, units_l30d_norm
      FROM `noonbigmerchsandbox.satyam.llm_analytics_base2`
    )
    SELECT *
    FROM base
    PIVOT (
      ARRAY_AGG(STRUCT(index_position AS rank, title, brand, delivery_type_tag, units_l30d_norm)
                IGNORE NULLS ORDER BY index_position LIMIT 10)
      FOR engine IN ('google', 'close4')
    )
  )
) USING (country, query)
WHERE clean_json IS NOT NULL
"""

SUMMARY_SQL = """
SELECT
  country,
  REGEXP_REPLACE(overall_llm_response, r'```json|```', '') AS clean_json
FROM `noonbigmerchsandbox.satyam.auto_analyser_summary_sa`
"""

DELIVERY_BREAKDOWN_SQL = """
SELECT
  engine,
  delivery_type_tag,
  COUNT(*) AS product_count,
  ROUND(AVG(units_l30d_norm), 4) AS avg_popularity
FROM `noonbigmerchsandbox.satyam.llm_analytics_base2`
GROUP BY engine, delivery_type_tag
ORDER BY engine, delivery_type_tag
"""

SCORE_OVER_RANK_SQL = """
SELECT
  engine,
  index_position,
  ROUND(AVG(units_l30d_norm), 4) AS avg_popularity
FROM `noonbigmerchsandbox.satyam.llm_analytics_base2`
WHERE index_position <= 10
GROUP BY engine, index_position
ORDER BY engine, index_position
"""
