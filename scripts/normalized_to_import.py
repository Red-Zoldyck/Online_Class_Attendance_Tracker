import argparse
import csv
import re
from pathlib import Path
from typing import List, Dict

DIGIT_RE = re.compile(r"(\d+)")


def infer_year(section: str) -> str:
    s = (section or "").upper().strip()
    if not s:
        return ""
    # Direct digit pick (1-4)
    m = DIGIT_RE.search(s)
    if m:
        num = m.group(1)
        if num in {"1", "2", "3", "4"}:
            return num
        # handle like "4TH" or "4TH-IRREG"
        if num and num[0] in {"1", "2", "3", "4"}:
            return num[0]
    # Irregular -> map to 4 by default
    if "IRREG" in s or "IRR" in s:
        return "4"
    return ""


def to_import_rows(rows: List[Dict[str, str]], default_term: str) -> List[Dict[str, str]]:
    out = []
    for r in rows:
        section = r.get("section", "").strip()
        code = r.get("course", "").strip()
        instructor = r.get("instructor", "").strip()
        # Build a readable schedule field
        day_block = r.get("day_block", "").strip()
        time = r.get("time", "").strip()
        room = r.get("room", "").strip()
        schedule = " ".join(part for part in [day_block, time, room] if part)

        year = infer_year(section)

        out.append({
            "CODE": code,
            "TITLE": "",  # leave blank; importer will keep existing title
            "SECTION": section,
            "TERM": default_term,
            "YEAR": year,
            "Name": instructor,
            "SCHEDULE": schedule,
        })
    return out


def convert(input_path: Path, output_path: Path, term: str):
    with input_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    converted = to_import_rows(rows, term)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["CODE", "TITLE", "SECTION", "TERM", "YEAR", "Name", "SCHEDULE"],
        )
        writer.writeheader()
        writer.writerows(converted)


def main():
    parser = argparse.ArgumentParser(description="Convert normalized schedule to importer-ready CSV")
    parser.add_argument("input", type=Path, help="normalized_schedule.csv")
    parser.add_argument("--output", type=Path, default=Path("import_ready_schedule.csv"))
    parser.add_argument("--term", default="1", help="TERM value to set (default: 1)")
    args = parser.parse_args()

    convert(args.input, args.output, args.term)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
