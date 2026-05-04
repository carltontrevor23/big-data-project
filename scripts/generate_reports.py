from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "db" / "patent_intelligence.db"
REPORTS_DIR = ROOT / "reports"
SQL_DIR = ROOT / "sql"


def fetch_query(conn: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)


def add_share(frame: pd.DataFrame, count_column: str, share_column: str = "share") -> pd.DataFrame:
    total = frame[count_column].sum()
    frame = frame.copy()
    frame[share_column] = 0.0 if total == 0 else (frame[count_column] / total).round(4)
    return frame


def build_yearly_diagnostics(yearly_trends: pd.DataFrame) -> pd.DataFrame:
    diagnostics = yearly_trends.copy()
    diagnostics["previous_year_patents"] = diagnostics["patent_count"].shift(1)
    diagnostics["yoy_change"] = diagnostics["patent_count"] - diagnostics["previous_year_patents"]
    diagnostics["yoy_growth_rate"] = (
        diagnostics["yoy_change"] / diagnostics["previous_year_patents"]
    ).replace([np.inf, -np.inf], np.nan)
    diagnostics["rolling_3yr_avg"] = diagnostics["patent_count"].rolling(3, min_periods=1).mean()
    diagnostics["yoy_change"] = diagnostics["yoy_change"].fillna(0).astype(int)
    diagnostics["yoy_growth_rate"] = diagnostics["yoy_growth_rate"].fillna(0).round(4)
    diagnostics["rolling_3yr_avg"] = diagnostics["rolling_3yr_avg"].round(2)
    diagnostics["previous_year_patents"] = diagnostics["previous_year_patents"].fillna(0).astype(int)
    return diagnostics


def build_patent_forecast(yearly_trends: pd.DataFrame, years_ahead: int = 3) -> pd.DataFrame:
    recent_years = yearly_trends.tail(10).copy()
    if len(recent_years) < 2:
        return pd.DataFrame(columns=["year", "predicted_patents", "model", "trend_slope"])

    x = recent_years["year"].astype(float).to_numpy()
    y = recent_years["patent_count"].astype(float).to_numpy()
    slope, intercept = np.polyfit(x, y, 1)
    future_years = np.arange(int(x.max()) + 1, int(x.max()) + years_ahead + 1)
    predictions = np.maximum(0, np.round((slope * future_years) + intercept).astype(int))

    return pd.DataFrame(
        {
            "year": future_years,
            "predicted_patents": predictions,
            "model": "linear trend from last 10 years",
            "trend_slope": round(float(slope), 2),
        }
    )


def classify_growth(rate: float) -> str:
    if rate >= 0.10:
        return "rapid growth"
    if rate >= 0.03:
        return "moderate growth"
    if rate <= -0.10:
        return "sharp decline"
    if rate <= -0.03:
        return "moderate decline"
    return "stable"


def load_queries() -> dict[str, str]:
    queries: dict[str, str] = {}
    current_name = None
    current_lines: list[str] = []

    for line in (SQL_DIR / "queries.sql").read_text(encoding="utf-8").splitlines():
        if line.startswith("-- name:"):
            if current_name and current_lines:
                queries[current_name] = "\n".join(current_lines).strip()
            current_name = line.split(":", 1)[1].strip()
            current_lines = []
            continue
        current_lines.append(line)

    if current_name and current_lines:
        queries[current_name] = "\n".join(current_lines).strip()

    return queries


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    queries = load_queries()

    conn = sqlite3.connect(DB_PATH)
    try:
        total_patents = fetch_query(conn, "SELECT COUNT(*) AS total_patents FROM patents")
        top_inventors = fetch_query(conn, queries["q1_top_inventors"])
        top_companies = fetch_query(conn, queries["q2_top_companies"])
        top_countries = fetch_query(conn, queries["q3_top_countries"])
        if "share" not in top_countries.columns:
            top_countries = add_share(top_countries, "patent_count")
        yearly_trends = fetch_query(conn, queries["q4_yearly_trends"])
        joined_view = fetch_query(conn, queries["q5_join_query"])
        cte_result = fetch_query(conn, queries["q6_cte_query"])
        ranked_inventors = fetch_query(conn, queries["q7_ranking_query"])
        company_concentration = add_share(
            fetch_query(conn, queries["q8_company_concentration"]), "patent_count"
        )
        country_yearly_share = fetch_query(conn, queries["q9_country_yearly_share"])

        yearly_diagnostics = build_yearly_diagnostics(yearly_trends)
        patent_forecast = build_patent_forecast(yearly_trends)
        company_concentration["cumulative_share"] = company_concentration["share"].cumsum().round(4)
        company_concentration["concentration_band"] = pd.cut(
            company_concentration["share"],
            bins=[-0.01, 0.01, 0.05, 1.0],
            labels=["fragmented", "meaningful", "dominant"],
        ).astype(str)
        country_yearly_share["share_growth_rate"] = (
            country_yearly_share.groupby("country")["share"].pct_change()
        ).replace([np.inf, -np.inf], np.nan)
        country_yearly_share["share_growth_rate"] = (
            country_yearly_share["share_growth_rate"].fillna(0).round(4)
        )
        country_yearly_share["diagnosis"] = country_yearly_share["share_growth_rate"].apply(
            classify_growth
        )

        top_inventors_report = top_inventors.rename(columns={"patent_count": "patents"})
        top_companies_report = top_companies.rename(columns={"patent_count": "patents"})
        top_countries_report = top_countries.rename(columns={"patent_count": "patents"})

        top_inventors.to_csv(REPORTS_DIR / "top_inventors.csv", index=False)
        top_companies.to_csv(REPORTS_DIR / "top_companies.csv", index=False)
        top_countries.to_csv(REPORTS_DIR / "country_trends.csv", index=False)
        yearly_trends.to_csv(REPORTS_DIR / "yearly_patent_trends.csv", index=False)
        joined_view.to_csv(REPORTS_DIR / "joined_patent_view.csv", index=False)
        ranked_inventors.to_csv(REPORTS_DIR / "ranked_inventors.csv", index=False)
        yearly_diagnostics.to_csv(REPORTS_DIR / "diagnostic_yearly_growth.csv", index=False)
        company_concentration.to_csv(REPORTS_DIR / "company_concentration.csv", index=False)
        country_yearly_share.to_csv(REPORTS_DIR / "country_share_diagnostics.csv", index=False)
        patent_forecast.to_csv(REPORTS_DIR / "patent_forecast.csv", index=False)

        latest_growth = yearly_diagnostics.iloc[-1]
        latest_country_year = country_yearly_share[
            country_yearly_share["year"] == country_yearly_share["year"].max()
        ]
        latest_country_year = latest_country_year[latest_country_year["patent_count"] >= 10]
        fastest_country = latest_country_year.sort_values(
            ["year", "share_growth_rate"], ascending=[False, False]
        ).head(1)
        top_5_company_share = float(company_concentration["share"].head(5).sum().round(4))
        hhi = float((company_concentration["share"] ** 2).sum().round(4))

        summary = {
            "total_patents": int(total_patents.loc[0, "total_patents"]),
            "analytics_types": ["descriptive", "diagnostic", "predictive"],
            "top_inventors": top_inventors_report[["name", "patents"]].to_dict(orient="records"),
            "top_companies": top_companies_report[["name", "patents"]].to_dict(orient="records"),
            "top_countries": top_countries_report[["country", "patents", "share"]].to_dict(
                orient="records"
            ),
            "yearly_trends": yearly_trends.to_dict(orient="records"),
            "diagnostic_insights": {
                "latest_year": int(latest_growth["year"]),
                "latest_yoy_growth_rate": float(latest_growth["yoy_growth_rate"]),
                "latest_yoy_change": int(latest_growth["yoy_change"]),
                "top_5_company_share": top_5_company_share,
                "company_hhi": hhi,
                "fastest_recent_country_share_growth": fastest_country.to_dict(orient="records"),
            },
            "predictive_forecast": patent_forecast.to_dict(orient="records"),
            "cte_result": cte_result.to_dict(orient="records"),
        }
        (REPORTS_DIR / "report_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

        report_lines = [
            "================== PATENT REPORT ==================",
            f"Total Patents: {summary['total_patents']:,}",
            "",
            "Descriptive Analytics:",
            "- Rank tables are included, but interpretation uses share and trend metrics.",
            "",
            "Top Inventors:",
        ]
        for idx, row in top_inventors.iterrows():
            report_lines.append(f"{idx + 1}. {row['name']} - {int(row['patent_count']):,}")

        report_lines.extend(["", "Top Companies:"])
        for idx, row in top_companies.iterrows():
            report_lines.append(f"{idx + 1}. {row['name']} - {int(row['patent_count']):,}")

        report_lines.extend(["", "Top Countries:"])
        for idx, row in top_countries.iterrows():
            share = float(row["share"]) * 100
            report_lines.append(
                f"{idx + 1}. {row['country']} - {int(row['patent_count']):,} ({share:.2f}%)"
            )

        report_lines.extend(["", "Patents by Year:"])
        for _, row in yearly_trends.tail(10).iterrows():
            report_lines.append(f"{int(row['year'])}: {int(row['patent_count']):,}")

        latest_growth_rate = float(latest_growth["yoy_growth_rate"]) * 100
        report_lines.extend(
            [
                "",
                "Diagnostic Analytics:",
                f"- Latest year-over-year change ({int(latest_growth['year'])}): "
                f"{int(latest_growth['yoy_change']):+,} patents ({latest_growth_rate:.2f}%).",
                f"- Top 5 company share: {top_5_company_share * 100:.2f}%.",
                f"- Company concentration index (HHI): {hhi:.4f}.",
            ]
        )
        if not fastest_country.empty:
            country_row = fastest_country.iloc[0]
            report_lines.append(
                f"- Fastest recent country share growth: {country_row['country']} "
                f"({float(country_row['share_growth_rate']) * 100:.2f}%)."
            )

        report_lines.extend(["", "Predictive Analytics:"])
        for _, row in patent_forecast.iterrows():
            report_lines.append(
                f"- {int(row['year'])}: {int(row['predicted_patents']):,} predicted patents "
                f"({row['model']})"
            )

        report_lines.extend(
            [
                "",
                "Exported Files:",
                "- reports/top_inventors.csv",
                "- reports/top_companies.csv",
                "- reports/country_trends.csv",
                "- reports/diagnostic_yearly_growth.csv",
                "- reports/company_concentration.csv",
                "- reports/country_share_diagnostics.csv",
                "- reports/patent_forecast.csv",
                "- reports/report_summary.json",
                "- reports/console_report.txt",
            ]
        )

        console_text = "\n".join(report_lines)
        print(console_text)
        (REPORTS_DIR / "console_report.txt").write_text(console_text, encoding="utf-8")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
