import csv
import json
import re
from collections import defaultdict
from pathlib import Path

CSV_PATH = "data/harry_potter_books.csv"


def safe_filename(book_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", book_name).strip("_")


def main():
    books = defaultdict(lambda: defaultdict(list))  # book -> chapter -> [text fragments]

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            books[row["book"]][row["chapter"]].append(row["text"])

    for book_name, chapters in books.items():
        sorted_chapters = sorted(chapters.keys(), key=lambda c: int(c.split("-")[1]))
        data = {ch: " ".join(chapters[ch]) for ch in sorted_chapters}

        out_path = Path("data") / f"{safe_filename(book_name)}.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out_path} ({len(data)} chapters)")


if __name__ == "__main__":
    main()
