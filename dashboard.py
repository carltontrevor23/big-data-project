from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "db" / "patent_intelligence.db"
REPORTS_DIR = BASE_DIR / "reports"


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(REPORTS_DIR / name)


@st.cache_data
def load_totals() -> dict[str, int]:
    conn = sqlite3.connect(DB_PATH)
    try:
        totals = {
            "patents": pd.read_sql_query("SELECT COUNT(*) AS total FROM patents", conn).iloc[0]["total"],
            "inventors": pd.read_sql_query("SELECT COUNT(*) AS total FROM inventors", conn).iloc[0]["total"],
            "companies": pd.read_sql_query("SELECT COUNT(*) AS total FROM companies", conn).iloc[0]["total"],
        }
    finally:
        conn.close()
    return totals


@st.cache_data
def load_recent_patents(limit: int) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        query = """
        SELECT patent_id, title, year
        FROM patents
        ORDER BY year DESC, patent_id DESC
        LIMIT ?
        """
        frame = pd.read_sql_query(query, conn, params=(limit,))
    finally:
        conn.close()
    return frame


def main() -> None:
    st.set_page_config(page_title="Patent Dashboard", layout="wide")
    st.title("Global Patent Intelligence Dashboard")
    st.caption("Small Streamlit view for the patent pipeline outputs.")

    if not DB_PATH.exists():
        st.error("Database file not found. Run the pipeline first.")
        return

    totals = load_totals()
    top_inventors = load_csv("top_inventors.csv")
    top_companies = load_csv("top_companies.csv")
    top_countries = load_csv("country_trends.csv")
    yearly_trends = load_csv("yearly_patent_trends.csv")

    col1, col2, col3 = st.columns(3)
    col1.metric("Patents", f"{int(totals['patents']):,}")
    col2.metric("Inventors", f"{int(totals['inventors']):,}")
    col3.metric("Companies", f"{int(totals['companies']):,}")

    left, right = st.columns(2)

    with left:
        st.subheader("Patents by Year")
        st.line_chart(yearly_trends.set_index("year")["patent_count"])
        st.dataframe(yearly_trends.tail(15), use_container_width=True, hide_index=True)

    with right:
        st.subheader("Top Countries")
        st.bar_chart(top_countries.set_index("country")["patent_count"])
        st.dataframe(top_countries, use_container_width=True, hide_index=True)

    left, right = st.columns(2)

    with left:
        st.subheader("Top Inventors")
        st.bar_chart(top_inventors.set_index("name")["patent_count"])
        st.dataframe(top_inventors, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Top Companies")
        st.bar_chart(top_companies.set_index("name")["patent_count"])
        st.dataframe(top_companies, use_container_width=True, hide_index=True)

    st.subheader("Recent Patent Records")
    row_limit = st.slider("Number of rows to show", 5, 25, 10)
    st.dataframe(load_recent_patents(row_limit), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
