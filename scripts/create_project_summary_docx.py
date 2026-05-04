from __future__ import annotations

import html
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Patent_Project_Presentation_Summary.docx"


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def paragraph(text: str = "", style: str | None = None) -> str:
    style_xml = ""
    if style:
        style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
    runs = "".join(f"<w:r><w:t>{esc(part)}</w:t></w:r>" for part in text.split("\n"))
    return f"<w:p>{style_xml}{runs}</w:p>"


def bullet(text: str) -> str:
    return paragraph(f"- {text}", "BodyText")


def heading(text: str, level: int = 1) -> str:
    return paragraph(text, f"Heading{level}")


def build_document_xml() -> str:
    sections: list[str] = []

    sections.append(heading("Global Patent Intelligence Project Presentation Summary", 1))
    sections.append(paragraph("Prepared for the project presentation and supervisor discussion."))
    sections.append(paragraph("Project folder: big-data-project-main"))

    sections.append(heading("1. Project Purpose", 1))
    sections.append(
        paragraph(
            "The purpose of this project is to convert large PatentsView TSV files into a clean, queryable, "
            "and presentable patent intelligence system. The pipeline starts from raw tab-separated files, "
            "cleans and reduces them into structured CSV datasets, loads them into a SQLite database, runs SQL "
            "analytics, exports report files, and displays the results in a Streamlit dashboard."
        )
    )
    sections.append(
        paragraph(
            "The project is important from a Big Data perspective because the raw files are too large and too "
            "messy to analyze comfortably by opening them directly. Instead, the system uses chunked processing, "
            "deduplication, relational modeling, SQL queries, and summarized reporting outputs."
        )
    )

    sections.append(heading("2. Raw TSV Files Provided", 1))
    sections.append(
        paragraph(
            "The raw files live in data/raw/. They are PatentsView granted patent datasets. TSV means tab-separated "
            "values, so each row is a record and each field is separated by a tab character."
        )
    )
    for item in [
        "g_patent.tsv: main patent records, including patent ID, title, date, and status fields.",
        "g_patent_abstract.tsv: patent abstracts. This is joined to g_patent.tsv using patent_id.",
        "g_inventor_disambiguated.tsv: inventor records. This connects patents to inventor IDs and inventor names.",
        "g_persistent_assignee.tsv or assignee source file: assignee/company records used to identify organizations behind patents.",
        "g_location_disambiguated.tsv: location lookup used to map inventor locations to countries.",
        "PV_grant_data_dictionary.pdf: reference documentation explaining the raw PatentsView fields.",
    ]:
        sections.append(bullet(item))

    sections.append(heading("3. Data Processing Script: scripts/build_pipeline.py", 1))
    sections.append(
        paragraph(
            "This script is the ETL layer: Extract, Transform, Load. It extracts the raw TSV data, transforms it into "
            "clean and smaller CSV files, then loads those files into a relational database."
        )
    )

    sections.append(heading("3.1 normalise_text(series)", 2))
    sections.append(
        paragraph(
            "This helper function cleans text columns by replacing missing values with empty strings, converting values "
            "to strings, reducing repeated whitespace, and trimming spaces at the beginning and end. This matters because "
            "raw big datasets often contain inconsistent spacing and missing values. Without this step, duplicate names "
            "or blank fields could be treated incorrectly."
        )
    )

    sections.append(heading("3.2 write_chunk(frame, path, first_chunk)", 2))
    sections.append(
        paragraph(
            "This function writes data to CSV in chunks. The first chunk writes headers, while later chunks append rows. "
            "This is important because the project handles large files that should not all be loaded into memory at once."
        )
    )

    sections.append(heading("3.3 build_location_lookup()", 2))
    sections.append(
        paragraph(
            "This function reads the location file and creates a dictionary mapping location_id to country. The country "
            "field is later added to inventors. This allows the project to analyze patent activity by country instead "
            "of only by inventor or company."
        )
    )

    sections.append(heading("3.4 process_patents(limit, chunk_size, sample_step)", 2))
    sections.append(
        paragraph(
            "This function processes g_patent.tsv together with g_patent_abstract.tsv. It joins abstracts to patents "
            "using patent_id, removes withdrawn patents, keeps useful fields, extracts the year from the filing date, "
            "drops invalid records, and writes data/processed/clean_patents.csv."
        )
    )
    for item in [
        "patent_id is kept as the primary identifier.",
        "title and abstract are cleaned text fields used for understanding the patent.",
        "filing_date records the date of the patent.",
        "year is extracted so trends can be analyzed over time.",
        "sample_step can keep every Nth patent when a lighter sample is needed.",
    ]:
        sections.append(bullet(item))

    sections.append(heading("3.5 process_inventors(selected_ids, chunk_size, country_lookup)", 2))
    sections.append(
        paragraph(
            "This function processes inventor data. It creates two outputs: clean_inventors.csv and "
            "clean_patent_inventors.csv. The first file stores unique inventors, their names, and countries. The second "
            "file stores relationships between patents and inventors."
        )
    )
    sections.append(
        paragraph(
            "This separation is important because one patent can have many inventors, and one inventor can appear on "
            "many patents. That is a many-to-many relationship, so it needs a link table instead of repeating all "
            "inventor details inside the patent table."
        )
    )

    sections.append(heading("3.6 process_companies(selected_ids, chunk_size)", 2))
    sections.append(
        paragraph(
            "This function processes assignee/company data. It creates clean_companies.csv and clean_patent_companies.csv. "
            "The company file stores unique organizations, while the patent-company file links each patent to its primary "
            "company or assignee."
        )
    )
    sections.append(
        paragraph(
            "This step is important because company analytics answer questions such as which organizations have the "
            "largest patent portfolios and whether the market is concentrated among a few companies."
        )
    )

    sections.append(heading("3.7 deduplicate_clean_file(path, subset)", 2))
    sections.append(
        paragraph(
            "This helper removes duplicate rows from the cleaned outputs using key columns such as patent_id, inventor_id, "
            "or company_id. It improves data quality before loading the database."
        )
    )

    sections.append(heading("3.8 build_database(chunk_size)", 2))
    sections.append(
        paragraph(
            "This function creates data/db/patent_intelligence.db. It applies the SQL schema, loads the cleaned CSV files "
            "into database tables, and creates a relationships table joining patents, inventors, and companies."
        )
    )
    sections.append(
        paragraph(
            "This matters because a database is better than plain CSV files for relational analysis. SQL can join tables, "
            "group records, rank results, calculate shares, and support dashboard queries efficiently."
        )
    )

    sections.append(heading("4. Cleaned Processed Files", 1))
    for item in [
        "data/processed/clean_patents.csv: one row per cleaned patent with patent_id, title, abstract, filing_date, and year.",
        "data/processed/clean_inventors.csv: one row per unique inventor with inventor_id, name, and country.",
        "data/processed/clean_companies.csv: one row per unique company or assignee with company_id and name.",
        "data/processed/clean_patent_inventors.csv: link table connecting patents to inventors.",
        "data/processed/clean_patent_companies.csv: link table connecting patents to companies.",
        "data/processed/clean_relationships.csv: combined relationship view linking patent_id, inventor_id, and company_id.",
        "data/processed/run_metadata.json: stores run settings such as chunk size, sample settings, and database path.",
    ]:
        sections.append(bullet(item))

    sections.append(heading("5. Database Design", 1))
    sections.append(
        paragraph(
            "The database schema is defined in sql/schema.sql. The database is stored as "
            "data/db/patent_intelligence.db. The main tables are patents, inventors, companies, patent_inventors, "
            "patent_companies, and relationships."
        )
    )
    for item in [
        "patents: stores core patent information and uses patent_id as the primary key.",
        "inventors: stores unique inventors and their countries.",
        "companies: stores unique assignees or companies.",
        "patent_inventors: handles the many-to-many relationship between patents and inventors.",
        "patent_companies: handles the relationship between patents and companies.",
        "relationships: combines patent-inventor-company links for easier reporting and joined views.",
        "Indexes are created on common join columns to improve query speed.",
    ]:
        sections.append(bullet(item))

    sections.append(heading("6. SQL Analytics: sql/queries.sql", 1))
    sections.append(
        paragraph(
            "The SQL file stores named queries used by the report generator. Keeping queries in sql/queries.sql makes "
            "the project easier to explain and maintain because the analytical logic is separate from Python code."
        )
    )
    for item in [
        "q1_top_inventors: identifies inventors with the strongest patent activity.",
        "q2_top_companies: identifies companies with the largest patent portfolios.",
        "q3_top_countries: calculates country patent totals and country share.",
        "q4_yearly_trends: produces the yearly trend used for descriptive and predictive analytics.",
        "q5_join_query: produces a readable joined view of patents, inventors, and companies.",
        "q6_cte_query: uses common table expressions to calculate average patents per inventor by country.",
        "q7_ranking_query: uses SQL ranking to rank inventors by patent activity.",
        "q8_company_concentration: supports diagnostic analytics by calculating company portfolio concentration.",
        "q9_country_yearly_share: supports diagnostic analytics by tracking how each country's share changes by year.",
    ]:
        sections.append(bullet(item))

    sections.append(heading("7. Report Generation: scripts/generate_reports.py", 1))
    sections.append(
        paragraph(
            "This script reads the SQLite database, runs the SQL queries, creates CSV report files, builds a JSON summary, "
            "and prints a console report. It is the main reporting layer requested by the supervisor."
        )
    )
    for item in [
        "fetch_query(conn, sql): runs a SQL query and returns a pandas DataFrame.",
        "add_share(frame, count_column): calculates share values so reports are not only raw counts.",
        "build_yearly_diagnostics(yearly_trends): calculates previous-year patents, year-over-year change, growth rate, and rolling averages.",
        "build_patent_forecast(yearly_trends): creates a three-year patent forecast using a linear trend from the last 10 years.",
        "classify_growth(rate): labels movement as rapid growth, moderate growth, stable, moderate decline, or sharp decline.",
        "load_queries(): reads named SQL queries from sql/queries.sql.",
        "main(): coordinates all report generation and exports the final files.",
    ]:
        sections.append(bullet(item))

    sections.append(heading("8. Report Outputs", 1))
    for item in [
        "reports/top_inventors.csv: descriptive report showing leading inventors.",
        "reports/top_companies.csv: descriptive report showing leading companies.",
        "reports/country_trends.csv: descriptive report showing country patent totals and shares.",
        "reports/yearly_patent_trends.csv: yearly patent volumes used for trend analysis.",
        "reports/diagnostic_yearly_growth.csv: diagnostic report showing year-over-year changes and growth rates.",
        "reports/company_concentration.csv: diagnostic report showing company share, cumulative share, and concentration bands.",
        "reports/country_share_diagnostics.csv: diagnostic report showing how country patent shares change over time.",
        "reports/patent_forecast.csv: predictive report forecasting patent volume for the next three years.",
        "reports/report_summary.json: machine-readable summary containing descriptive, diagnostic, and predictive analytics.",
        "reports/console_report.txt: saved version of the terminal report.",
        "reports/joined_patent_view.csv: sample joined view for explaining relationships.",
        "reports/ranked_inventors.csv: ranking output using SQL window functions.",
    ]:
        sections.append(bullet(item))

    sections.append(heading("9. Analytics Types Included", 1))
    sections.append(heading("9.1 Descriptive Analytics", 2))
    sections.append(
        paragraph(
            "Descriptive analytics answer: What happened? In this project, descriptive analytics include patent totals, "
            "top inventors, top companies, top countries, and yearly patent activity. However, the dashboard does not rely "
            "only on counts; it also shows shares and trends."
        )
    )
    sections.append(heading("9.2 Diagnostic Analytics", 2))
    sections.append(
        paragraph(
            "Diagnostic analytics answer: Why did it happen or what explains the pattern? The project includes year-over-year "
            "growth rates, rolling averages, company concentration, country share movement, and growth labels. These help "
            "explain whether patent activity is rising, falling, concentrated, fragmented, or shifting between countries."
        )
    )
    sections.append(heading("9.3 Predictive Analytics", 2))
    sections.append(
        paragraph(
            "Predictive analytics answer: What is likely to happen next? The project creates a three-year forecast using "
            "recent yearly patent volumes and a linear trend model. This is intentionally simple and explainable for a "
            "course project. It gives a baseline forecast that can later be improved with more advanced models."
        )
    )

    sections.append(heading("10. Streamlit Dashboard: dashboard.py", 1))
    sections.append(
        paragraph(
            "The dashboard is the presentation layer. It reads the exported report CSV files and the SQLite database, then "
            "presents the results visually. It helps non-technical readers understand the data without opening raw files "
            "or writing SQL."
        )
    )
    for item in [
        "load_csv(name): loads report CSV files from the reports folder.",
        "load_totals(): queries the database for total patents, inventors, and companies.",
        "load_recent_patents(limit): retrieves recent patent records from the database.",
        "Analytics Overview: displays headline metrics such as latest growth, top company share, HHI, fastest country share growth, and forecast.",
        "Descriptive tab: shows patent trend by year, top country share, top inventors, and top companies.",
        "Diagnostic tab: shows year-over-year growth, company portfolio concentration, and country share diagnostics.",
        "Predictive tab: shows actual versus forecast patent volume.",
        "Recent Patent Records: gives examples of actual patent records supporting the analysis.",
    ]:
        sections.append(bullet(item))

    sections.append(heading("11. Why the Dashboard Graph Titles Were Added", 1))
    sections.append(
        paragraph(
            "Each graph now has a clear title so readers immediately know what the visual is explaining. This improves "
            "presentation quality because a supervisor or audience member should not have to guess the meaning of a chart."
        )
    )
    for item in [
        "Patent Volume Trend by Year: shows how patent volume changes across years.",
        "Top Countries by Patent Share: shows relative country contribution, not just counts.",
        "Year-over-Year Patent Growth Rate: shows whether patent volume is increasing or decreasing.",
        "Top 20 Companies by Patent Portfolio Share: shows how concentrated patents are among companies.",
        "Actual vs Forecast Patent Volume: compares historical data with predicted future values.",
    ]:
        sections.append(bullet(item))

    sections.append(heading("12. Commands to Run the Project", 1))
    sections.append(paragraph("Build or rebuild the database from existing processed CSV files:"))
    sections.append(paragraph(r".\venv\Scripts\python.exe .\scripts\build_pipeline.py --skip-patents --skip-inventors --skip-companies"))
    sections.append(paragraph("Generate reports:"))
    sections.append(paragraph(r".\venv\Scripts\python.exe .\scripts\generate_reports.py"))
    sections.append(paragraph("Run the dashboard:"))
    sections.append(paragraph(r"python -m streamlit run .\dashboard.py"))

    sections.append(heading("13. Questions the Supervisor May Ask", 1))
    qa = [
        (
            "Why use chunks?",
            "The raw TSV files can be large, so chunks reduce memory pressure and make the pipeline scalable.",
        ),
        (
            "Why use a database instead of only CSV?",
            "The database supports joins, grouping, indexing, ranking, and cleaner relational analysis.",
        ),
        (
            "Why separate patents, inventors, and companies?",
            "Because patents, inventors, and companies have many-to-many relationships. Separate tables avoid duplication and improve data integrity.",
        ),
        (
            "Why include share and growth instead of only counts?",
            "Counts are useful but basic. Share shows relative importance, and growth shows change over time.",
        ),
        (
            "What does HHI mean?",
            "HHI is a concentration index. A low value suggests patents are spread across many companies; a high value suggests dominance by a few companies.",
        ),
        (
            "Why use a simple linear forecast?",
            "It is explainable and appropriate as a baseline predictive model. More complex models can be added later.",
        ),
        (
            "What makes this a Big Data project?",
            "It uses large raw TSV files, chunked processing, cleaning, transformation, relational modeling, SQL analytics, and dashboard reporting.",
        ),
    ]
    for question, answer in qa:
        sections.append(paragraph(f"Q: {question}", "BodyText"))
        sections.append(paragraph(f"A: {answer}", "BodyText"))

    sections.append(heading("14. Final Presentation Message", 1))
    sections.append(
        paragraph(
            "This project demonstrates a complete data pipeline: raw patent data was cleaned, transformed, modeled in a "
            "database, analyzed using SQL and Python, exported into required report formats, and visualized in a dashboard. "
            "The final system goes beyond basic counts by including descriptive, diagnostic, and predictive analytics."
        )
    )

    body = "".join(sections)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""


def rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""


def document_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""


def styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="BodyText">
    <w:name w:val="Body Text"/>
    <w:pPr><w:spacing w:after="120"/></w:pPr>
    <w:rPr><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:pPr><w:spacing w:before="360" w:after="160"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="26"/></w:rPr>
  </w:style>
</w:styles>
"""


def main() -> None:
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types_xml())
        docx.writestr("_rels/.rels", rels_xml())
        docx.writestr("word/_rels/document.xml.rels", document_rels_xml())
        docx.writestr("word/styles.xml", styles_xml())
        docx.writestr("word/document.xml", build_document_xml())
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
