from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DB_DIR = ROOT / "data" / "db"
SQL_DIR = ROOT / "sql"


def normalise_text(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def write_chunk(frame: pd.DataFrame, path: Path, first_chunk: bool) -> None:
    frame.to_csv(path, index=False, mode="w" if first_chunk else "a", header=first_chunk)


def load_selected_ids_from_clean_patents() -> set[str]:
    patent_file = PROCESSED_DIR / "clean_patents.csv"
    if not patent_file.exists():
        raise FileNotFoundError("clean_patents.csv was not found in data/processed")
    patents = pd.read_csv(patent_file, usecols=["patent_id"], dtype=str)
    return set(patents["patent_id"].dropna().astype(str))


def deduplicate_clean_file(path: Path, subset: list[str]) -> None:
    if not path.exists():
        return
    frame = pd.read_csv(path, dtype=str, low_memory=False)
    frame = frame.drop_duplicates(subset=subset)
    frame.to_csv(path, index=False)


def build_location_lookup() -> dict[str, str]:
    location_file = RAW_DIR / "g_location_disambiguated.tsv"
    if not location_file.exists():
        return {}

    sample = pd.read_csv(location_file, sep="\t", nrows=5, dtype=str, low_memory=False)
    columns = {column.lower(): column for column in sample.columns}

    location_key = columns.get("location_id")
    country_key = None
    for column in sample.columns:
        if "country" in column.lower():
            country_key = column
            break

    if not location_key or not country_key:
        return {}

    lookup: dict[str, str] = {}
    for chunk in pd.read_csv(
        location_file,
        sep="\t",
        dtype=str,
        usecols=[location_key, country_key],
        chunksize=100_000,
        low_memory=False,
    ):
        chunk = chunk.dropna(subset=[location_key]).copy()
        chunk[country_key] = normalise_text(chunk[country_key]).replace("", "Unknown")
        pairs = (
            chunk[[location_key, country_key]]
            .drop_duplicates(subset=[location_key])
            .itertuples(index=False, name=None)
        )
        for location_id, country in pairs:
            lookup[str(location_id)] = str(country)

    return lookup


def process_patents(limit: int | None, chunk_size: int, sample_step: int | None) -> set[str] | None:
    patent_file = RAW_DIR / "g_patent.tsv"
    abstract_file = RAW_DIR / "g_patent_abstract.tsv"
    output_file = PROCESSED_DIR / "clean_patents.csv"

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    selected_ids: set[str] | None = set() if limit is not None else None
    written = 0
    first_chunk = True
    patent_position = 0

    patent_reader = pd.read_csv(
        patent_file,
        sep="\t",
        dtype=str,
        chunksize=chunk_size,
        low_memory=False,
    )
    abstract_reader = pd.read_csv(
        abstract_file,
        sep="\t",
        dtype=str,
        chunksize=chunk_size,
        low_memory=False,
    )

    for patent_chunk, abstract_chunk in zip(patent_reader, abstract_reader):
        patent_chunk.columns = [column.strip('"') for column in patent_chunk.columns]
        abstract_chunk.columns = [column.strip('"') for column in abstract_chunk.columns]

        patent_chunk["patent_id"] = normalise_text(patent_chunk["patent_id"])
        abstract_chunk["patent_id"] = normalise_text(abstract_chunk["patent_id"])

        if patent_chunk["patent_id"].equals(abstract_chunk["patent_id"]):
            patent_chunk["patent_abstract"] = abstract_chunk["patent_abstract"].values
            merged = patent_chunk
        else:
            merged = patent_chunk.merge(abstract_chunk, on="patent_id", how="left")

        merged = merged[merged["withdrawn"].fillna("0") != "1"].copy()
        merged["patent_title"] = normalise_text(merged["patent_title"])
        merged["patent_abstract"] = normalise_text(merged["patent_abstract"])
        merged["patent_date"] = normalise_text(merged["patent_date"])
        merged = merged[merged["patent_title"] != ""]
        merged = merged[merged["patent_date"] != ""]

        merged["year"] = pd.to_numeric(
            merged["patent_date"].str.slice(0, 4), errors="coerce"
        ).astype("Int64")
        merged = merged.dropna(subset=["year"])

        cleaned = merged.loc[
            :, ["patent_id", "patent_title", "patent_abstract", "patent_date", "year"]
        ].rename(
            columns={
                "patent_title": "title",
                "patent_abstract": "abstract",
                "patent_date": "filing_date",
            }
        )

        cleaned = cleaned.drop_duplicates(subset=["patent_id"])

        if sample_step and sample_step > 1:
            mask = [((patent_position + idx) % sample_step) == 0 for idx in range(len(cleaned))]
            patent_position += len(cleaned)
            cleaned = cleaned.loc[mask].copy()
        else:
            patent_position += len(cleaned)

        if limit is not None:
            remaining = limit - written
            if remaining <= 0:
                break
            cleaned = cleaned.head(remaining)

        if cleaned.empty:
            continue

        write_chunk(cleaned, output_file, first_chunk)
        first_chunk = False

        written += len(cleaned)
        if selected_ids is not None:
            selected_ids.update(cleaned["patent_id"].tolist())

        print(f"patents: {written:,} rows written", end="\r")

        if limit is not None and written >= limit:
            break

    print(" " * 60, end="\r")
    print(f"patents: finished with {written:,} rows")
    return selected_ids


def process_inventors(selected_ids: set[str] | None, chunk_size: int, country_lookup: dict[str, str]) -> None:
    inventor_file = RAW_DIR / "g_inventor_disambiguated.tsv"
    inventors_output = PROCESSED_DIR / "clean_inventors.csv"
    patent_inventors_output = PROCESSED_DIR / "clean_patent_inventors.csv"

    seen_inventors: set[str] = set()
    first_inventor_chunk = True
    first_link_chunk = True
    inventor_rows = 0
    link_rows = 0

    for chunk in pd.read_csv(
        inventor_file,
        sep="\t",
        dtype=str,
        chunksize=chunk_size,
        low_memory=False,
    ):
        chunk.columns = [column.strip('"') for column in chunk.columns]
        chunk["patent_id"] = normalise_text(chunk["patent_id"])

        if selected_ids is not None:
            chunk = chunk[chunk["patent_id"].isin(selected_ids)].copy()
            if chunk.empty:
                continue

        chunk["inventor_id"] = normalise_text(chunk["inventor_id"])
        chunk["first_name"] = normalise_text(chunk["disambig_inventor_name_first"])
        chunk["last_name"] = normalise_text(chunk["disambig_inventor_name_last"])
        chunk["name"] = normalise_text(chunk["first_name"] + " " + chunk["last_name"])
        chunk["name"] = chunk["name"].replace("", "Unknown Inventor")

        if "location_id" in chunk.columns:
            chunk["country"] = chunk["location_id"].map(country_lookup).fillna("Unknown")
        else:
            chunk["country"] = "Unknown"

        links = chunk.loc[:, ["patent_id", "inventor_id"]].drop_duplicates()
        write_chunk(links, patent_inventors_output, first_link_chunk)
        first_link_chunk = False
        link_rows += len(links)

        inventors = chunk.loc[:, ["inventor_id", "name", "country"]].drop_duplicates(
            subset=["inventor_id"]
        )
        inventors = inventors[~inventors["inventor_id"].isin(seen_inventors)].copy()

        if not inventors.empty:
            seen_inventors.update(inventors["inventor_id"].tolist())
            write_chunk(inventors, inventors_output, first_inventor_chunk)
            first_inventor_chunk = False
            inventor_rows += len(inventors)

        print(
            f"inventors: {inventor_rows:,} unique, {link_rows:,} patent links",
            end="\r",
        )

    print(" " * 80, end="\r")
    print(f"inventors: finished with {inventor_rows:,} unique inventors")


def process_companies(selected_ids: set[str] | None, chunk_size: int) -> None:
    assignee_file = RAW_DIR / "g_assignee_disambiguated.tsv"
    companies_output = PROCESSED_DIR / "clean_companies.csv"
    patent_companies_output = PROCESSED_DIR / "clean_patent_companies.csv"

    seen_companies: set[str] = set()
    first_company_chunk = True
    first_link_chunk = True
    company_rows = 0
    link_rows = 0

    for chunk in pd.read_csv(
        assignee_file,
        sep="\t",
        dtype=str,
        chunksize=chunk_size,
        low_memory=False,
    ):
        chunk.columns = [column.strip('"') for column in chunk.columns]
        chunk["patent_id"] = normalise_text(chunk["patent_id"])

        if selected_ids is not None:
            chunk = chunk[chunk["patent_id"].isin(selected_ids)].copy()
            if chunk.empty:
                continue

        chunk["assignee_id"] = normalise_text(chunk["assignee_id"])
        chunk["org_name"] = normalise_text(chunk["disambig_assignee_organization"])
        chunk["person_name"] = normalise_text(
            normalise_text(chunk["disambig_assignee_individual_name_first"])
            + " "
            + normalise_text(chunk["disambig_assignee_individual_name_last"])
        )
        chunk["name"] = chunk["org_name"].where(chunk["org_name"] != "", chunk["person_name"])
        chunk["name"] = chunk["name"].replace("", "Unknown Assignee")

        primary_links = chunk[chunk["assignee_sequence"].fillna("0") == "0"].copy()
        primary_links = primary_links.loc[:, ["patent_id", "assignee_id"]].rename(
            columns={"assignee_id": "company_id"}
        )
        primary_links = primary_links.drop_duplicates(subset=["patent_id", "company_id"])

        if not primary_links.empty:
            write_chunk(primary_links, patent_companies_output, first_link_chunk)
            first_link_chunk = False
            link_rows += len(primary_links)

        companies = chunk.loc[:, ["assignee_id", "name"]].rename(
            columns={"assignee_id": "company_id"}
        )
        companies = companies.drop_duplicates(subset=["company_id"])
        companies = companies[~companies["company_id"].isin(seen_companies)].copy()

        if not companies.empty:
            seen_companies.update(companies["company_id"].tolist())
            write_chunk(companies, companies_output, first_company_chunk)
            first_company_chunk = False
            company_rows += len(companies)

        print(
            f"companies: {company_rows:,} unique, {link_rows:,} primary links",
            end="\r",
        )

    print(" " * 80, end="\r")
    print(f"companies: finished with {company_rows:,} unique companies")


def load_csv_to_table(conn: sqlite3.Connection, csv_path: Path, table_name: str, chunk_size: int) -> None:
    for chunk in pd.read_csv(csv_path, chunksize=chunk_size, dtype=str, low_memory=False):
        chunk.to_sql(table_name, conn, if_exists="append", index=False)


def build_database(chunk_size: int) -> Path:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    db_path = DB_DIR / "patent_intelligence.db"

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        deduplicate_clean_file(PROCESSED_DIR / "clean_patents.csv", ["patent_id"])
        deduplicate_clean_file(PROCESSED_DIR / "clean_inventors.csv", ["inventor_id"])
        deduplicate_clean_file(PROCESSED_DIR / "clean_companies.csv", ["company_id"])
        deduplicate_clean_file(
            PROCESSED_DIR / "clean_patent_inventors.csv", ["patent_id", "inventor_id"]
        )
        deduplicate_clean_file(
            PROCESSED_DIR / "clean_patent_companies.csv", ["patent_id", "company_id"]
        )

        schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
        conn.executescript(schema_sql)

        load_csv_to_table(conn, PROCESSED_DIR / "clean_patents.csv", "patents", chunk_size)
        load_csv_to_table(conn, PROCESSED_DIR / "clean_inventors.csv", "inventors", chunk_size)
        load_csv_to_table(conn, PROCESSED_DIR / "clean_companies.csv", "companies", chunk_size)
        load_csv_to_table(
            conn, PROCESSED_DIR / "clean_patent_inventors.csv", "patent_inventors", chunk_size
        )
        load_csv_to_table(
            conn, PROCESSED_DIR / "clean_patent_companies.csv", "patent_companies", chunk_size
        )

        conn.executescript(
            """
            INSERT INTO relationships (patent_id, inventor_id, company_id)
            SELECT
                pi.patent_id,
                pi.inventor_id,
                pc.company_id
            FROM patent_inventors pi
            LEFT JOIN patent_companies pc
                ON pi.patent_id = pc.patent_id;
            """
        )

        relationships = pd.read_sql_query(
            "SELECT patent_id, inventor_id, company_id FROM relationships", conn
        )
        relationships.to_csv(PROCESSED_DIR / "clean_relationships.csv", index=False)
        conn.commit()
    finally:
        conn.close()

    return db_path


def write_run_metadata(limit: int | None, chunk_size: int, sample_step: int | None, db_path: Path) -> None:
    metadata = {
        "patent_limit": limit,
        "chunk_size": chunk_size,
        "sample_step": sample_step,
        "database": str(db_path.relative_to(ROOT)),
    }
    (PROCESSED_DIR / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean patent data and load it into SQLite.")
    parser.add_argument(
        "--patent-limit",
        type=int,
        default=None,
        help="Optional limit for the number of patents to process.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=50_000,
        help="Rows per chunk while reading the raw TSV files.",
    )
    parser.add_argument(
        "--sample-step",
        type=int,
        default=None,
        help="Keep every Nth patent after cleaning to build a lighter sample spread across the file.",
    )
    parser.add_argument(
        "--skip-patents",
        action="store_true",
        help="Reuse the existing clean_patents.csv instead of rebuilding it.",
    )
    parser.add_argument(
        "--skip-inventors",
        action="store_true",
        help="Reuse the existing clean_inventors.csv and clean_patent_inventors.csv.",
    )
    parser.add_argument(
        "--skip-companies",
        action="store_true",
        help="Reuse the existing clean_companies.csv and clean_patent_companies.csv.",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip rebuilding the SQLite database.",
    )
    args = parser.parse_args()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    country_lookup = build_location_lookup()

    if args.skip_patents:
        selected_ids = load_selected_ids_from_clean_patents()
    else:
        selected_ids = process_patents(args.patent_limit, args.chunk_size, args.sample_step)

    if not args.skip_inventors:
        process_inventors(selected_ids, args.chunk_size, country_lookup)

    if not args.skip_companies:
        process_companies(selected_ids, args.chunk_size)

    if not args.skip_db:
        db_path = build_database(args.chunk_size)
        write_run_metadata(args.patent_limit, args.chunk_size, args.sample_step, db_path)
        print(f"database: saved to {db_path}")


if __name__ == "__main__":
    main()
