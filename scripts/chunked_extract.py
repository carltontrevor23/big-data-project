from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_INPUT_DIR = Path("data/raw")
DEFAULT_OUTPUT_DIR = Path("data/processed")


def human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def list_tsv_files(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("*.tsv"))


def read_header(file_path: Path, delimiter: str) -> list[str]:
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        return next(reader)


def profile_file(
    file_path: Path,
    delimiter: str,
    chunk_size: int,
    sample_rows: int,
    count_rows: bool,
) -> None:
    print(f"\n=== {file_path.name} ===")
    print(f"Path: {file_path}")
    print(f"Size: {human_size(file_path.stat().st_size)}")

    columns = read_header(file_path, delimiter)
    print(f"Columns ({len(columns)}): {', '.join(columns)}")

    sampled = pd.read_csv(
        file_path,
        sep=delimiter,
        nrows=sample_rows,
        dtype=str,
        low_memory=False,
    )
    print(f"\nSample preview ({len(sampled)} rows):")
    print(sampled.head(sample_rows).to_string(index=False))

    if count_rows:
        total_rows = 0
        for chunk in pd.read_csv(
            file_path,
            sep=delimiter,
            dtype=str,
            chunksize=chunk_size,
            low_memory=False,
        ):
            total_rows += len(chunk)
            print(f"Processed {total_rows:,} rows from {file_path.name}...", end="\r")
        print(" " * 80, end="\r")
        print(f"Total rows: {total_rows:,}")


def extract_columns(
    file_path: Path,
    output_dir: Path,
    delimiter: str,
    chunk_size: int,
    columns: list[str] | None,
    row_limit: int | None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_columns = columns or read_header(file_path, delimiter)
    output_path = output_dir / f"{file_path.stem}_filtered.tsv"

    rows_written = 0
    write_header = True

    for chunk in pd.read_csv(
        file_path,
        sep=delimiter,
        dtype=str,
        usecols=selected_columns,
        chunksize=chunk_size,
        low_memory=False,
    ):
        if row_limit is not None and rows_written >= row_limit:
            break

        if row_limit is not None:
            remaining = row_limit - rows_written
            if remaining <= 0:
                break
            chunk = chunk.head(remaining)

        chunk.to_csv(
            output_path,
            sep=delimiter,
            index=False,
            mode="w" if write_header else "a",
            header=write_header,
        )

        rows_written += len(chunk)
        write_header = False
        print(f"Wrote {rows_written:,} rows to {output_path.name}...", end="\r")

    print(" " * 80, end="\r")
    print(f"Saved {rows_written:,} rows to {output_path}")
    return output_path


def parse_columns(raw_columns: str | None) -> list[str] | None:
    if not raw_columns:
        return None
    return [column.strip() for column in raw_columns.split(",") if column.strip()]


def parse_file_names(raw_file_names: Iterable[str] | None) -> list[str] | None:
    if not raw_file_names:
        return None

    parsed: list[str] = []
    for raw_name in raw_file_names:
        parsed.extend(part.strip() for part in raw_name.split(",") if part.strip())
    return parsed or None


def resolve_files(input_dir: Path, file_names: Iterable[str] | None) -> list[Path]:
    if not file_names:
        return list_tsv_files(input_dir)

    resolved_files: list[Path] = []
    for name in file_names:
        path = input_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Could not find file: {path}")
        resolved_files.append(path)
    return resolved_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile or extract large TSV files in manageable chunks."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing source TSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write extracted TSV files.",
    )
    parser.add_argument(
        "--files",
        action="append",
        help=(
            "Specific TSV filenames to process. Repeat the flag or pass a comma-separated "
            "list. Defaults to all TSV files in input-dir."
        ),
    )
    parser.add_argument(
        "--delimiter",
        default="\t",
        help="Field delimiter. Defaults to tab.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100_000,
        help="Rows per chunk while processing large files.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    profile_parser = subparsers.add_parser(
        "profile",
        help="Show columns, a small preview, and optionally count rows.",
    )
    profile_parser.add_argument(
        "--sample-rows",
        type=int,
        default=5,
        help="Number of preview rows to print.",
    )
    profile_parser.add_argument(
        "--count-rows",
        action="store_true",
        help="Count rows by scanning the full file in chunks.",
    )

    extract_parser = subparsers.add_parser(
        "extract",
        help="Write selected columns into smaller TSV files in chunks.",
    )
    extract_parser.add_argument(
        "--columns",
        help="Comma-separated list of columns to keep. Defaults to all columns.",
    )
    extract_parser.add_argument(
        "--row-limit",
        type=int,
        help="Optional maximum number of rows to write for testing.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    files = resolve_files(args.input_dir, parse_file_names(args.files))
    if not files:
        raise FileNotFoundError(f"No TSV files found in {args.input_dir}")

    if args.command == "profile":
        for file_path in files:
            profile_file(
                file_path=file_path,
                delimiter=args.delimiter,
                chunk_size=args.chunk_size,
                sample_rows=args.sample_rows,
                count_rows=args.count_rows,
            )
        return

    if args.command == "extract":
        columns = parse_columns(args.columns)
        for file_path in files:
            extract_columns(
                file_path=file_path,
                output_dir=args.output_dir,
                delimiter=args.delimiter,
                chunk_size=args.chunk_size,
                columns=columns,
                row_limit=args.row_limit,
            )
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
