import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "db" / "patent_intelligence.db"
REPORTS_DIR = BASE_DIR / "reports"


@st.cache_data
def load_csv(name):
    return pd.read_csv(REPORTS_DIR / name)


@st.cache_data
def load_totals():
    conn = sqlite3.connect(DB_PATH)
    try:
        totals = {
            "patents": pd.read_sql_query("SELECT COUNT(*) AS total FROM patents", conn).iloc[0]["total"],
            "inventors": pd.read_sql_query("SELECT COUNT(*) AS total FROM inventors", conn).iloc[0]["total"],
            "companies": pd.read_sql_query("SELECT COUNT(*) AS total FROM companies", conn).iloc[0]["total"],
            "avg_weight": pd.read_sql_query(
                "SELECT ROUND(AVG(patent_weight), 2) AS total FROM patent_metrics", conn
            ).iloc[0]["total"],
        }
    finally:
        conn.close()
    return totals


@st.cache_data
def load_recent_patents(limit):
    conn = sqlite3.connect(DB_PATH)
    try:
        query = """
        SELECT p.patent_id, p.title, p.year, pm.patent_weight, pm.dependency_count
        FROM patents p
        LEFT JOIN patent_metrics pm
            ON p.patent_id = pm.patent_id
        ORDER BY p.year DESC, p.patent_id DESC
        LIMIT ?
        """
        frame = pd.read_sql_query(query, conn, params=(limit,))
    finally:
        conn.close()
    return frame


def year_index(frame, value_column):
    display = frame.copy()
    display["year"] = display["year"].astype(int).astype(str)
    return display.set_index("year")[value_column]


def display_years(frame):
    display = frame.copy()
    if "year" in display.columns:
        display["year"] = display["year"].astype(int).astype(str)
    return display


def main():
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
    processing_time = load_csv("processing_time.csv")
    patent_weight_distribution = load_csv("patent_weight_distribution.csv")
    top_weighted_patents = load_csv("top_weighted_patents.csv")
    dependency_distribution = load_csv("dependency_distribution.csv")
    type_distribution = load_csv("type_distribution_over_time.csv")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Patents", f"{int(totals['patents']):,}")
    col2.metric("Inventors", f"{int(totals['inventors']):,}")
    col3.metric("Companies", f"{int(totals['companies']):,}")
    col4.metric("Avg Patent Weight", f"{float(totals['avg_weight']):.2f}")

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

    descriptive_tab, diagnostic_tab, weight_tab, distribution_tab, predictive_tab = st.tabs(
        ["Descriptive", "Diagnostic", "Weights", "Distributions", "Predictive"]
    )

    with descriptive_tab:
        st.subheader("Descriptive Analytics")
        left, right = st.columns(2)

        with left:
            st.markdown("#### Patent Volume Trend by Year")
            st.line_chart(year_index(yearly_trends, "patent_count"))
            st.markdown("Recent yearly patent totals")
            st.dataframe(display_years(yearly_trends.tail(15)), use_container_width=True, hide_index=True)

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
            st.line_chart(year_index(yearly_diagnostics, "yoy_growth_rate"))
            st.markdown("Yearly growth diagnostics")
            st.dataframe(
                display_years(yearly_diagnostics.tail(15)),
                use_container_width=True,
                hide_index=True,
            )

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
        st.dataframe(
            display_years(recent_country_diagnostics),
            use_container_width=True,
            hide_index=True,
        )

    with weight_tab:
        st.subheader("Patent Weight and Dependencies")
        left, right = st.columns(2)

        with left:
            st.markdown("#### Average Patent Weight Over Time")
            st.line_chart(year_index(patent_weight_distribution, "avg_patent_weight"))
            st.markdown("Patent weight distribution by year")
            st.dataframe(
                display_years(patent_weight_distribution.tail(15)),
                use_container_width=True,
                hide_index=True,
            )

        with right:
            st.markdown("#### Average Dependencies Over Time")
            st.line_chart(year_index(patent_weight_distribution, "avg_dependencies"))
            st.markdown("Latest processing time")
            st.dataframe(processing_time, use_container_width=True, hide_index=True)

        st.markdown("#### Top Weighted Patents")
        st.dataframe(top_weighted_patents, use_container_width=True, hide_index=True)

    with distribution_tab:
        st.subheader("Distribution Changes Over Time")
        left, right = st.columns(2)

        with left:
            dependency_recent = dependency_distribution[
                dependency_distribution["year"]
                >= dependency_distribution["year"].max() - 10
            ]
            dependency_pivot = dependency_recent.pivot_table(
                index="year",
                columns="dependency_count",
                values="patent_count",
                aggfunc="sum",
                fill_value=0,
            )
            dependency_pivot.index = dependency_pivot.index.astype(int).astype(str)
            st.markdown("#### Dependency Count Distribution")
            st.bar_chart(dependency_pivot)

        with right:
            type_recent = type_distribution[
                type_distribution["year"] >= type_distribution["year"].max() - 10
            ]
            type_pivot = type_recent.pivot_table(
                index="year",
                columns="patent_type",
                values="yearly_share",
                aggfunc="sum",
                fill_value=0,
            )
            type_pivot.index = type_pivot.index.astype(int).astype(str)
            st.markdown("#### Patent Type Share")
            st.line_chart(type_pivot)

        st.markdown("Dependency distribution table")
        st.dataframe(
            display_years(dependency_distribution.tail(50)),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("Patent type distribution table")
        st.dataframe(
            display_years(type_distribution.tail(50)),
            use_container_width=True,
            hide_index=True,
        )

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
        forecast_chart.index = forecast_chart.index.astype(int).astype(str)
        st.markdown("#### Actual vs Forecast Patent Volume")
        st.line_chart(forecast_chart)
        st.markdown("Three-year patent volume forecast")
        st.dataframe(display_years(patent_forecast), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Recent Patent Records")
    row_limit = st.slider("Number of rows to show", 5, 25, 10)
    st.dataframe(
        display_years(load_recent_patents(row_limit)),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
