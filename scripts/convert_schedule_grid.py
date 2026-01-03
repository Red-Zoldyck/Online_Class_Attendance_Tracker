import argparse
import csv
import re
from pathlib import Path
from typing import List, Tuple

ROOM_PATTERN = re.compile(r"^[A-Z]-\d{3}$")

def detect_rooms(header: List[str]) -> List[Tuple[int, str]]:
    rooms: List[Tuple[int, str]] = []
    for idx, val in enumerate(header):
        if idx == 0:
            continue
        name = (val or "").strip()
        if ROOM_PATTERN.match(name):
            rooms.append((idx, name))
    return rooms

def parse_grid(rows: List[List[str]]) -> List[dict]:
    output: List[dict] = []
    current_block = ""
    rooms: List[Tuple[int, str]] = []
    i = 0
    total = len(rows)

    while i < total:
        row = rows[i]
        first = (row[0] or "").strip() if row else ""

        # Day/block lines like "MONDAY/WEDNESDAY - MORNING"
        if first.upper().startswith(("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")):
            current_block = first
            i += 1
            continue

        # Header line with TIME and room columns
        if first.upper() == "TIME":
            rooms = detect_rooms(row)
            i += 1
            continue

        # Time row e.g., "7:30 - 9:00 AM"
        if ":" in first and ("AM" in first.upper() or "PM" in first.upper()):
            time_value = first
            courses_row = rows[i + 1] if i + 1 < total and (rows[i + 1][0] or "").strip() == "" else None
            instructors_row = rows[i + 2] if i + 2 < total and (rows[i + 2][0] or "").strip() == "" else None

            for idx, room_name in rooms:
                section = row[idx].strip() if idx < len(row) else ""
                course = courses_row[idx].strip() if courses_row and idx < len(courses_row) else ""
                instructor = instructors_row[idx].strip() if instructors_row and idx < len(instructors_row) else ""

                if section or course or instructor:
                    output.append({
                        "day_block": current_block,
                        "time": time_value,
                        "room": room_name,
                        "section": section,
                        "course": course,
                        "instructor": instructor,
                    })
            # Skip past the triple (time + courses + instructors) if present
            if instructors_row:
                i += 3
            elif courses_row:
                i += 2
            else:
                i += 1
            continue

        i += 1

    return output


def convert(input_path: Path, output_path: Path) -> None:
    with input_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    flattened = parse_grid(rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["day_block", "time", "room", "section", "course", "instructor"],
        )
        writer.writeheader()
        writer.writerows(flattened)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert room/time grid schedule CSV to normalized rows")
    parser.add_argument("input", type=Path, help="Path to the grid CSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("normalized_schedule.csv"),
        help="Output CSV path (default: normalized_schedule.csv)",
    )
    args = parser.parse_args()

    convert(args.input, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
