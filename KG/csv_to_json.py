import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path


def safe_filename(book_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", book_name).strip("_")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--book-col", default="book")
    parser.add_argument("--section-col", default="chapter")
    parser.add_argument("--text-col", default="text")
    parser.add_argument("--out-dir", default="data")
    args = parser.parse_args()

    books = defaultdict(lambda: defaultdict(list))

    with open(args.csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            books[row[args.book_col]][row[args.section_col]].append(row[args.text_col])

    for book_name, sections in books.items():
        data = {section: " ".join(parts) for section, parts in sections.items()}

        out_path = Path(args.out_dir) / f"{safe_filename(book_name)}.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out_path} ({len(data)} sections)")


if __name__ == "__main__":
    main()
