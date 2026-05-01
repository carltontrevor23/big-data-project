from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "db" / "patent_intelligence.db"
REPORTS_DIR = ROOT / "reports"
SQL_DIR = ROOT / "sql"


def fetch_query(conn: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)


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
        yearly_trends = fetch_query(conn, queries["q4_yearly_trends"])
        joined_view = fetch_query(conn, queries["q5_join_query"])
        cte_result = fetch_query(conn, queries["q6_cte_query"])
        ranked_inventors = fetch_query(conn, queries["q7_ranking_query"])

        top_inventors.to_csv(REPORTS_DIR / "top_inventors.csv", index=False)
        top_companies.to_csv(REPORTS_DIR / "top_companies.csv", index=False)
        top_countries.to_csv(REPORTS_DIR / "country_trends.csv", index=False)
        yearly_trends.to_csv(REPORTS_DIR / "yearly_patent_trends.csv", index=False)
        joined_view.to_csv(REPORTS_DIR / "joined_patent_view.csv", index=False)
        ranked_inventors.to_csv(REPORTS_DIR / "ranked_inventors.csv", index=False)

        summary = {
            "total_patents": int(total_patents.loc[0, "total_patents"]),
            "top_inventors": top_inventors.to_dict(orient="records"),
            "top_companies": top_companies.to_dict(orient="records"),
            "top_countries": top_countries.to_dict(orient="records"),
            "yearly_trends": yearly_trends.to_dict(orient="records"),
            "cte_result": cte_result.to_dict(orient="records"),
        }
        (REPORTS_DIR / "report_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

        report_lines = [
            "================== PATENT REPORT ==================",
            f"Total Patents: {summary['total_patents']:,}",
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
            report_lines.append(f"{idx + 1}. {row['country']} - {int(row['patent_count']):,}")

        report_lines.extend(["", "Patents by Year:"])
        for _, row in yearly_trends.tail(10).iterrows():
            report_lines.append(f"{int(row['year'])}: {int(row['patent_count']):,}")

        console_text = "\n".join(report_lines)
        print(console_text)
        (REPORTS_DIR / "console_report.txt").write_text(console_text, encoding="utf-8")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
