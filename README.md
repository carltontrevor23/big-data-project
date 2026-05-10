# Global Patent Intelligence Data Pipeline

This project builds a small patent data pipeline with PatentsView granted patent files. The flow is:

raw TSV files -> Data cleaning using pandas  -> SQLite database -> SQL analysis -> CSV/JSON/console reports

The reporting layer covers three analytics types in addition to the patent metrics:

- Descriptive analytics: rankings, country shares, yearly patent trend tables
- Diagnostic analytics: year-over-year growth, company concentration, country share movement
- Predictive analytics: a three-year patent-volume forecast using a recent linear trend model
- Patent processing and weight analytics: pipeline processing time, claim-based patent weight, dependency counts, and distribution changes over time

## Project layout

- `scripts/build_pipeline.py` cleans the raw files and loads the SQLite database
- `scripts/generate_reports.py` runs the SQL queries and exports the reports
- `dashboard.py` shows a simple Streamlit dashboard from the saved outputs
- `sql/schema.sql` creates the tables
- `sql/queries.sql` stores the analysis queries
- `data/processed/` keeps the cleaned CSV files
- `data/db/patent_intelligence.db` is the SQLite database, including patent metrics and run timing
- `reports/` contains the exported report files

## Raw files used

The raw PatentsView files in `data/raw/`:

- `g_patent.tsv`
- `g_patent_abstract.tsv`
- `g_inventor_disambiguated.tsv`
- `g_assignee_disambiguated.tsv`

## How to run the scripts

Activate the virtual environment and run:

```powershell
.\venv\Scripts\Activate.ps1
python .\scripts\build_pipeline.py 
python .\scripts\generate_reports.py
```

If you want to process the full dataset, leave out both `--patent-limit` and `--sample-step`.
If you want a smaller test run, use `--patent-limit`.

## Outputs

After the scripts finish, you should have:

- `data/processed/clean_patents.csv`
- `data/processed/clean_inventors.csv`
- `data/processed/clean_companies.csv`
- `data/processed/clean_relationships.csv`
- `data/db/patent_intelligence.db`
- `reports/top_inventors.csv`
- `reports/top_companies.csv`
- `reports/country_trends.csv`
- `reports/diagnostic_yearly_growth.csv`
- `reports/company_concentration.csv`
- `reports/country_share_diagnostics.csv`
- `reports/patent_forecast.csv`
- `reports/processing_time.csv`
- `reports/patent_weight_distribution.csv`
- `reports/top_weighted_patents.csv`
- `reports/dependency_distribution.csv`
- `reports/type_distribution_over_time.csv`
- `reports/report_summary.json`
- `reports/console_report.txt`

The console and JSON reports include descriptive, diagnostic, predictive, processing-time,
dependency, distribution, and patent-weight sections. The dashboard also has separate tabs for
each analytics type.

## Supervisor metrics

- **How long it takes to process patents:** the pipeline records end-to-end cleaning and SQLite
  loading time in the `pipeline_runs` table and exports it to `reports/processing_time.csv`.
- **Dependencies:** each patent gets inventor count, company count, and total dependency count in
  the `patent_metrics` table. In this version, dependencies mean linked inventors plus linked
  companies because citation/reference raw files are not present in `data/raw/`.
- **Weight of patent:** each patent receives a simple weight score:
  `num_claims + 0.10 * title_word_count + 0.01 * abstract_word_count`.
  This uses available fields from `g_patent.tsv` and `g_patent_abstract.tsv`.
- **How the distribution changes over time:** yearly reports show patent count, average weight,
  average claims, average dependencies, patent type shares, and dependency-count distributions.
- **Store in a DB:** all cleaned records and derived metrics are stored in
  `data/db/patent_intelligence.db`.

True patent office processing time, meaning application filing date to grant date, requires an
application-date file such as PatentsView `g_application.tsv`. The current raw files include grant
date but not application filing date, so that metric is documented as a future enhancement once the
extra source file is added.

## Dashboard

If you want to view the project in a small dashboard, install Streamlit in the same virtual environment:

```powershell
python -m pip install streamlit
```

Then run:

```powershell
python -m streamlit run .\dashboard.py
```

Streamlit will show a local address in the terminal, usually `http://localhost:8501`.

## Notes

- The patent file and abstract file are processed in chunks so the project can run on a normal laptop.
- The relationship table links each patent-inventor pair with the primary assignee for that patent.
- Countries depend on the optional location lookup file. Without it, the country analysis still runs but the values will be `Unknown`.
