"""Loading and checking the query-classification CSV files."""

import csv
from pathlib import Path

LABELS = ("KNOWLEDGE_RAG", "LITERATURE_CONTEXT", "GENERAL_INFORMATION")
REQUIRED_COLUMNS = {"query_id", "query", "label", "topic_group"}


def load_rows(path: Path) -> list[dict[str, str]]:
    """Read one dataset file and reject incomplete or unexpected rows."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(f"{path.name} must contain: {sorted(REQUIRED_COLUMNS)}")
        rows = list(reader)

    if not rows:
        raise ValueError(f"Dataset is empty: {path}")

    for line_number, row in enumerate(rows, start=2):
        if not row["query"].strip():
            raise ValueError(f"Empty query in {path.name}, row {line_number}")
        if row["label"] not in LABELS:
            raise ValueError(
                f"Unexpected label {row['label']!r} in {path.name}, row {line_number}"
            )
        if not row["topic_group"].strip():
            raise ValueError(f"Empty topic_group in {path.name}, row {line_number}")

    normalized_queries = [row["query"].strip().casefold() for row in rows]
    if len(normalized_queries) != len(set(normalized_queries)):
        raise ValueError(f"Duplicate question found in {path.name}")

    return rows


def validate_train_test(train_rows: list[dict[str, str]], test_rows: list[dict[str, str]]) -> None:
    """Check that the held-out set does not share questions or topic groups."""
    train_queries = {row["query"].strip().casefold() for row in train_rows}
    test_queries = {row["query"].strip().casefold() for row in test_rows}
    if train_queries & test_queries:
        raise ValueError("Training and test files contain duplicate questions")

    train_groups = {row["topic_group"] for row in train_rows}
    test_groups = {row["topic_group"] for row in test_rows}
    if train_groups & test_groups:
        raise ValueError("Training and test files share topic groups")

    for name, rows, expected_count in (("training", train_rows, 400), ("test", test_rows, 100)):
        counts = {label: sum(row["label"] == label for row in rows) for label in LABELS}
        if counts != {label: expected_count for label in LABELS}:
            raise ValueError(f"Unexpected {name} class counts: {counts}")
