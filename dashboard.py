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
    yearly_diagnostics = load_csv("diagnostic_yearly_growth.csv")
    company_concentration = load_csv("company_concentration.csv")
    country_share_diagnostics = load_csv("country_share_diagnostics.csv")
    patent_forecast = load_csv("patent_forecast.csv")

    col1, col2, col3 = st.columns(3)
    col1.metric("Patents", f"{int(totals['patents']):,}")
    col2.metric("Inventors", f"{int(totals['inventors']):,}")
    col3.metric("Companies", f"{int(totals['companies']):,}")

    st.subheader("Analytics Overview")
    latest_growth = yearly_diagnostics.iloc[-1]
    top_5_company_share = company_concentration["share"].head(5).sum()
    hhi = (company_concentration["share"] ** 2).sum()
    latest_country_year = country_share_diagnostics[
        country_share_diagnostics["year"] == country_share_diagnostics["year"].max()
    ]
    latest_country_year = latest_country_year[latest_country_year["patent_count"] >= 10]
    if latest_country_year.empty:
        latest_country_year = country_share_diagnostics[
            country_share_diagnostics["year"] == country_share_diagnostics["year"].max()
        ]
    fastest_recent_country = latest_country_year.sort_values(
        ["year", "share_growth_rate"], ascending=[False, False]
    ).iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Latest YoY Growth",
        f"{float(latest_growth['yoy_growth_rate']) * 100:.2f}%",
        f"{int(latest_growth['yoy_change']):+,} patents",
    )
    col2.metric("Top 5 Company Share", f"{top_5_company_share * 100:.2f}%")
    col3.metric("Company HHI", f"{hhi:.4f}")

    col1, col2 = st.columns(2)
    col1.metric(
        "Fastest Recent Country Share Growth",
        str(fastest_recent_country["country"]),
        f"{float(fastest_recent_country['share_growth_rate']) * 100:.2f}%",
    )
    col2.metric(
        "Next Forecast Year",
        str(int(patent_forecast.iloc[0]["year"])),
        f"{int(patent_forecast.iloc[0]['predicted_patents']):,} predicted patents",
    )

    descriptive_tab, diagnostic_tab, predictive_tab = st.tabs(
        ["Descriptive", "Diagnostic", "Predictive"]
    )

    with descriptive_tab:
        st.subheader("Descriptive Analytics")
        left, right = st.columns(2)

        with left:
            st.markdown("#### Patent Volume Trend by Year")
            st.line_chart(yearly_trends.set_index("year")["patent_count"])
            st.markdown("Recent yearly patent totals")
            st.dataframe(yearly_trends.tail(15), use_container_width=True, hide_index=True)

        with right:
            country_display = top_countries.copy()
            country_display["share_percent"] = (country_display["share"] * 100).round(2)
            st.markdown("#### Top Countries by Patent Share")
            st.bar_chart(country_display.set_index("country")["share_percent"])
            st.markdown("Country share table")
            st.dataframe(country_display, use_container_width=True, hide_index=True)

        left, right = st.columns(2)

        with left:
            st.subheader("Top Inventors")
            st.dataframe(top_inventors, use_container_width=True, hide_index=True)

        with right:
            st.subheader("Top Companies")
            st.dataframe(top_companies, use_container_width=True, hide_index=True)

    with diagnostic_tab:
        st.subheader("Diagnostic Analytics")
        left, right = st.columns(2)

        with left:
            st.markdown("#### Year-over-Year Patent Growth Rate")
            st.line_chart(yearly_diagnostics.set_index("year")["yoy_growth_rate"])
            st.markdown("Yearly growth diagnostics")
            st.dataframe(yearly_diagnostics.tail(15), use_container_width=True, hide_index=True)

        with right:
            concentration_display = company_concentration.head(20).copy()
            concentration_display["share_percent"] = (
                concentration_display["share"] * 100
            ).round(2)
            st.markdown("#### Top 20 Companies by Patent Portfolio Share")
            st.bar_chart(concentration_display.set_index("name")["share_percent"])
            st.markdown("Company concentration diagnostics")
            st.dataframe(concentration_display, use_container_width=True, hide_index=True)

        recent_country_diagnostics = country_share_diagnostics.sort_values(
            ["year", "share_growth_rate"], ascending=[False, False]
        ).head(20)
        st.markdown("#### Recent Country Share Growth Diagnostics")
        st.dataframe(recent_country_diagnostics, use_container_width=True, hide_index=True)

    with predictive_tab:
        st.subheader("Predictive Analytics")
        combined = pd.concat(
            [
                yearly_trends.rename(columns={"patent_count": "patents"}).assign(series="actual"),
                patent_forecast.rename(columns={"predicted_patents": "patents"}).assign(
                    series="forecast"
                )[["year", "patents", "series"]],
            ],
            ignore_index=True,
        )
        forecast_chart = combined.pivot(index="year", columns="series", values="patents")
        st.markdown("#### Actual vs Forecast Patent Volume")
        st.line_chart(forecast_chart)
        st.markdown("Three-year patent volume forecast")
        st.dataframe(patent_forecast, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Recent Patent Records")
    row_limit = st.slider("Number of rows to show", 5, 25, 10)
    st.dataframe(load_recent_patents(row_limit), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
